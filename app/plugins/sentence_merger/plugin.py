import re
import json
import time
from typing import Dict, Any, Type, List, Optional, Union
from collections import defaultdict, Counter
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity
import spacy
from pydantic import BaseModel, Field

from ...models.plugin import BasePlugin, BasePluginResponse
from .models import SentenceMergerResponse, SentenceCluster


class SentenceMergerInput(BaseModel):
    text: str = Field(
        default="",
        max_length=500000,
        json_schema_extra={
            "label": "Text to Analyze",
            "field_type": "textarea",
            "placeholder": "Enter your text here for sentence merging analysis...",
            "help": "Input text will be automatically split into sentences. Alternatively, use the sentences field for pre-split sentences.",
        },
    )
    sentences: Optional[Union[str, List[str]]] = Field(
        default=None,
        json_schema_extra={
            "label": "Pre-split Sentences (JSON Array)",
            "field_type": "textarea",
            "placeholder": "[\"First sentence.\", \"Second sentence.\", \"Third sentence.\"]",
            "help": "Optional: Provide sentences as a JSON array. If provided, this takes precedence over the text field.",
        },
    )
    similarity_threshold: float = Field(
        default=0.68,
        ge=0.1,
        le=0.99,
        json_schema_extra={
            "label": "Similarity Threshold",
            "field_type": "number",
            "placeholder": "0.68",
            "validation": {"step": 0.01},
            "help": "Similarity threshold for clustering (0.1-0.99). Lower values (0.6-0.7) merge more aggressively, higher values (0.75-0.9) are more conservative. Default 0.68 balances quality and reduction.",
        },
    )


