import re
from typing import Dict, Any, Type
from collections import Counter
from pydantic import BaseModel, Field
from ...models.plugin import BasePlugin, BasePluginResponse


class TextStatResponse(BasePluginResponse):
    """Pydantic model for text statistics plugin response"""
    character_count: int = Field(..., description="Total number of characters including spaces and punctuation")
    character_count_no_spaces: int = Field(..., description="Total number of characters excluding spaces")
    word_count: int = Field(..., description="Total number of words")
    line_count: int = Field(..., description="Total number of lines")
    unique_words: int = Field(..., description="Number of unique words (case-insensitive)")
    unique_characters: int = Field(..., description="Number of unique characters")
    word_frequency: Dict[str, int] = Field(..., description="Frequency count of each word")
    character_frequency: Dict[str, int] = Field(..., description="Frequency count of each character")
    average_word_length: float = Field(..., description="Average length of words")
    sentence_count: int = Field(..., description="Estimated number of sentences")


class TextStatInput(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=100000,
        json_schema_extra={
            "label": "Text to Analyze",
            "field_type": "textarea",
            "placeholder": "Enter your text here for analysis...",
        },
    )


class Plugin(BasePlugin):
    """Text Statistics Plugin - Analyzes text and provides comprehensive statistics"""

    @classmethod
    def get_input_model(cls) -> Type[BaseModel]:
        """Return the canonical input model for this plugin."""
        return TextStatInput
    
    @classmethod
    def get_response_model(cls) -> Type[BasePluginResponse]:
        """Return the Pydantic model for this plugin's response"""
        return TextStatResponse
    
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the text statistics analysis
        
        Args:
            data: Dictionary containing 'text' key with the text to analyze
            
        Returns:
            Dictionary with comprehensive text statistics that validates against TextStatResponse
        """
        text = data.get('text', '')
        
        if not text:
            # For error cases, we might want to have a separate error response model
            # For now, we'll return a valid response with zeros
            return {
                "character_count": 0,
                "character_count_no_spaces": 0,
                "word_count": 0,
                "line_count": 0,
                "unique_words": 0,
                "unique_characters": 0,
                "word_frequency": {},
                "character_frequency": {},
                "average_word_length": 0.0,
                "sentence_count": 0
            }
        
        # Basic counts
        character_count = len(text)
        character_count_no_spaces = len(text.replace(' ', ''))
        line_count = len(text.splitlines())
        
        # Word analysis
        words = self._extract_words(text)
        word_count = len(words)
        unique_words_set = set(word.lower() for word in words)
        unique_words = len(unique_words_set)
        
        # Character analysis
        unique_characters = len(set(text))
        
        # Frequency analysis
        word_frequency = dict(Counter(word.lower() for word in words))
        character_frequency = dict(Counter(text))
        
        # Advanced statistics
        average_word_length = sum(len(word) for word in words) / word_count if word_count > 0 else 0.0
        sentence_count = self._count_sentences(text)
        
        return {
            "character_count": character_count,
            "character_count_no_spaces": character_count_no_spaces,
            "word_count": word_count,
            "line_count": line_count,
            "unique_words": unique_words,
            "unique_characters": unique_characters,
            "word_frequency": word_frequency,
            "character_frequency": character_frequency,
            "average_word_length": round(average_word_length, 2),
            "sentence_count": sentence_count
        }
    
    def _extract_words(self, text: str) -> list:
        """Extract words from text using regex"""
        # Match word characters (letters, numbers, apostrophes in contractions)
        words = re.findall(r"\b\w+(?:'\w+)?\b", text)
        return words
    
    def _count_sentences(self, text: str) -> int:
        """Count sentences based on sentence-ending punctuation"""
        # Count sentences by looking for sentence-ending punctuation
        sentence_endings = re.findall(r'[.!?]+', text)
        return len(sentence_endings) if sentence_endings else (1 if text.strip() else 0) 
