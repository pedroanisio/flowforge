import re
from typing import Dict, Any, Type, List, Tuple, Set, Literal
from pydantic import BaseModel, Field
from ...models.plugin import BasePlugin, BasePluginResponse
from .models import ContextAwareStopwordsResponse, WordInfo, ProcessingStatistics

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    from nltk.tag import pos_tag
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False


class ContextAwareStopwordsInput(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=100000,
        json_schema_extra={
            "label": "Text to Process",
            "field_type": "textarea",
            "placeholder": "Enter your text here for context-aware stopword removal...",
        },
    )
    method: Literal["standard", "context_aware", "pos_based"] = Field(
        default="context_aware",
        json_schema_extra={
            "label": "Removal Method",
            "field_type": "select",
            "options": ["standard", "context_aware", "pos_based"],
            "help": "Standard: basic stopword list; Context-aware: preserves words based on context; POS-based: uses part-of-speech tagging",
        },
    )
    preserve_important: bool = Field(
        default=True,
        json_schema_extra={
            "label": "Preserve Important Words",
            "field_type": "checkbox",
            "help": "When enabled, preserves words that might be stopwords but are important in context (e.g., 'will' as a noun vs. auxiliary verb)",
        },
    )
    custom_stopwords: str = Field(
        default="",
        json_schema_extra={
            "label": "Additional Stopwords",
            "field_type": "text",
            "placeholder": "word1, word2, word3",
            "help": "Comma-separated list of additional words to remove (optional)",
        },
    )


