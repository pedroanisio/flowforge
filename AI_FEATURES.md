# 🧠 AI-Powered Optimization & Auto-Tuning

## Overview

The Neural Plugin System now includes **AI-powered optimization and auto-tuning** capabilities that learn from historical executions to provide intelligent recommendations, performance predictions, and automatic optimizations.

## 🌟 Key Features

### 1. **Chain Optimization**
Automatically analyzes and optimizes chains for better performance.

### 2. **Plugin Recommendations**
Suggests next plugins based on similar chains and usage patterns.

### 3. **Execution Time Prediction**
Predicts how long a chain will take to execute and identifies bottlenecks.

### 4. **Strategy Recommendation**
Recommends optimal processing strategies based on input characteristics.

### 5. **Pattern Learning**
Identifies common patterns in successful chains.

### 6. **Performance Insights**
Provides detailed analytics about plugin and chain performance.

---

## 📡 AI API Endpoints

### Chain Optimization

**POST** `/api/ai/chains/{chain_id}/optimize`

Analyzes and optimizes a chain for better performance.

```bash
curl -X POST http://localhost:8000/api/ai/chains/chain-123/optimize
```

**Response:**
```json
{
  "success": true,
  "original_prediction": {
    "predicted_duration_seconds": 45.2,
    "confidence": 0.85
  },
  "optimized_chain": {...},
  "optimized_prediction": {
    "predicted_duration_seconds": 22.3,
    "confidence": 0.85
  },
  "improvements": [
    {
      "type": "redundancy_removal",
      "description": "Removed 2 redundant nodes",
      "impact": "medium"
    }
  ],
  "expected_speedup": 2.03,
  "time_saved_seconds": 22.9
}
```

### Execution Time Prediction

**GET** `/api/ai/chains/{chain_id}/predictions?input_size_bytes=1048576`

Predicts execution time and identifies bottlenecks.

```bash
curl http://localhost:8000/api/ai/chains/chain-123/predictions?input_size_bytes=1048576
```

**Response:**
```json
{
  "success": true,
  "prediction": {
    "predicted_duration_seconds": 45.2,
    "predicted_duration_human": "0:00:45",
    "confidence_interval": [38.5, 52.1],
    "node_predictions": {
      "node1": 15.3,
      "node2": 29.9
    },
    "bottlenecks": ["node2"],
    "confidence": 0.85,
    "based_on_executions": 127
  }
}
```

### Plugin Suggestions

**GET** `/api/ai/chains/{chain_id}/suggestions?top_k=5`

Get AI-powered suggestions for next plugin to add to chain.

```bash
curl http://localhost:8000/api/ai/chains/chain-123/suggestions?top_k=5
```

**Response:**
```json
{
  "success": true,
  "suggestions": [
    {
      "plugin_id": "pandoc_converter",
      "confidence": 0.92,
      "reason": "Used in 92% of similar chains; Follows this sequence in 45 historical executions",
      "confidence_label": "high"
    },
    {
      "plugin_id": "text_stat",
      "confidence": 0.78,
      "reason": "Co-occurs in 78% of chains with your plugins",
      "confidence_label": "medium"
    }
  ]
}
```

### Starter Plugin Suggestions

**GET** `/api/ai/suggestions/starter-plugins?top_k=5`

Get suggestions for starting a new chain.

```bash
curl http://localhost:8000/api/ai/suggestions/starter-plugins?top_k=5
```

**Response:**
```json
{
  "success": true,
  "suggestions": [
    {
      "plugin_id": "pdf2html",
      "confidence": 0.45,
      "reason": "Commonly used to start chains (234 times)",
      "confidence_label": "medium"
    },
    {
      "plugin_id": "text_stat",
      "confidence": 0.32,
      "reason": "Commonly used to start chains (167 times)",
      "confidence_label": "low"
    }
  ]
}
```

### Find Similar Chains

