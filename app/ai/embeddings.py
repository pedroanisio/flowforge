"""
Chain Embeddings System

Creates vector representations of chains for similarity analysis and recommendations.
"""
import numpy as np
from typing import List, Dict, Any, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json

from ..models.chain import ChainDefinition


class ChainEmbeddings:
    """Generate and compare chain embeddings"""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=100,
            ngram_range=(1, 2)
        )
        self.fitted = False
        self.chain_vectors = {}

    def _chain_to_text(self, chain: ChainDefinition) -> str:
        """Convert chain to text representation for embedding"""
        components = []

        # Add chain metadata
        components.append(f"name: {chain.name}")
        components.append(f"description: {chain.description}")

        # Add plugin sequence
        plugin_sequence = []
        for node in chain.nodes:
            if node.plugin_id:
                plugin_sequence.append(node.plugin_id)
        components.append(f"plugins: {' '.join(plugin_sequence)}")

        # Add tags
        if chain.tags:
            components.append(f"tags: {' '.join(chain.tags)}")

        # Add node types
        node_types = [node.type.value for node in chain.nodes]
        components.append(f"node_types: {' '.join(node_types)}")

        return " ".join(components)

    def fit(self, chains: List[ChainDefinition]):
        """Fit the vectorizer on a collection of chains"""
        texts = [self._chain_to_text(chain) for chain in chains]

        if len(texts) > 0:
            self.vectorizer.fit(texts)
            self.fitted = True

            # Store vectors for each chain
            for chain, text in zip(chains, texts):
                vector = self.vectorizer.transform([text]).toarray()[0]
                self.chain_vectors[chain.id] = vector

    def embed_chain(self, chain: ChainDefinition) -> np.ndarray:
        """Get embedding vector for a chain"""
        if not self.fitted:
            # If not fitted, return zero vector
            return np.zeros(100)

        text = self._chain_to_text(chain)
        vector = self.vectorizer.transform([text]).toarray()[0]
        return vector

    def find_similar_chains(
        self,
        chain: ChainDefinition,
        all_chains: List[ChainDefinition],
        top_k: int = 5
    ) -> List[Tuple[ChainDefinition, float]]:
        """Find chains similar to the given chain"""
        if not all_chains:
            return []

        # Fit if not already fitted
        if not self.fitted:
            self.fit(all_chains)

        # Get embedding for target chain
        target_vector = self.embed_chain(chain)

        # Calculate similarities
        similarities = []
        for other_chain in all_chains:
            if other_chain.id == chain.id:
                continue  # Skip self

            other_vector = self.embed_chain(other_chain)
            similarity = cosine_similarity(
                target_vector.reshape(1, -1),
                other_vector.reshape(1, -1)
            )[0][0]

            similarities.append((other_chain, float(similarity)))

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def get_plugin_similarity(self, plugin1: str, plugin2: str) -> float:
        """Get similarity score between two plugins based on usage patterns"""
        # Simple similarity based on co-occurrence in chains
        # In a real system, this would use more sophisticated embeddings

        if plugin1 == plugin2:
            return 1.0

        # For now, return a dummy similarity
        # This would be enhanced with actual usage pattern analysis
        return 0.5

    def cluster_chains(self, chains: List[ChainDefinition], n_clusters: int = 5) -> Dict[int, List[str]]:
        """Cluster chains into similar groups"""
        if not chains or len(chains) < n_clusters:
            return {0: [c.id for c in chains]}

        try:
            from sklearn.cluster import KMeans

            # Fit and get embeddings
            self.fit(chains)
            vectors = [self.embed_chain(chain) for chain in chains]

            # Cluster
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(vectors)

            # Group chains by cluster
            clusters = {}
            for chain, label in zip(chains, labels):
                label = int(label)
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(chain.id)

            return clusters
        except Exception:
            # Fallback if clustering fails
            return {0: [c.id for c in chains]}
