"""
Plugin Recommendation System

Suggests next plugins based on historical patterns and chain similarity.
"""
from typing import List, Dict, Tuple, Optional
from collections import Counter, defaultdict

from ..models.chain import ChainDefinition
from .execution_history import ExecutionHistoryManager, ExecutionRecord
from .embeddings import ChainEmbeddings


class PluginRecommender:
    """Recommends plugins based on usage patterns"""

    def __init__(self, history_manager: Optional[ExecutionHistoryManager] = None):
        self.history_manager = history_manager or ExecutionHistoryManager()
        self.embeddings = ChainEmbeddings()

    def suggest_next_plugin(
        self,
        current_chain: ChainDefinition,
        all_chains: List[ChainDefinition],
        top_k: int = 5
    ) -> List[Tuple[str, float, str]]:
        """
        Suggest next plugin to add to chain

        Returns: List of (plugin_id, confidence, reason) tuples
        """
        suggestions = []

        # Strategy 1: Find similar chains and see what plugins they use
        similar_suggestions = self._suggest_from_similar_chains(
            current_chain, all_chains, top_k
        )
        suggestions.extend(similar_suggestions)

        # Strategy 2: Common plugin sequences from history
        sequence_suggestions = self._suggest_from_sequences(current_chain, top_k)
        suggestions.extend(sequence_suggestions)

        # Strategy 3: Plugin co-occurrence patterns
        cooccurrence_suggestions = self._suggest_from_cooccurrence(current_chain, top_k)
        suggestions.extend(cooccurrence_suggestions)

        # Aggregate suggestions and calculate final scores
        plugin_scores = defaultdict(lambda: {"score": 0.0, "reasons": []})

        for plugin_id, score, reason in suggestions:
            plugin_scores[plugin_id]["score"] += score
            plugin_scores[plugin_id]["reasons"].append(reason)

        # Convert to list and sort
        final_suggestions = []
        for plugin_id, data in plugin_scores.items():
            avg_score = data["score"] / len(data["reasons"])
            reason = "; ".join(set(data["reasons"]))
            final_suggestions.append((plugin_id, avg_score, reason))

        final_suggestions.sort(key=lambda x: x[1], reverse=True)

        return final_suggestions[:top_k]

    def _suggest_from_similar_chains(
        self,
        chain: ChainDefinition,
        all_chains: List[ChainDefinition],
        top_k: int
    ) -> List[Tuple[str, float, str]]:
        """Suggest plugins from similar chains"""
        suggestions = []

        # Get current plugins in chain
        current_plugins = set(
            node.plugin_id for node in chain.nodes if node.plugin_id
        )

        # Find similar chains
        similar_chains = self.embeddings.find_similar_chains(chain, all_chains, top_k=10)

        # Count plugins in similar chains that aren't in current chain
        plugin_counts = Counter()
        for similar_chain, similarity in similar_chains:
            for node in similar_chain.nodes:
                if node.plugin_id and node.plugin_id not in current_plugins:
                    plugin_counts[node.plugin_id] += similarity

        # Convert to suggestions
        for plugin_id, score in plugin_counts.most_common(top_k):
            confidence = min(score / len(similar_chains), 1.0)
            suggestions.append((
                plugin_id,
                confidence,
                f"Used in {int(score * 100)}% of similar chains"
            ))

        return suggestions

    def _suggest_from_sequences(
        self,
        chain: ChainDefinition,
        top_k: int
    ) -> List[Tuple[str, float, str]]:
        """Suggest plugins based on common sequences"""
        suggestions = []

        # Get current plugin sequence
        current_plugins = [node.plugin_id for node in chain.nodes if node.plugin_id]

        if not current_plugins:
            return suggestions

        # Get execution history
        executions = self.history_manager.get_successful_executions(limit=1000)

        # Find sequences that match the current chain
        next_plugin_counts = Counter()
        matching_sequences = 0

        for execution in executions:
            plugins = execution.plugins_used

            # Check if execution contains current sequence
            if len(plugins) > len(current_plugins):
                # Check if it starts with or contains our sequence
                for i in range(len(plugins) - len(current_plugins)):
                    if plugins[i:i+len(current_plugins)] == current_plugins:
                        # Get next plugin in sequence
                        next_plugin = plugins[i + len(current_plugins)]
                        if next_plugin not in current_plugins:
                            next_plugin_counts[next_plugin] += 1
                            matching_sequences += 1

        # Convert to suggestions
        if matching_sequences > 0:
            for plugin_id, count in next_plugin_counts.most_common(top_k):
                confidence = count / matching_sequences
                suggestions.append((
                    plugin_id,
                    confidence,
                    f"Follows this sequence in {count} historical executions"
                ))

        return suggestions

    def _suggest_from_cooccurrence(
        self,
        chain: ChainDefinition,
        top_k: int
    ) -> List[Tuple[str, float, str]]:
        """Suggest plugins that commonly appear together with current plugins"""
        suggestions = []

        # Get current plugins
        current_plugins = set(node.plugin_id for node in chain.nodes if node.plugin_id)

        if not current_plugins:
            return suggestions

        # Get execution history
        executions = self.history_manager.get_successful_executions(limit=1000)

        # Count co-occurrences
        cooccurrence_counts = Counter()
        chains_with_current = 0

        for execution in executions:
            plugins_set = set(execution.plugins_used)

            # Check if execution contains any of our current plugins
            if current_plugins & plugins_set:
                chains_with_current += 1
                # Count other plugins in the chain
                for plugin in plugins_set:
                    if plugin not in current_plugins:
                        cooccurrence_counts[plugin] += 1

        # Convert to suggestions
        if chains_with_current > 0:
            for plugin_id, count in cooccurrence_counts.most_common(top_k):
                confidence = count / chains_with_current
                suggestions.append((
                    plugin_id,
                    confidence,
                    f"Co-occurs in {int(confidence * 100)}% of chains with your plugins"
                ))

        return suggestions

    def suggest_starter_plugins(self, top_k: int = 5) -> List[Tuple[str, float, str]]:
        """Suggest plugins for starting a new chain"""
        executions = self.history_manager.get_successful_executions(limit=1000)

        # Count first plugins in successful chains
        first_plugin_counts = Counter()
        for execution in executions:
            if execution.plugins_used:
                first_plugin_counts[execution.plugins_used[0]] += 1

        # Convert to suggestions
        total = sum(first_plugin_counts.values())
        suggestions = []

        for plugin_id, count in first_plugin_counts.most_common(top_k):
            confidence = count / total if total > 0 else 0
            suggestions.append((
                plugin_id,
                confidence,
                f"Commonly used to start chains ({count} times)"
            ))

        return suggestions

    def suggest_compatible_plugins(
        self,
        plugin_id: str,
        all_plugins: List[str],
        top_k: int = 5
    ) -> List[Tuple[str, float, str]]:
        """Suggest plugins that work well with a specific plugin"""
        executions = self.history_manager.get_executions_for_plugin(plugin_id, limit=1000)

        # Count plugins that appear with the target plugin
        compatible_counts = Counter()
        for execution in executions:
            if execution.success:
                for other_plugin in execution.plugins_used:
                    if other_plugin != plugin_id:
                        compatible_counts[other_plugin] += 1

        # Convert to suggestions
        total = len(executions)
        suggestions = []

        for other_plugin, count in compatible_counts.most_common(top_k):
            confidence = count / total if total > 0 else 0
            suggestions.append((
                other_plugin,
                confidence,
                f"Works well with {plugin_id} ({int(confidence * 100)}% success rate)"
            ))

        return suggestions