**GET** `/api/ai/chains/{chain_id}/similar?top_k=5`

Find chains similar to the given chain using AI embeddings.

```bash
curl http://localhost:8000/api/ai/chains/chain-123/similar?top_k=5
```

**Response:**
```json
{
  "success": true,
  "similar_chains": [
    {
      "chain_id": "chain-456",
      "chain_name": "PDF Analysis Pipeline",
      "similarity_score": 0.89,
      "predicted_duration": 32.1,
      "num_nodes": 4,
      "tags": ["pdf", "analysis"]
    }
  ]
}
```

### Strategy Recommendation

**GET** `/api/ai/plugins/{plugin_id}/strategy?input_size_bytes=10485760`

Get optimal processing strategy recommendation.

```bash
curl "http://localhost:8000/api/ai/plugins/pandoc_converter/strategy?input_size_bytes=10485760"
```

**Response:**
```json
{
  "success": true,
  "recommendation": {
    "recommended_strategy": "chunked",
    "confidence": 0.85,
    "reason": "File size requires chunked processing for memory efficiency",
    "alternatives": [
      {
        "strategy": "text_extraction",
        "reason": "Extract text only (fast, reduced features)"
      }
    ]
  }
}
```

### Plugin Insights

**GET** `/api/ai/plugins/{plugin_id}/insights`

Get AI-powered insights about a plugin.

```bash
curl http://localhost:8000/api/ai/plugins/text_stat/insights
```

**Response:**
```json
{
  "success": true,
  "insights": {
    "plugin_id": "text_stat",
    "performance": {
      "total_executions": 523,
      "average_duration": 1.2,
      "success_rate": 0.98
    },
    "compatible_plugins": [
      {
        "plugin_id": "pandoc_converter",
        "compatibility_score": 0.87,
        "reason": "Works well with text_stat (87% success rate)"
      }
    ],
    "usage_rank": 2
  }
}
```

### Chain Patterns

**GET** `/api/ai/patterns`

Get AI-identified common chain patterns.

```bash
curl http://localhost:8000/api/ai/patterns
```

**Response:**
```json
{
  "success": true,
  "patterns": {
    "total_patterns": 15,
    "top_patterns": [
      {
        "pattern": "pdf2html -> text_stat -> pandoc_converter",
        "frequency": 45,
        "example_chains": ["chain-123", "chain-456", "chain-789"]
      }
    ],
    "most_common": {
      "pattern": "pdf2html -> text_stat -> pandoc_converter",
      "frequency": 45
    }
  }
}
```

### System Insights

**GET** `/api/ai/insights/system`

Get system-wide AI insights.

```bash
curl http://localhost:8000/api/ai/insights/system
```

**Response:**
```json
{
  "success": true,
  "insights": {
    "total_executions": 1523,
    "total_processing_time_hours": 12.5,
    "average_execution_time_seconds": 29.6,
    "most_used_plugins": [
      {"plugin_id": "text_stat", "usage_count": 523},
      {"plugin_id": "pandoc_converter", "usage_count": 412}
    ],
    "slow_plugins": [
      {
        "plugin_id": "pandoc_converter",
        "average_duration": 45.2,
        "p95_duration": 120.5
      }
    ],
    "patterns_identified": 15
  }
}
```

### Execution History

**GET** `/api/ai/execution-history?limit=50`

Get execution history for analysis.

```bash
# All executions
curl http://localhost:8000/api/ai/execution-history?limit=50

# For specific chain
curl http://localhost:8000/api/ai/execution-history?chain_id=chain-123&limit=50

# For specific plugin
curl http://localhost:8000/api/ai/execution-history?plugin_id=text_stat&limit=50
```

---

## 💻 Python SDK Usage

### Import AI Components

```python
from app.ai.chain_optimizer import ChainOptimizer
from app.ai.plugin_recommender import PluginRecommender
from app.ai.execution_predictor import ExecutionPredictor
from app.ai.strategy_recommender import StrategyRecommender
```

