import re
from typing import Dict, Any, Type
from collections import Counter
from pydantic import BaseModel, Field
from ...models.plugin import BasePlugin, BasePluginResponse
from .models import BagOfWordsResponse, WordItem, FrequencyHistogram


class BagOfWordsInput(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=100000,
        json_schema_extra={
            "label": "Text to Analyze",
            "field_type": "textarea",
            "placeholder": "Enter your text here for bag of words analysis...",
        },
    )
    cutoff: int = Field(
        default=0,
        ge=0,
        le=1000,
        json_schema_extra={
            "label": "Frequency Cutoff",
            "field_type": "number",
            "placeholder": "0",
            "help": "Only show words that appear at least this many times (0 = show all words)",
        },
    )


class Plugin(BasePlugin):
    """Bag of Words Plugin - Creates a bag of words representation with frequency filtering"""

    @classmethod
    def get_input_model(cls) -> Type[BaseModel]:
        """Return the canonical input model for this plugin."""
        return BagOfWordsInput
    
    @classmethod
    def get_response_model(cls) -> Type[BasePluginResponse]:
        """Return the Pydantic model for this plugin's response"""
        return BagOfWordsResponse
    
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the bag of words analysis with frequency filtering
        
        Args:
            data: Dictionary containing 'text' key and optional 'cutoff' key
            
        Returns:
            Dictionary with bag of words analysis that validates against BagOfWordsResponse
        """
        text = data.get('text', '')
        cutoff = data.get('cutoff', 0)
        
        # Ensure cutoff is an integer and non-negative
        if isinstance(cutoff, str):
            try:
                cutoff = int(cutoff)
            except ValueError:
                cutoff = 0
        cutoff = max(0, cutoff)
        
        if not text:
            return {
                "total_words": 0,
                "unique_words": 0,
                "filtered_words": 0,
                "cutoff_threshold": cutoff,
                "word_frequencies": {},
                "word_list": []
            }
        
        # Extract words from text
        words = self._extract_words(text)
        total_words = len(words)
        
        # Calculate word frequencies
        word_counter = Counter(word.lower() for word in words)
        unique_words = len(word_counter)
        
        # Apply cutoff filter and sort by frequency (descending)
        sorted_frequencies = sorted(
            [(word, freq) for word, freq in word_counter.items() if freq >= cutoff],
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Create sorted word frequencies dictionary (maintains order in Python 3.7+)
        filtered_frequencies = {word: freq for word, freq in sorted_frequencies}
        filtered_words = len(filtered_frequencies)
        
        # Create sorted word list by frequency (descending)
        word_list = [
            {"word": word, "frequency": freq}
            for word, freq in sorted_frequencies
        ]
        
        # Generate frequency histogram
        histogram = self._generate_frequency_histogram(filtered_frequencies)
        
        return {
            "total_words": total_words,
            "unique_words": unique_words,
            "filtered_words": filtered_words,
            "cutoff_threshold": cutoff,
            "word_frequencies": filtered_frequencies,
            "word_list": word_list,
            "frequency_histogram": histogram
        }
    
    def _extract_words(self, text: str) -> list:
        """Extract words from text using regex"""
        # Match word characters (letters, numbers, apostrophes in contractions)
        # This is consistent with the text_stat plugin
        words = re.findall(r"\b\w+(?:'\w+)?\b", text)
        return words
    
    def _generate_frequency_histogram(self, word_frequencies: Dict[str, int]) -> Dict[str, Any]:
        """Generate histogram data for frequency distribution"""
        if not word_frequencies:
            return {
                "bins": [],
                "counts": [],
                "labels": []
            }
        
        # Get all frequency values
        frequencies = list(word_frequencies.values())
        max_freq = max(frequencies)
        
        # Create frequency bins
        if max_freq <= 10:
            # For small datasets, use individual bins
            bins = list(range(1, max_freq + 1))
            bin_labels = [str(i) for i in bins]
        else:
            # For larger datasets, group into ranges
            if max_freq <= 50:
                bins = [1, 2, 3, 4, 5, 10, max_freq]
                bin_labels = ["1", "2", "3", "4", "5", "6-9", f"10-{max_freq}"]
            else:
                bins = [1, 2, 5, 10, 20, 50, max_freq]
                bin_labels = ["1", "2", "3-4", "5-9", "10-19", "20-49", f"50-{max_freq}"]
        
        # Count words in each bin
        counts = []
        for i, bin_val in enumerate(bins):
            if i == 0:
                # First bin: exactly this frequency
                count = sum(1 for freq in frequencies if freq == bin_val)
            elif i == len(bins) - 1:
                # Last bin: from previous bin + 1 to max
                prev_bin = bins[i - 1]
                count = sum(1 for freq in frequencies if freq > prev_bin)
            else:
                # Middle bins: from previous bin + 1 to current bin
                prev_bin = bins[i - 1] if i > 0 else 0
                count = sum(1 for freq in frequencies if prev_bin < freq <= bin_val)
            counts.append(count)
        
        # Clean up bins and labels to only include non-zero counts
        filtered_bins = []
        filtered_counts = []
        filtered_labels = []
        
        for i, count in enumerate(counts):
            if count > 0:
                filtered_bins.append(str(bins[i]))
                filtered_counts.append(count)
                filtered_labels.append(bin_labels[i])
        
        return {
            "bins": filtered_bins,
            "counts": filtered_counts,
            "labels": filtered_labels
        }