class SentenceMerger:
    def __init__(self, similarity_threshold=0.68):  # Lowered from 0.8
        # Load pre-trained sentence transformer model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        # Load spacy model with error handling
        try:
            self.nlp = spacy.load('en_core_web_sm')
        except OSError:
            # Fallback if model not available
            self.nlp = None
        self.similarity_threshold = similarity_threshold
    
    def preprocess_text(self, text: str) -> str:
        """Enhanced text preprocessing to clean and normalize text"""
        # Remove problematic line breaks and normalize whitespace
        text = re.sub(r'\r\n|\r|\n', ' ', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Clean up punctuation spacing
        text = re.sub(r'\s+([.!?])', r'\1', text)
        # Ensure single space after sentence endings
        text = re.sub(r'([.!?])\s*', r'\1 ', text)
        return text.strip()
    
    def get_embeddings(self, sentences):
        """Generate embeddings for sentences"""
        # Preprocess sentences before embedding
        preprocessed = [self.preprocess_text(sent) for sent in sentences]
        return self.model.encode(preprocessed)
    
    def cluster_similar_sentences(self, sentences, embeddings):
        """Cluster sentences based on semantic similarity with improved algorithm"""
        if len(sentences) <= 1:
            return {0: sentences}
            
        # Calculate similarity matrix
        similarity_matrix = cosine_similarity(embeddings)
        
        # Use hierarchical clustering with ward linkage for better results
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=1-self.similarity_threshold,
            metric='precomputed',
            linkage='average'  # Could experiment with 'ward' but needs euclidean distance
        )
        
        # Convert similarity to distance
        distance_matrix = 1 - similarity_matrix
        clusters = clustering.fit_predict(distance_matrix)
        
        # Group sentences by cluster
        clustered_sentences = defaultdict(list)
        for idx, cluster_id in enumerate(clusters):
            clustered_sentences[cluster_id].append(sentences[idx])
        
        return dict(clustered_sentences)
    
    def extract_key_phrases(self, sentences):
        """Enhanced key phrase extraction with better filtering"""
        if not self.nlp:
            # Improved fallback without spacy
            text = " ".join(sentences)
            words = re.findall(r'\b\w+\b', text.lower())
            # Filter out common stopwords and short words
            stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'}
            word_counts = Counter(w for w in words if len(w) > 2 and w not in stopwords)
            return [word for word, count in word_counts.most_common(5) if count > 1]
        
        text = " ".join(sentences)
        doc = self.nlp(text)
        
        key_phrases = []
        
        # Extract meaningful noun phrases (filter out short/generic ones)
        for chunk in doc.noun_chunks:
            phrase = chunk.text.lower().strip()
            if len(phrase) > 3 and not phrase.startswith(('the ', 'a ', 'an ')):
                key_phrases.append(phrase)
        
        # Extract named entities
        for ent in doc.ents:
            if ent.label_ in ['PERSON', 'ORG', 'PRODUCT', 'TECH']:  # Focus on relevant entities
                phrase = ent.text.lower().strip()
                if phrase not in key_phrases and len(phrase) > 2:
                    key_phrases.append(phrase)
        
        # Extract important keywords based on POS tags
        important_words = []
        for token in doc:
            if (token.pos_ in ['NOUN', 'PROPN', 'ADJ'] and 
                len(token.text) > 3 and 
                not token.is_stop and 
                not token.is_punct):
                important_words.append(token.lemma_.lower())
        
        # Add frequent important words
        word_counts = Counter(important_words)
        for word, count in word_counts.most_common(3):
            if count > 1 and word not in key_phrases:
                key_phrases.append(word)
        
        return list(set(key_phrases[:8]))  # Limit to 8 most relevant phrases
    
    def calculate_cluster_similarity(self, sentences, embeddings):
        """Calculate average similarity within a cluster"""
        if len(sentences) <= 1:
            return 1.0
            
        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = cosine_similarity([embeddings[i]], [embeddings[j]])[0][0]
                similarities.append(sim)
        
        return np.mean(similarities) if similarities else 1.0
    
    def merge_cluster(self, sentences):
        """Enhanced merging strategy that intelligently combines sentences"""
        if len(sentences) == 1:
            return self.preprocess_text(sentences[0])
        
        # Preprocess all sentences
        clean_sentences = [self.preprocess_text(sent) for sent in sentences]
        
        if not self.nlp:
            # Simple fallback: return the longest, most informative sentence
            return max(clean_sentences, key=lambda x: len(x.split()))
        
        # Analyze sentences for intelligent merging
        sentence_docs = [self.nlp(sent) for sent in clean_sentences]
        
        # Find the most comprehensive sentence as base
        base_idx = 0
        max_info = 0
        for i, doc in enumerate(sentence_docs):
            # Score based on named entities, important keywords, and length
            score = (len([ent for ent in doc.ents]) * 2 + 
                    len([token for token in doc if token.pos_ in ['NOUN', 'PROPN', 'VERB']]) +
                    len(doc) * 0.1)
            if score > max_info:
                max_info = score
                base_idx = i
        
        base_sentence = clean_sentences[base_idx]
        base_doc = sentence_docs[base_idx]
        
        # Extract key concepts from base sentence
        base_concepts = set()
        for token in base_doc:
            if not token.is_stop and not token.is_punct and len(token.text) > 2:
                base_concepts.add(token.lemma_.lower())
        
        # Find additional unique information from other sentences
        additional_info = []
        for i, doc in enumerate(sentence_docs):
            if i == base_idx:
                continue
                
            # Find unique concepts not in base
            unique_concepts = set()
            for token in doc:
                if (not token.is_stop and not token.is_punct and 
                    len(token.text) > 2 and 
                    token.lemma_.lower() not in base_concepts):
                    unique_concepts.add(token.lemma_.lower())
            
            # If significant unique content, consider adding key phrases
            if len(unique_concepts) >= 2:
                # Extract the most important unique phrase
                for chunk in doc.noun_chunks:
                    chunk_lemmas = {token.lemma_.lower() for token in chunk if not token.is_stop}
                    if chunk_lemmas & unique_concepts and len(chunk.text.strip()) > 3:
                        additional_info.append(chunk.text.strip())
                        break
        
        # Combine information intelligently
        if additional_info:
            # Remove period from base and add additional info
            base_clean = base_sentence.rstrip('.')
            # Add unique information as additional clauses
            unique_additions = []
            for info in additional_info[:2]:  # Limit to 2 additions
                if info.lower() not in base_clean.lower():
                    unique_additions.append(info)
            
            if unique_additions:
                combined = f"{base_clean}, incorporating {', '.join(unique_additions)}."
                # Clean up grammar
                combined = re.sub(r',\s*,', ',', combined)  # Remove double commas
                return combined
        
        return base_sentence
    
    def merge_sentences(self, sentences):
        """Main method to merge similar sentences with enhanced processing"""
        if not sentences:
            return [], {}
            
        # Generate embeddings
        embeddings = self.get_embeddings(sentences)
        
        # Cluster similar sentences
        clusters = self.cluster_similar_sentences(sentences, embeddings)
        
        # Merge each cluster and collect details
        merged_sentences = []
        cluster_details = []
        
        for cluster_id, cluster_sentences in clusters.items():
            # Get embeddings for this cluster
            cluster_indices = [i for i, sent in enumerate(sentences) if sent in cluster_sentences]
            cluster_embeddings = [embeddings[i] for i in cluster_indices]
            
            # Merge the cluster
            merged = self.merge_cluster(cluster_sentences)
            merged_sentences.append(merged)
            
            # Calculate cluster statistics
            similarity_score = self.calculate_cluster_similarity(cluster_sentences, cluster_embeddings)
            key_phrases = self.extract_key_phrases(cluster_sentences)
            
            cluster_details.append({
                'cluster_id': cluster_id,
                'sentences': cluster_sentences,
                'merged_sentence': merged,
                'similarity_score': similarity_score,
                'key_phrases': key_phrases
            })
        
        return merged_sentences, cluster_details


