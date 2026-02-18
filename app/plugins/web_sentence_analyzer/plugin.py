import re
from typing import Dict, Any, List, Optional, Type
from collections import Counter
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import nltk
from nltk.tokenize import sent_tokenize
from urllib.parse import urlparse
import logging
from pydantic import BaseModel, Field
from dataclasses import dataclass, field
from ...models.plugin import BasePlugin, BasePluginResponse


class NodeAnalysis:
    """Analysis data for a DOM node"""
    def __init__(self, element: Tag, text_length: int, child_count: int, depth: int):
        self.element = element
        self.text_length = text_length
        self.child_count = child_count
        self.depth = depth
        self.text_density = self._calculate_text_density()
        self.content_score = self._calculate_content_score()
    
    def _calculate_text_density(self) -> float:
        """Calculate text-to-HTML ratio"""
        html_length = len(str(self.element))
        return self.text_length / html_length if html_length > 0 else 0
    
    def _calculate_content_score(self) -> float:
        """Calculate overall content score using multiple factors"""
        # Base score from text length (logarithmic scale for diminishing returns)
        import math
        length_score = min(math.log(self.text_length + 1) / math.log(2000), 1.0)
        
        # Text density bonus (higher is better, but cap it)
        density_score = min(self.text_density * 3, 1.0)
        
        # Depth penalty (deeper nodes are less likely to be main content)
        depth_penalty = max(0.1, 1 - (self.depth * 0.15))
        
        # Child count factor (moderate number of children is good)
        if self.child_count == 0:
            child_score = 0.7  # Leaf nodes can be good (paragraphs)
        elif 1 <= self.child_count <= 5:
            child_score = 1.0  # Optimal structure
        elif 6 <= self.child_count <= 15:
            child_score = 0.8  # Still good
        else:
            child_score = max(0.2, 1 - (self.child_count * 0.03))  # Penalize too many children
        
        # Navigation penalty - check for navigation-heavy content
        element_text = self.element.get_text().lower()
        nav_keywords = ['home', 'menu', 'search', 'login', 'sdk', 'github', 'api', 'guide']
        nav_penalty = 1.0
        nav_count = sum(1 for keyword in nav_keywords if keyword in element_text)
        if nav_count > 3:  # High navigation keyword density
            nav_penalty = max(0.3, 1 - (nav_count * 0.1))
        
        # Repetition penalty - check for repeated text patterns
        words = element_text.split()
        if len(words) > 10:
            word_counts = {}
            for word in words:
                if len(word) > 3:  # Only count substantial words
                    word_counts[word] = word_counts.get(word, 0) + 1
            
            # Calculate repetition ratio
            max_repetitions = max(word_counts.values()) if word_counts else 1
            repetition_penalty = max(0.5, 1 - (max_repetitions / len(words)))
        else:
            repetition_penalty = 1.0
        
        # Bonus for substantial content
        substantial_bonus = 1.2 if self.text_length > 1000 else 1.0
        
        base_score = (length_score * 0.30 + density_score * 0.20 + 
                     depth_penalty * 0.20 + child_score * 0.15 + 
                     nav_penalty * 0.10 + repetition_penalty * 0.05)
        
        return min(base_score * substantial_bonus, 1.0)


class SentenceInfo(BaseModel):
    """Model for individual sentence information"""
    rank: int = Field(..., description="Ranking by frequency")
    sentence: str = Field(..., description="The sentence text")
    frequency: int = Field(..., description="How many times this sentence appears")


class WebSentenceAnalyzerResponse(BasePluginResponse):
    """Pydantic model for web sentence analyzer plugin response"""
    url: str = Field(..., description="The analyzed URL")
    page_title: str = Field(..., description="Title of the webpage")
    total_sentences: int = Field(..., description="Total number of sentences found")
    unique_sentences: int = Field(..., description="Number of unique sentences")
    total_text_length: int = Field(..., description="Total character count of extracted text")
    average_sentence_length: float = Field(..., description="Average length of sentences in characters")
    most_common_sentences: List[SentenceInfo] = Field(..., description="List of sentences sorted by frequency")
    content_nodes_found: int = Field(..., description="Number of content-rich nodes identified")
    
    # Optional error field for handling error cases
    error: Optional[str] = Field(None, description="Error message if analysis failed")