### Initialize Optimizer

```python
optimizer = ChainOptimizer()
```

### Optimize a Chain

```python
chain = chain_manager.load_chain("chain-123")
all_chains = chain_manager.list_chains()

result = optimizer.optimize_chain(chain, all_chains)

print(f"Expected speedup: {result['expected_speedup']}x")
print(f"Time saved: {result['time_saved_seconds']}s")
```

### Predict Execution Time

```python
chain = chain_manager.load_chain("chain-123")
prediction = optimizer.predict_execution(chain, input_size_bytes=1048576)

print(f"Predicted duration: {prediction['predicted_duration_seconds']}s")
print(f"Confidence: {prediction['confidence']}")
print(f"Bottlenecks: {prediction['bottlenecks']}")
```

### Get Plugin Recommendations

```python
chain = chain_manager.load_chain("chain-123")
all_chains = chain_manager.list_chains()

suggestions = optimizer.suggest_next_plugins(chain, all_chains, top_k=5)

for suggestion in suggestions:
    print(f"{suggestion['plugin_id']}: {suggestion['confidence']} - {suggestion['reason']}")
```

### Recommend Processing Strategy

```python
recommendation = optimizer.recommend_strategy(
    plugin_id="pandoc_converter",
    input_size_bytes=10 * 1024 * 1024  # 10MB
)

print(f"Recommended: {recommendation['recommended_strategy']}")
print(f"Reason: {recommendation['reason']}")
```

---

## 🧪 How It Works

### 1. Execution History Collection

Every chain execution is automatically recorded with:
- Execution time and success status
- Plugin sequence used
- Input file size
- Node-level performance metrics

This data is stored in `app/data/execution_history/executions.jsonl`.

### 2. Machine Learning Models

#### **Chain Embeddings**
- Uses TF-IDF vectorization to create embeddings of chains
- Enables similarity search and pattern matching
- Clusters similar chains for analysis

#### **Execution Time Prediction**
- Statistical models based on historical performance
- Considers: plugin sequence, input size, historical variance
- Provides confidence intervals

#### **Pattern Recognition**
- Analyzes successful chain sequences
- Identifies common plugin combinations
- Tracks co-occurrence patterns

#### **Strategy Selection**
- Rule-based system (extensible to ML)
- Considers: input size, plugin capabilities, historical performance
- Recommends optimal processing approach

### 3. Recommendation Engine

Combines multiple signals:
- **Similarity**: Finds chains similar to current
- **Sequences**: Learns from successful patterns
- **Co-occurrence**: Tracks plugins that work well together
- **Performance**: Weighs by success rate and speed

---

## 📊 Data & Privacy

### Data Stored

- Chain execution metadata (no file contents)
- Performance metrics
- Plugin usage patterns
- Success/failure rates

### Data Location

```
app/data/execution_history/
└── executions.jsonl
```

### Data Retention

- Unlimited retention by default
- Use cleanup API to clear history if needed

### Privacy

- No sensitive data stored
- No file contents recorded
- Only metadata and performance metrics

---

## 🎯 Best Practices

### 1. Build History First

AI features improve with more execution history. Run chains regularly to build data.

### 2. Review Suggestions

AI suggestions are recommendations, not requirements. Review before applying.

### 3. Monitor Confidence

Pay attention to confidence scores:
- **High (0.8+)**: Strong recommendation
- **Medium (0.5-0.8)**: Consider carefully
- **Low (<0.5)**: Use with caution

### 4. Iterate

- Try AI suggestions
- Review results
- Refine based on outcomes

### 5. Combine with Human Expertise

AI augments human decision-making, doesn't replace it.

---

## 🔧 Configuration

### Disable AI Features

```python
# In app/core/config.py
class Settings(BaseSettings):
    enable_ai: bool = Field(default=True, env="ENABLE_AI")
```