class Plugin(BasePlugin):
    """Enhanced Sentence Merger Plugin - Merges similar sentences using advanced semantic clustering"""

    @classmethod
    def get_input_model(cls) -> Type[BaseModel]:
        """Return the canonical input model for this plugin."""
        return SentenceMergerInput
    
    @classmethod
    def get_response_model(cls) -> Type[BasePluginResponse]:
        """Return the Pydantic model for this plugin's response"""
        return SentenceMergerResponse
    
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the enhanced sentence merger analysis
        
        Args:
            data: Dictionary containing 'text' or 'sentences' and optional 'similarity_threshold'
            
        Returns:
            Dictionary with sentence merger analysis that validates against SentenceMergerResponse
        """
        start_time = time.time()
        
        # Extract input parameters with improved defaults
        text = data.get('text', '')
        sentences_input = data.get('sentences', [])
        similarity_threshold = float(data.get('similarity_threshold', 0.68))  # Lowered default
        
        # Parse sentences from text or use provided sentences list
        if text and not sentences_input:
            # Split text into sentences using improved regex
            sentences = self._split_into_sentences(text)
        elif sentences_input:
            sentences = self._normalize_sentences_input(sentences_input)
        else:
            sentences = []
        
        # Enhanced sentence cleaning
        cleaned_sentences = []
        for sent in sentences:
            # Remove citation markers and clean formatting
            cleaned = re.sub(r'\[cite:.*?\]', '', sent)
            cleaned = re.sub(r'\r\n|\r|\n', ' ', cleaned)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            
            # Filter out very short or low-quality sentences
            if cleaned and len(cleaned) > 15 and len(cleaned.split()) > 3:
                cleaned_sentences.append(cleaned)
        
        original_count = len(cleaned_sentences)
        
        if original_count == 0:
            return {
                "original_sentence_count": 0,
                "merged_sentence_count": 0,
                "reduction_percentage": 0.0,
                "similarity_threshold": similarity_threshold,
                "clusters": [],
                "merged_sentences": [],
                "processing_stats": {
                    "processing_time_seconds": time.time() - start_time,
                    "embedding_time_seconds": 0.0,
                    "clustering_time_seconds": 0.0
                }
            }
        
        # Initialize merger with improved parameters
        embedding_start = time.time()
        merger = SentenceMerger(similarity_threshold=similarity_threshold)
        embedding_time = time.time() - embedding_start
        
        # Process sentences
        clustering_start = time.time()
        merged_sentences, cluster_details = merger.merge_sentences(cleaned_sentences)
        clustering_time = time.time() - clustering_start
        
        merged_count = len(merged_sentences)
        reduction_percentage = ((original_count - merged_count) / original_count * 100) if original_count > 0 else 0.0
        
        total_time = time.time() - start_time
        
        return {
            "original_sentence_count": original_count,
            "merged_sentence_count": merged_count,
            "reduction_percentage": round(reduction_percentage, 2),
            "similarity_threshold": similarity_threshold,
            "clusters": cluster_details,
            "merged_sentences": sorted(merged_sentences),  # Sort for consistency
            "processing_stats": {
                "processing_time_seconds": round(total_time, 3),
                "embedding_time_seconds": round(embedding_time, 3),
                "clustering_time_seconds": round(clustering_time, 3)
            }
        }

    def _normalize_sentences_input(self, sentences_input: Union[str, List[str]]) -> List[str]:
        """Normalize `sentences` from JSON array text, newline text, or list input."""
        if isinstance(sentences_input, str):
            raw = sentences_input.strip()
            if not raw:
                return []

            parsed_values: Optional[List[Any]] = None
            if raw.startswith("["):
                try:
                    parsed_candidate = json.loads(raw)
                    if isinstance(parsed_candidate, list):
                        parsed_values = parsed_candidate
                except json.JSONDecodeError:
                    parsed_values = None

            if parsed_values is None:
                parsed_values = [segment for segment in re.split(r'[\r\n]+', raw) if segment]

            return [str(item).strip() for item in parsed_values if str(item).strip()]

        if isinstance(sentences_input, list):
            return [str(item).strip() for item in sentences_input if str(item).strip()]

        return []
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Enhanced sentence splitting with better handling of edge cases"""
        # Improved sentence splitting that handles abbreviations and edge cases
        text = re.sub(r'\r\n|\r|\n', ' ', text)  # Normalize line breaks
        
        # First, protect common abbreviations by temporarily replacing them
        abbreviations = {
            r'\bDr\.': 'Dr___TEMP___',
            r'\bMr\.': 'Mr___TEMP___',
            r'\bMrs\.': 'Mrs___TEMP___',
            r'\bMs\.': 'Ms___TEMP___',
            r'\bProf\.': 'Prof___TEMP___',
            r'\bvs\.': 'vs___TEMP___',
            r'\betc\.': 'etc___TEMP___',
            r'\bi\.e\.': 'ie___TEMP___',
            r'\be\.g\.': 'eg___TEMP___'
        }
        
        # Temporarily replace abbreviations
        for abbrev_pattern, replacement in abbreviations.items():
            text = re.sub(abbrev_pattern, replacement, text)
        
        # Split on sentence-ending punctuation followed by whitespace and capital letter
        sentences = re.split(r'\.\s+(?=[A-Z])', text)
        
        # Also split on other sentence endings
        all_sentences = []
        for sent in sentences:
            # Split on ! and ? as well
            sub_sentences = re.split(r'[!?]\s+(?=[A-Z])', sent)
            all_sentences.extend(sub_sentences)
        
        # Restore abbreviations
        final_sentences = []
        for sent in all_sentences:
            # Restore each abbreviation
            sent = sent.replace('Dr___TEMP___', 'Dr.')
            sent = sent.replace('Mr___TEMP___', 'Mr.')
            sent = sent.replace('Mrs___TEMP___', 'Mrs.')
            sent = sent.replace('Ms___TEMP___', 'Ms.')
            sent = sent.replace('Prof___TEMP___', 'Prof.')
            sent = sent.replace('vs___TEMP___', 'vs.')
            sent = sent.replace('etc___TEMP___', 'etc.')
            sent = sent.replace('ie___TEMP___', 'i.e.')
            sent = sent.replace('eg___TEMP___', 'e.g.')
            final_sentences.append(sent.strip())
        
        return [s for s in final_sentences if s.strip()] 