class WebSentenceAnalyzerInput(BaseModel):
    url: str = Field(
        ...,
        min_length=8,
        max_length=2000,
        json_schema_extra={
            "label": "Website URL",
            "field_type": "text",
            "placeholder": "https://example.com",
            "help": "Enter the full URL of the webpage you want to analyze (must include http:// or https://)",
        },
    )
    max_sentences: int = Field(
        default=50,
        ge=1,
        le=1000,
        json_schema_extra={
            "label": "Maximum Sentences to Return",
            "field_type": "number",
            "help": "Limit the number of sentences in the results (default: 50)",
        },
    )
    min_sentence_length: int = Field(
        default=10,
        ge=1,
        le=200,
        json_schema_extra={
            "label": "Minimum Sentence Length",
            "field_type": "number",
            "help": "Filter out sentences shorter than this number of characters (default: 10)",
        },
    )


@dataclass
class AnalyzerConfig:
    """Configuration class for DOMContentAnalyzer"""
    max_content_size: int = 10 * 1024 * 1024  # 10MB
    request_timeout: int = 30
    min_content_length: int = 100
    max_nodes: int = 5
    min_sentence_length: int = 10
    max_sentences: int = 50
    chunk_size: int = 8192
    
    # Navigation patterns for filtering
    navigation_patterns: List[str] = field(default_factory=lambda: [
        r'skip to (?:main )?content',
        r'skip to navigation',
        r'menu',
        r'home\s+news\s+sport\s+business',
        r'sign in|log in|register|subscribe',
        r'search|newsletter|follow us',
        r'privacy policy|terms of service|cookie policy',
        r'contact us|about us|help|support',
        r'previous|next|more stories',
        r'share this|tweet|facebook|linkedin',
        r'advertisement|sponsored content',
        r'related articles|you may also like|recommended',
        r'^\s*\d+\s*$',  # Just numbers
        # Enhanced patterns for modern web UI
        r'search\.\.\.',
        r'home page',
        r'copy page',
        r'on this page',
        r'⌘\s*[A-Z]',  # Keyboard shortcuts
        r'ctrl\+[A-Z]',
        r'github\s+github',
        r'yes\s+no\s+for',
        r'was this page helpful',
        r'get started',
        r'learn more',
        r'view\s+(?:all|more|list)',
        r'check out',
        r'dive deeper',
        r'explore\s+\w+',
        r'sdk.*sdk.*sdk',  # Multiple SDK mentions
        r'^\s*[▪•·‣⁃]\s*',  # Bullet points
        r'click here',
        r'read more',
        r'show more'
    ])
    
    excluded_tags: List[str] = field(default_factory=lambda: [
        'script', 'style', 'noscript', 'nav', 'header', 'footer',
        'aside', 'iframe', 'svg', 'form', 'input', 'button', 'comment'
    ])