```bash
# Disable via environment variable
export ENABLE_AI=false
```

### Adjust Learning Parameters

```python
# app/ai/embeddings.py
vectorizer = TfidfVectorizer(
    max_features=100,  # Adjust for more/less granularity
    ngram_range=(1, 2) # Word pairs
)
```

---

## 🚀 Performance Impact

### Memory Usage
- **Execution History**: ~1KB per execution
- **Embeddings**: ~10KB per chain when fitted
- **Total**: Minimal (<100MB for 10,000 executions)

### API Latency
- **Predictions**: <50ms
- **Recommendations**: <100ms
- **Optimization**: <200ms

### Background Impact
- History recording: <5ms per execution
- No blocking operations
- Async where possible

---

## 🐛 Troubleshooting

### No Suggestions Returned

**Cause**: Insufficient execution history

**Solution**: Run more chains to build history, or use starter suggestions

### Low Confidence Scores

**Cause**: Limited similar data

**Solution**: Build more diverse execution history

### Inaccurate Predictions

**Cause**: Different input patterns than historical data

**Solution**: Provide input_size_bytes for better predictions

### Import Errors

**Cause**: Missing ML dependencies

**Solution**:
```bash
pip install -r requirements.txt
```

---

## 📚 Examples

### Example 1: Optimize Before Running

```python
# Load chain
chain = chain_manager.load_chain("my-chain")

# Get optimization
result = optimizer.optimize_chain(chain, chain_manager.list_chains())

# Save optimized version
if result["expected_speedup"] > 1.5:
    optimized_chain = result["optimized_chain"]
    chain_manager.save_chain(optimized_chain)
```

### Example 2: Smart Chain Builder

```python
# Start new chain
chain = chain_manager.create_chain("Smart PDF Analysis")

# Get starter suggestions
starters = optimizer.suggest_starter_plugins(top_k=1)
first_plugin = starters[0]["plugin_id"]

# Add first plugin
chain.nodes.append(ChainNode(
    id="node1",
    type=ChainNodeType.PLUGIN,
    plugin_id=first_plugin
))

# Get next suggestions
suggestions = optimizer.suggest_next_plugins(chain, chain_manager.list_chains(), top_k=3)

# Add suggested plugins
for suggestion in suggestions:
    if suggestion["confidence"] > 0.7:
        chain.nodes.append(ChainNode(
            id=f"node{len(chain.nodes) + 1}",
            type=ChainNodeType.PLUGIN,
            plugin_id=suggestion["plugin_id"]
        ))

chain_manager.save_chain(chain)
```

### Example 3: Performance Monitoring

```python
# Get system insights
insights = optimizer.get_system_insights()

print(f"Total executions: {insights['total_executions']}")
print(f"Most used: {insights['most_used_plugins'][0]['plugin_id']}")

# Identify slow plugins
for slow in insights['slow_plugins']:
    print(f"⚠️ {slow['plugin_id']}: {slow['p95_duration']}s (P95)")
```

---

## 🎓 Advanced Topics

### Custom ML Models

Replace the simple heuristics with trained ML models:

```python
# app/ai/execution_predictor.py
from sklearn.ensemble import RandomForestRegressor

class MLExecutionPredictor(ExecutionPredictor):
    def __init__(self):
        super().__init__()
        self.model = RandomForestRegressor()
        self._train_model()

    def _train_model(self):
        # Load execution history
        executions = self.history_manager.get_all_executions(limit=10000)

        # Extract features
        X = self._extract_features(executions)
        y = [e.duration_seconds for e in executions]

        # Train
        self.model.fit(X, y)
```

### Integration with External ML Platforms

```python
# Use Hugging Face models for better embeddings
from transformers import AutoModel, AutoTokenizer

model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
```

---

## 📖 API Reference

Full API documentation available at `/docs` (FastAPI auto-generated).

---

**AI Features Version**: 1.0.0
**Last Updated**: January 2025
