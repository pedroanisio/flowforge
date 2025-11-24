# FlowForge
## AI-Powered Workflow Automation Platform

[![Status](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> **Build intelligent document workflows in minutes. Drag, drop, automate. Let AI optimize your pipelines.**

FlowForge is a FastAPI-based workflow automation platform that enables you to create document processing pipelines through a visual chain builder with AI-powered optimization and intelligent recommendations.

---

## ✨ Key Features

### 🎯 Core Capabilities
- **Visual Workflow Builder** - Drag-and-drop interface for creating complex pipelines
- **10 Pre-built Plugins** - Ready-to-use text processing, document conversion, and NLP tools
- **Type-Safe Architecture** - Pydantic models ensure data validation throughout
- **Container Orchestration** - Docker-based services for specialized processing
- **Real-time Execution** - Parallel processing with dependency resolution

### 🤖 AI-Powered Intelligence
- **Execution Prediction** - ML-based time estimates with confidence scores
- **Plugin Recommendations** - Smart suggestions using TF-IDF embeddings
- **Chain Optimization** - Automatic redundancy removal and parallelization
- **Pattern Learning** - Learns from successful workflow executions
- **Analytics Dashboard** - Visualize performance and identify bottlenecks

### 🔒 Enterprise Ready
- **JWT Authentication** - OAuth2-compatible security (optional)
- **API Rate Limiting** - Prevent abuse with per-endpoint limits
- **File Streaming** - Handle large files efficiently (chunked uploads)
- **Structured Logging** - JSON logging for production monitoring
- **CI/CD Pipeline** - Automated testing and quality checks

---

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/pedroanisio/dwp.git
cd dwp

# Start all services
docker compose up -d

# Access the application
open http://localhost:8000
```

**That's it!** The platform is now running with all services.

### Manual Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
npm install

# Build CSS
npm run build-css

# Start the server
uvicorn app.main:app --reload --port 8000
```

---

## 📸 Screenshots

### Visual Chain Builder
Create workflows by connecting plugins in a visual interface with real-time validation.

### AI Analytics Dashboard
Monitor performance, identify bottlenecks, and get AI-powered insights.

### Plugin Execution
Execute individual plugins or complex chains with instant results.

---

## 📦 Available Plugins

| Plugin | Category | Description |
|--------|----------|-------------|
| **text_stat** | Analysis | Comprehensive text statistics and metrics |
| **pandoc_converter** | Conversion | Universal document format conversion |
| **pdf2html** | Conversion | PDF to HTML (container-based) |
| **json_to_xml** | Transformation | JSON to XML conversion |
| **xml_to_json** | Transformation | XML to JSON conversion |
| **doc_viewer** | Utilities | Document viewing and metadata |
| **web_sentence_analyzer** | NLP | Advanced sentence analysis |
| **bag_of_words** | NLP | Text feature extraction |
| **context_aware_stopwords** | NLP | Intelligent stopword removal |
| **sentence_merger** | NLP | Sentence combination strategies |

---

## 🔧 Usage Examples

### Execute a Single Plugin

```python
import requests

# Execute text statistics plugin
response = requests.post(
    "http://localhost:8000/api/plugin/text_stat/execute",
    json={"text": "Hello, world! This is a test."}
)

result = response.json()
print(result["data"]["word_count"])  # 6
```

### Create and Execute a Chain

```python
# Create a chain
chain = {
    "name": "Document Analysis Pipeline",
    "nodes": [
        {
            "id": "node1",
            "type": "plugin",
            "plugin_id": "doc_viewer",
            "position": {"x": 100, "y": 100}
        },
        {
            "id": "node2",
            "type": "plugin",
            "plugin_id": "text_stat",
            "position": {"x": 300, "y": 100}
        }
    ],
    "connections": [
        {
            "source_node_id": "node1",
            "target_node_id": "node2",
            "data_mapping": {"content": "text"}
        }
    ]
}

# Save chain
response = requests.post(
    "http://localhost:8000/api/chains",
    json={"definition": chain}
)

chain_id = response.json()["chain_id"]

# Execute chain
response = requests.post(
    f"http://localhost:8000/api/chains/{chain_id}/execute",
    json={"input": "your data here"}
)

print(response.json())
```

### Get AI Recommendations

```python
# Get plugin suggestions
response = requests.get(
    f"http://localhost:8000/api/ai/chains/{chain_id}/suggestions"
)

suggestions = response.json()["suggestions"]
for suggestion in suggestions:
    print(f"{suggestion['plugin_id']} ({suggestion['confidence']*100:.0f}%): {suggestion['reason']}")
```

---

## 🛠️ Development

### Project Structure

```
dwp/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── core/                   # Core functionality
│   │   ├── plugin_manager.py  # Plugin system
│   │   ├── chain_executor.py  # Workflow execution
│   │   └── auth.py             # Authentication
│   ├── ai/                     # AI/ML features
│   │   ├── chain_optimizer.py # Workflow optimization
│   │   ├── plugin_recommender.py
│   │   └── execution_predictor.py
│   ├── models/                 # Pydantic models
│   ├── plugins/                # Plugin implementations
│   └── templates/              # HTML templates
├── tests/                      # Test suite
├── docs/                       # Documentation
└── requirements.txt            # Dependencies
```

### Creating a New Plugin

1. **Create plugin directory**:
   ```bash
   mkdir app/plugins/my_plugin
   ```

2. **Create `manifest.json`**:
   ```json
   {
     "id": "my_plugin",
     "name": "My Plugin",
     "description": "What it does",
     "inputs": [
       {
         "name": "text",
         "type": "text",
         "required": true
       }
     ]
   }
   ```

3. **Implement `plugin.py`**:
   ```python
   from ...models.plugin import BasePlugin, BasePluginResponse

   class MyPluginResponse(BasePluginResponse):
       result: str

   class Plugin(BasePlugin):
       @classmethod
       def get_response_model(cls):
           return MyPluginResponse

       def execute(self, data):
           return {"result": data["text"].upper()}
   ```

4. **Test your plugin**:
   ```bash
   pytest tests/unit/test_my_plugin.py
   ```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 📊 API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/plugins` | List all available plugins |
| `POST` | `/api/plugin/{id}/execute` | Execute a single plugin |
| `GET` | `/api/chains` | List all chains |
| `POST` | `/api/chains` | Create a new chain |
| `POST` | `/api/chains/{id}/execute` | Execute a chain |
| `GET` | `/api/chains/{id}/analytics` | Get chain analytics |

### AI Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/ai/chains/{id}/optimize` | Optimize chain |
| `GET` | `/api/ai/chains/{id}/predictions` | Predict execution time |
| `GET` | `/api/ai/chains/{id}/suggestions` | Get plugin suggestions |
| `GET` | `/api/ai/insights/system` | System-wide insights |

**Full API documentation**: http://localhost:8000/docs (Swagger UI)

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific tests
pytest tests/unit/test_plugins.py
```

**Current test coverage**: 70%+ (goal: 80%+)

---

## 📚 Documentation

- **[Architecture](docs/ARCHITECTURE.md)** - System design and components
- **[AI Features](docs/AI_FEATURES.md)** - AI/ML capabilities
- **[Security](docs/SECURITY.md)** - Security best practices
- **[UI Guide](docs/UI_GUIDE.md)** - User interface documentation
- **[Contributing](CONTRIBUTING.md)** - Contribution guidelines
- **[Changelog](CHANGELOG.md)** - Version history

---

## 🔐 Configuration

Create a `.env` file for configuration:

```bash
# Authentication (optional)
ENABLE_AUTH=false
SECRET_KEY=your-secret-key-here

# Rate Limiting
RATE_LIMIT_ENABLED=true
DEFAULT_RATE_LIMIT=100/minute

# File Uploads
MAX_UPLOAD_SIZE_MB=100

# Environment
ENVIRONMENT=development
```

See [`.env.example`](.env.example) for all options.

---

## 🐳 Docker Deployment

### Production Build
```bash
docker compose up -d
```

### Development Build
```bash
docker compose -f docker-compose.yml --profile dev up -d
```

### Environment Variables
```bash
docker compose up -d \
  -e ENABLE_AUTH=true \
  -e SECRET_KEY=your-secret-key
```

---

## 🚦 Status & Roadmap

**Current Version**: 2.0.0 (Active Development)

### ✅ Implemented
- ✓ Visual workflow builder
- ✓ 10 production-ready plugins
- ✓ AI-powered optimization
- ✓ Execution prediction
- ✓ Plugin recommendations
- ✓ Analytics dashboard
- ✓ JWT authentication
- ✓ Container orchestration

### 🔜 Planned (v2.1)
- WebSocket real-time updates
- Background job queue
- Plugin marketplace
- Advanced ML models (GPT-based)
- Multi-tenancy support

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md).

### Ways to Contribute
- 🐛 Report bugs
- 💡 Suggest features
- 📝 Improve documentation
- 🔌 Create plugins
- ✅ Write tests
- 🎨 Enhance UI

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation
- [Fabric.js](http://fabricjs.com/) - Canvas manipulation
- [Chart.js](https://www.chartjs.org/) - Data visualization
- [Tailwind CSS](https://tailwindcss.com/) - Styling
- [scikit-learn](https://scikit-learn.org/) - Machine learning

---

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/pedroanisio/dwp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/pedroanisio/dwp/discussions)

---

## ⭐ Star History

If you find this project useful, please consider giving it a star! ⭐

---

**Made with ❤️ by Pedro Anisio and contributors**

*FlowForge - Build Intelligent Workflows*