class DOMContentAnalyzer:
    """Enhanced DOM Content Analyzer with security, performance, and configuration improvements"""
    
    def __init__(self, config: Optional[AnalyzerConfig] = None):
        self.config = config or AnalyzerConfig()
        self.logger = logging.getLogger(__name__)
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create configured requests session"""
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=3)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        return session
    
    def _fetch_safely(self, url: str) -> requests.Response:
        """Fetch URL with size limits and safety checks"""
        with self.session.get(url, timeout=self.config.request_timeout, stream=True) as response:
            response.raise_for_status()
            
            # Check content length
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) > self.config.max_content_size:
                raise ValueError(f"Content too large: {content_length} bytes (max: {self.config.max_content_size})")
            
            # Read content with size limit
            content = b''
            for chunk in response.iter_content(chunk_size=self.config.chunk_size):
                content += chunk
                if len(content) > self.config.max_content_size:
                    raise ValueError(f"Content exceeds {self.config.max_content_size} bytes")
            
            # Create new response with content
            response._content = content
            return response
    
    def _get_text_content(self, element: Tag) -> str:
        """Extract text without expensive copy operations"""
        texts = []
        for el in element.descendants:
            if isinstance(el, NavigableString) and el.parent.name not in self.config.excluded_tags:
                text = el.strip()
                if text:
                    texts.append(text)
        
        combined_text = ' '.join(texts)
        return re.sub(r'\s+', ' ', combined_text).strip()
    
    def _preprocess_text_for_tokenization(self, text: str) -> str:
        """Clean and preprocess text before sentence tokenization"""
        if not text:
            return text
        
        # Remove zero-width and formatting Unicode characters (comprehensive)
        text = re.sub(r'[\u200b-\u200f\u2028-\u202f\ufeff\u00ad\u061c\u180e\u2060-\u2064\u206a-\u206f]', '', text)
        
        # Extra aggressive removal of zero-width space if still present
        text = text.replace('\u200b', '')
        
        # Clean up common web UI artifacts
        text = re.sub(r'⌘\s*[A-Z]', '', text)  # Keyboard shortcuts
        text = re.sub(r'Ctrl\+[A-Z]', '', text)
        text = re.sub(r'search\.\.\.\s*', '', text, flags=re.IGNORECASE)
        
        # Remove repeated navigation text patterns
        text = re.sub(r'(\b\w+\b)(\s+\1){2,}', r'\1', text)  # Remove triple+ repetitions
        
        # Clean up excessive whitespace and punctuation
        text = re.sub(r'\s{3,}', ' ', text)  # Multiple spaces to single
        text = re.sub(r'\.{3,}', '...', text)  # Multiple dots to ellipsis
        text = re.sub(r'[!]{2,}', '!', text)  # Multiple exclamations
        text = re.sub(r'[?]{2,}', '?', text)  # Multiple questions
        
        # Remove standalone navigation fragments
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            # Skip lines that are just navigation or UI elements
            if (len(line) < 5 or 
                re.match(r'^[A-Z\s]+$', line) or  # All caps short lines
                re.match(r'^[\d\s\-]+$', line) or  # Just numbers and dashes
                line.lower() in ['home', 'menu', 'search', 'login', 'help']):
                continue
            cleaned_lines.append(line)
        
        text = ' '.join(cleaned_lines)
        return re.sub(r'\s+', ' ', text).strip()
    
    def _filter_navigation_text(self, text: str) -> str:
        """Filter out navigation and boilerplate text patterns"""
        if not text:
            return text
        
        # Check if entire text matches navigation patterns
        text_lower = text.lower()
        for pattern in self.config.navigation_patterns:
            if re.search(pattern, text_lower):
                if len(text) < 200:  # Short navigation text
                    return ""
        
        # Split into sentences and filter each
        sentences = text.split('.')
        filtered_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:  # Too short
                continue
                
            sentence_lower = sentence.lower()
            is_navigation = False
            
            for pattern in self.config.navigation_patterns:
                if re.search(pattern, sentence_lower):
                    is_navigation = True
                    break
            
            if not is_navigation:
                filtered_sentences.append(sentence)
        
        return '. '.join(filtered_sentences).strip()
    
    def _analyze_dom_node(self, element: Tag, depth: int = 0) -> Optional[NodeAnalysis]:
        """Analyze a single DOM node for content richness"""
        if not isinstance(element, Tag) or element.name in self.config.excluded_tags:
            return None
        
        # Skip common navigation containers by class/id
        if self._is_likely_navigation_container(element):
            return None
        
        # Get text content using optimized method
        text_content = self._get_text_content(element)
        text_content = self._filter_navigation_text(text_content)
        text_length = len(text_content)
        
        # Skip nodes with insufficient text
        if text_length < 50:
            return None
        
        # Skip if text appears to be mostly navigation
        if self._is_mostly_navigation_text(text_content):
            return None
        
        # Count direct children that are tags
        child_count = len([child for child in element.children if isinstance(child, Tag)])
        
        return NodeAnalysis(element, text_length, child_count, depth)
    
    def _is_likely_navigation_container(self, element: Tag) -> bool:
        """Check if element is likely a navigation container"""
        if not element.get('class') and not element.get('id'):
            return False
        
        classes = ' '.join(element.get('class', [])).lower()
        element_id = element.get('id', '').lower()
        combined = f"{classes} {element_id}"
        
        nav_indicators = [
            'nav', 'menu', 'header', 'footer', 'sidebar', 'aside',
            'breadcrumb', 'pagination', 'toolbar', 'topbar', 'bottombar',
            'social', 'share', 'follow', 'subscribe', 'newsletter',
            'ad', 'ads', 'advertisement', 'promo', 'sponsor',
            'related', 'recommend', 'similar', 'trending', 'popular'
        ]
        
        return any(indicator in combined for indicator in nav_indicators)
    
    def _is_mostly_navigation_text(self, text: str) -> bool:
        """Check if text is mostly navigation content"""
        if len(text) < 100:
            return False
        
        # Count navigation-like sentences
        sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 5]
        if len(sentences) < 3:
            return False
        
        nav_sentence_count = 0
        for sentence in sentences:
            sentence_lower = sentence.lower()
            for pattern in self.config.navigation_patterns:
                if re.search(pattern, sentence_lower):
                    nav_sentence_count += 1
                    break
        
        # If more than 50% are navigation sentences, consider it mostly navigation
        return nav_sentence_count / len(sentences) > 0.5
    
    def _find_content_nodes(self, soup: BeautifulSoup) -> List[NodeAnalysis]:
        """Find all nodes with significant text content"""
        content_nodes = []
        
        def traverse_dom(element: Tag, depth: int = 0):
            """Recursively traverse DOM and analyze nodes"""
            analysis = self._analyze_dom_node(element, depth)
            if analysis and analysis.text_length >= self.config.min_content_length:
                content_nodes.append(analysis)
            
            # Traverse children
            for child in element.children:
                if isinstance(child, Tag):
                    traverse_dom(child, depth + 1)
        
        # Start traversal from body or html
        start_element = soup.find('body') or soup.find('html') or soup
        if isinstance(start_element, Tag):
            traverse_dom(start_element)
        
        return content_nodes
    
    def _select_best_content_nodes(self, content_nodes: List[NodeAnalysis]) -> List[NodeAnalysis]:
        """Select the best content nodes, avoiding nested duplicates"""
        if not content_nodes:
            return []
        
        # Sort by content score
        sorted_nodes = sorted(content_nodes, key=lambda x: x.content_score, reverse=True)
        selected_nodes = []
        
        for node in sorted_nodes:
            if len(selected_nodes) >= self.config.max_nodes:
                break
            
            # Check if this node is nested within any already selected node
            is_nested = False
            for selected in selected_nodes:
                if self._is_nested_within(node.element, selected.element):
                    is_nested = True
                    break
            
            # Also check if any selected node is nested within this node
            nested_indices = []
            for i, selected in enumerate(selected_nodes):
                if self._is_nested_within(selected.element, node.element):
                    nested_indices.append(i)
            
            if nested_indices:
                # Remove nested nodes and add this one
                for i in reversed(nested_indices):
                    selected_nodes.pop(i)
                selected_nodes.append(node)
            elif not is_nested:
                selected_nodes.append(node)
        
        return selected_nodes
    
    def _is_nested_within(self, child_element: Tag, parent_element: Tag) -> bool:
        """Check if child_element is nested within parent_element"""
        current = child_element.parent
        while current:
            if current == parent_element:
                return True
            current = current.parent
        return False
    
    def _extract_content_from_nodes(self, content_nodes: List[NodeAnalysis]) -> str:
        """Extract and combine text from selected content nodes"""
        if not content_nodes:
            return ""
        
        content_parts = []
        for node in content_nodes:
            text = self._get_text_content(node.element)
            if text and text not in content_parts:  # Avoid duplicates
                content_parts.append(text)
        
        return ' '.join(content_parts)
    
    def _filter_low_quality_sentences(self, sentences: List[str]) -> List[str]:
        """Filter out low-quality sentences after tokenization"""
        filtered_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Skip very short sentences that are likely fragments
            if len(sentence) < 15:
                continue
            
            # Skip sentences with too many non-alphabetic characters
            alpha_ratio = sum(c.isalpha() for c in sentence) / len(sentence)
            if alpha_ratio < 0.5:
                continue
            
            # Skip sentences that are mostly navigation
            sentence_lower = sentence.lower()
            nav_word_count = 0
            nav_keywords = [
                'home', 'menu', 'search', 'login', 'register', 'subscribe',
                'contact', 'about', 'help', 'support', 'privacy', 'terms',
                'github', 'sdk', 'api', 'documentation', 'guide', 'tutorial',
                'quickstart', 'example', 'learn', 'explore', 'check', 'view'
            ]
            
            words = sentence_lower.split()
            for word in words:
                if word in nav_keywords:
                    nav_word_count += 1
            
            # If more than 40% of words are navigation keywords, skip
            if len(words) > 0 and nav_word_count / len(words) > 0.4:
                continue
            
            # Skip sentences with unusual patterns
            if (re.search(r'^\s*[A-Z\s]{10,}$', sentence) or  # Long all-caps
                re.search(r'[⌘]', sentence) or  # Keyboard shortcuts
                sentence.count('...') > 2 or  # Too many ellipses
                sentence.lower().startswith(('copy ', 'click ', 'view ', 'see ')) and len(sentence) < 50):
                continue
            
            # Skip sentences that look like lists or navigation items
            if (sentence.count(' ') < 3 and 
                any(word in sentence.lower() for word in ['sdk', 'api', 'home', 'menu', 'search'])):
                continue
                
            filtered_sentences.append(sentence)
        
        return filtered_sentences
    
    def analyze(self, url: str, max_sentences: Optional[int] = None, min_sentence_length: Optional[int] = None) -> Dict[str, Any]:
        """
        Analyze web page using enhanced DOM-based content extraction
        
        Args:
            url: URL to analyze
            max_sentences: Override config max_sentences
            min_sentence_length: Override config min_sentence_length
        
        Returns:
            Dictionary with analysis results
        """
        # Use config defaults or override values
        max_sentences = max_sentences or self.config.max_sentences
        min_sentence_length = min_sentence_length or self.config.min_sentence_length
        
        # Validate inputs
        if not url or not self._is_valid_url(url):
            return {
                "url": url,
                "page_title": "",
                "total_sentences": 0,
                "unique_sentences": 0,
                "total_text_length": 0,
                "average_sentence_length": 0.0,
                "most_common_sentences": [],
                "content_nodes_found": 0,
                "error": "Invalid URL provided"
            }
        
        # Clamp parameters
        max_sentences = max(1, min(max_sentences, 500))
        min_sentence_length = max(5, min(min_sentence_length, 200))
        
        try:
            # Fetch webpage safely
            response = self._fetch_safely(url)
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'html' not in content_type:
                return {
                    "url": url,
                    "page_title": "",
                    "total_sentences": 0,
                    "unique_sentences": 0,
                    "total_text_length": 0,
                    "average_sentence_length": 0.0,
                    "most_common_sentences": [],
                    "content_nodes_found": 0,
                    "error": f"Not an HTML page: {content_type}"
                }
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get title
            title_tag = soup.find('title')
            page_title = title_tag.get_text().strip() if title_tag else urlparse(url).netloc
            
            # Find content-rich nodes
            self.logger.info(f"Analyzing DOM structure for {url}")
            content_nodes = self._find_content_nodes(soup)
            
            if not content_nodes:
                return {
                    "url": url,
                    "page_title": page_title,
                    "total_sentences": 0,
                    "unique_sentences": 0,
                    "total_text_length": 0,
                    "average_sentence_length": 0.0,
                    "most_common_sentences": [],
                    "content_nodes_found": 0,
                    "error": "No content-rich nodes found in DOM"
                }
            
            # Select best content nodes
            best_nodes = self._select_best_content_nodes(content_nodes)
            self.logger.info(f"Found {len(content_nodes)} content nodes, selected {len(best_nodes)} best nodes")
            
            # Extract text from selected nodes
            text_content = self._extract_content_from_nodes(best_nodes)
            
            if not text_content:
                return {
                    "url": url,
                    "page_title": page_title,
                    "total_sentences": 0,
                    "unique_sentences": 0,
                    "total_text_length": 0,
                    "average_sentence_length": 0.0,
                    "most_common_sentences": [],
                    "content_nodes_found": len(content_nodes),
                    "error": "No text content extracted from content nodes"
                }
            
            # Preprocess text for better sentence tokenization
            preprocessed_text = self._preprocess_text_for_tokenization(text_content)
            
            # Tokenize sentences
            sentences = sent_tokenize(preprocessed_text)
            
            # Apply post-processing quality filter
            sentences = self._filter_low_quality_sentences(sentences)
            
            # Filter sentences by length
            valid_sentences = [
                sentence.strip() 
                for sentence in sentences 
                if len(sentence.strip()) >= min_sentence_length
            ]
            
            if not valid_sentences:
                return {
                    "url": url,
                    "page_title": page_title,
                    "total_sentences": len(sentences),
                    "unique_sentences": 0,
                    "total_text_length": len(text_content),
                    "average_sentence_length": 0.0,
                    "most_common_sentences": [],
                    "content_nodes_found": len(content_nodes),
                    "error": f"No sentences found with minimum length of {min_sentence_length} characters"
                }
            
            # Count sentence frequencies
            normalized_for_counting = [s.lower().strip() for s in valid_sentences]
            sentence_counts = Counter(normalized_for_counting)
            
            # Map back to original sentences
            original_sentences = {}
            for original, normalized in zip(valid_sentences, normalized_for_counting):
                if normalized not in original_sentences:
                    original_sentences[normalized] = original
            
            # Get most common sentences
            most_common = sentence_counts.most_common(max_sentences)
            
            most_common_sentences = [
                {
                    "rank": idx + 1,
                    "sentence": original_sentences[normalized_sentence],
                    "frequency": count
                }
                for idx, (normalized_sentence, count) in enumerate(most_common)
            ]
            
            # Calculate statistics
            total_length = sum(len(s) for s in valid_sentences)
            avg_length = total_length / len(valid_sentences) if valid_sentences else 0
            
            return {
                "url": url,
                "page_title": page_title,
                "total_sentences": len(sentences),
                "unique_sentences": len(sentence_counts),
                "total_text_length": len(text_content),
                "average_sentence_length": round(avg_length, 2),
                "most_common_sentences": most_common_sentences,
                "content_nodes_found": len(content_nodes)
            }
            
        except requests.RequestException as e:
            return {
                "url": url,
                "page_title": "",
                "total_sentences": 0,
                "unique_sentences": 0,
                "total_text_length": 0,
                "average_sentence_length": 0.0,
                "most_common_sentences": [],
                "content_nodes_found": 0,
                "error": f"Failed to fetch webpage: {str(e)}"
            }
        except Exception as e:
            self.logger.error(f"Analysis failed for {url}: {e}")
            return {
                "url": url,
                "page_title": "",
                "total_sentences": 0,
                "unique_sentences": 0,
                "total_text_length": 0,
                "average_sentence_length": 0.0,
                "most_common_sentences": [],
                "content_nodes_found": 0,
                "error": f"Analysis failed: {str(e)}"
            }
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([
                result.scheme in ['http', 'https'],
                result.netloc,
                '.' in result.netloc
            ])
        except Exception:
            return False


class Plugin(BasePlugin):
    """Enhanced Web Sentence Analyzer Plugin - Advanced DOM-based content extraction"""
    
    def __init__(self):
        """Initialize the plugin with enhanced DOM analyzer and NLTK setup"""
        # Configure logging
        self.logger = logging.getLogger(__name__)
        
        # Ensure NLTK punkt tokenizer is available
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            self.logger.info("Downloading NLTK punkt tokenizer...")
            nltk.download('punkt', quiet=True)
        
        # Initialize DOM content analyzer
        self.analyzer = DOMContentAnalyzer()

    @classmethod
    def get_input_model(cls) -> Type[BaseModel]:
        """Return the canonical input model for this plugin."""
        return WebSentenceAnalyzerInput
    
    @classmethod
    def get_response_model(cls) -> Type[BasePluginResponse]:
        """Return the Pydantic model for this plugin's response"""
        return WebSentenceAnalyzerResponse
    
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute comprehensive web page sentence analysis using enhanced DOM-based extraction
        
        Args:
            data: Dictionary containing 'url' and optional parameters
            
        Returns:
            Dictionary with comprehensive sentence analysis results that validates against WebSentenceAnalyzerResponse
        """
        # Extract and validate parameters with bounds checking
        url = str(data.get('url', '')).strip()
        max_sentences = min(max(int(data.get('max_sentences', 50)), 10), 500)
        min_sentence_length = min(max(int(data.get('min_sentence_length', 10)), 5), 100)
        
        # Validate URL
        if not url:
            return {
                "url": "",
                "page_title": "",
                "total_sentences": 0,
                "unique_sentences": 0,
                "total_text_length": 0,
                "average_sentence_length": 0.0,
                "most_common_sentences": [],
                "content_nodes_found": 0,
                "error": "No URL provided for analysis"
            }
        
        # Use the enhanced DOM analyzer
        return self.analyzer.analyze(url, max_sentences, min_sentence_length) 