class Plugin(BasePlugin):
    """Context-Aware Stopword Removal Plugin - Advanced stopword removal using POS tagging and context analysis"""
    
    def __init__(self):
        super().__init__()
        self._download_nltk_data()
        
    def _download_nltk_data(self):
        """Download required NLTK data if available"""
        if NLTK_AVAILABLE:
            try:
                nltk.data.find('tokenizers/punkt')
                nltk.data.find('corpora/stopwords')
                nltk.data.find('taggers/averaged_perceptron_tagger')
            except LookupError:
                try:
                    nltk.download('punkt', quiet=True)
                    nltk.download('stopwords', quiet=True)
                    nltk.download('averaged_perceptron_tagger', quiet=True)
                except Exception:
                    pass
    
    @classmethod
    def get_input_model(cls) -> Type[BaseModel]:
        """Return the canonical input model for this plugin."""
        return ContextAwareStopwordsInput

    @classmethod
    def get_response_model(cls) -> Type[BasePluginResponse]:
        """Return the Pydantic model for this plugin's response"""
        return ContextAwareStopwordsResponse
    
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute context-aware stopword removal
        
        Args:
            data: Dictionary containing 'text', 'method', 'preserve_important', and 'custom_stopwords'
            
        Returns:
            Dictionary with processed text and analysis that validates against ContextAwareStopwordsResponse
        """
        text = data.get('text', '')
        method = data.get('method', 'context_aware')
        preserve_important = data.get('preserve_important', True)
        custom_stopwords = data.get('custom_stopwords', '')
        
        if not text:
            return self._empty_response(method)
        
        # Parse custom stopwords
        custom_stop_set = set()
        if custom_stopwords:
            custom_stop_set = {word.strip().lower() for word in custom_stopwords.split(',') if word.strip()}
        
        # Process text based on method
        if method == 'standard':
            return self._standard_stopword_removal(text, custom_stop_set)
        elif method == 'pos_based':
            return self._pos_based_removal(text, custom_stop_set, preserve_important)
        else:  # context_aware (default)
            return self._context_aware_removal(text, custom_stop_set, preserve_important)
    
    def _empty_response(self, method: str) -> Dict[str, Any]:
        """Return empty response for empty input"""
        return {
            "original_text": "",
            "processed_text": "",
            "method_used": method,
            "words_removed": [],
            "words_preserved": [],
            "statistics": {
                "original_word_count": 0,
                "processed_word_count": 0,
                "words_removed_count": 0,
                "words_preserved_count": 0,
                "stopword_removal_rate": 0.0
            }
        }
    
    def _get_basic_stopwords(self) -> Set[str]:
        """Get basic English stopwords"""
        if NLTK_AVAILABLE:
            try:
                return set(stopwords.words('english'))
            except Exception:
                pass
        
        # Fallback basic stopword list
        return {
            'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours',
            'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her', 'hers',
            'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves',
            'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am', 'is', 'are',
            'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does',
            'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until',
            'while', 'of', 'at', 'by', 'for', 'with', 'through', 'during', 'before', 'after',
            'above', 'below', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again',
            'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all',
            'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
            'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'can', 'will', 'just',
            'should', 'now'
        }
    
    def _tokenize_and_tag(self, text: str) -> List[Tuple[str, str]]:
        """Tokenize text and get POS tags"""
        if NLTK_AVAILABLE:
            try:
                tokens = word_tokenize(text)
                tagged = pos_tag(tokens)
                return tagged
            except Exception:
                pass
        
        # Fallback tokenization without POS tagging
        words = re.findall(r'\b\w+\b', text)
        return [(word, 'UNKNOWN') for word in words]
    
    def _standard_stopword_removal(self, text: str, custom_stopwords: Set[str]) -> Dict[str, Any]:
        """Standard stopword removal using predefined list"""
        stop_words = self._get_basic_stopwords()
        stop_words.update(custom_stopwords)
        
        words = re.findall(r'\b\w+\b', text)
        original_count = len(words)
        
        removed_words = []
        kept_words = []
        
        for word in words:
            word_lower = word.lower()
            if word_lower in stop_words:
                removed_words.append({
                    "word": word,
                    "pos_tag": "STOPWORD",
                    "reason": "Standard stopword list"
                })
            else:
                kept_words.append(word)
        
        processed_text = ' '.join(kept_words)
        processed_count = len(kept_words)
        removed_count = len(removed_words)
        
        return {
            "original_text": text,
            "processed_text": processed_text,
            "method_used": "standard",
            "words_removed": removed_words,
            "words_preserved": [],
            "statistics": {
                "original_word_count": original_count,
                "processed_word_count": processed_count,
                "words_removed_count": removed_count,
                "words_preserved_count": 0,
                "stopword_removal_rate": (removed_count / original_count * 100) if original_count > 0 else 0.0
            }
        }
    
    def _pos_based_removal(self, text: str, custom_stopwords: Set[str], preserve_important: bool) -> Dict[str, Any]:
        """POS-based stopword removal"""
        stop_words = self._get_basic_stopwords()
        stop_words.update(custom_stopwords)
        
        tagged_words = self._tokenize_and_tag(text)
        original_count = len(tagged_words)
        
        # POS tags that typically indicate stopwords
        stopword_pos = {'DT', 'IN', 'TO', 'CC', 'PRP', 'PRP$', 'WDT', 'WP', 'WP$', 'WRB'}
        
        # POS tags that should be preserved even if they're in stopword list
        important_pos = {'NN', 'NNS', 'NNP', 'NNPS', 'VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ', 'JJ', 'JJR', 'JJS'}
        
        removed_words = []
        preserved_words = []
        kept_words = []
        
        for word, pos in tagged_words:
            word_lower = word.lower()
            
            if word_lower in stop_words:
                if preserve_important and pos in important_pos:
                    # Preserve word despite being in stopword list
                    kept_words.append(word)
                    preserved_words.append({
                        "word": word,
                        "pos_tag": pos,
                        "reason": f"Preserved: {pos} tag indicates importance"
                    })
                else:
                    # Remove as stopword
                    removed_words.append({
                        "word": word,
                        "pos_tag": pos,
                        "reason": f"Stopword with {pos} tag"
                    })
            elif pos in stopword_pos:
                # Remove based on POS tag even if not in stopword list
                removed_words.append({
                    "word": word,
                    "pos_tag": pos,
                    "reason": f"Removed: {pos} tag indicates function word"
                })
            else:
                kept_words.append(word)
        
        processed_text = ' '.join(kept_words)
        processed_count = len(kept_words)
        removed_count = len(removed_words)
        preserved_count = len(preserved_words)
        
        return {
            "original_text": text,
            "processed_text": processed_text,
            "method_used": "pos_based",
            "words_removed": removed_words,
            "words_preserved": preserved_words,
            "statistics": {
                "original_word_count": original_count,
                "processed_word_count": processed_count,
                "words_removed_count": removed_count,
                "words_preserved_count": preserved_count,
                "stopword_removal_rate": (removed_count / original_count * 100) if original_count > 0 else 0.0
            }
        }
    
    def _context_aware_removal(self, text: str, custom_stopwords: Set[str], preserve_important: bool) -> Dict[str, Any]:
        """Context-aware stopword removal with advanced heuristics"""
        stop_words = self._get_basic_stopwords()
        stop_words.update(custom_stopwords)
        
        tagged_words = self._tokenize_and_tag(text)
        original_count = len(tagged_words)
        
        removed_words = []
        preserved_words = []
        kept_words = []
        
        for i, (word, pos) in enumerate(tagged_words):
            word_lower = word.lower()
            
            if word_lower in stop_words:
                # Apply context-aware rules
                should_preserve = False
                reason = ""
                
                if preserve_important:
                    # Rule 1: Preserve "will" when it's a noun (testament)
                    if word_lower == 'will' and pos in ['NN', 'NNS']:
                        should_preserve = True
                        reason = "Preserved: 'will' as noun (testament)"
                    
                    # Rule 2: Preserve "may" when it's a noun (month)
                    elif word_lower == 'may' and pos in ['NN', 'NNP']:
                        should_preserve = True
                        reason = "Preserved: 'may' as noun (month/name)"
                    
                    # Rule 3: Preserve "can" when it's a noun (container)
                    elif word_lower == 'can' and pos in ['NN', 'NNS']:
                        should_preserve = True
                        reason = "Preserved: 'can' as noun (container)"
                    
                    # Rule 4: Preserve pronouns in specific contexts (e.g., emphasis)
                    elif pos in ['PRP', 'PRP$'] and i > 0:
                        prev_word = tagged_words[i-1][0].lower()
                        if prev_word in ['only', 'just', 'even', 'especially']:
                            should_preserve = True
                            reason = f"Preserved: pronoun after emphasis word '{prev_word}'"
                    
                    # Rule 5: Preserve important determiners in specific contexts
                    elif word_lower in ['this', 'that', 'these', 'those'] and pos == 'DT':
                        # Check if followed by important noun
                        if i < len(tagged_words) - 1:
                            next_pos = tagged_words[i+1][1]
                            if next_pos in ['NN', 'NNS', 'NNP', 'NNPS']:
                                should_preserve = True
                                reason = "Preserved: demonstrative before important noun"
                
                if should_preserve:
                    kept_words.append(word)
                    preserved_words.append({
                        "word": word,
                        "pos_tag": pos,
                        "reason": reason
                    })
                else:
                    removed_words.append({
                        "word": word,
                        "pos_tag": pos,
                        "reason": "Context-aware stopword removal"
                    })
            else:
                kept_words.append(word)
        
        processed_text = ' '.join(kept_words)
        processed_count = len(kept_words)
        removed_count = len(removed_words)
        preserved_count = len(preserved_words)
        
        return {
            "original_text": text,
            "processed_text": processed_text,
            "method_used": "context_aware",
            "words_removed": removed_words,
            "words_preserved": preserved_words,
            "statistics": {
                "original_word_count": original_count,
                "processed_word_count": processed_count,
                "words_removed_count": removed_count,
                "words_preserved_count": preserved_count,
                "stopword_removal_rate": (removed_count / original_count * 100) if original_count > 0 else 0.0
            }
        }
