
# 🚀 **What is this Repository?**

This is a **Neural Plugin System with Chain Builder** - a sophisticated, modern web application that features:

- **Dynamic Plugin System**: Plugins are discovered and loaded at runtime
- **Visual Chain Builder**: Create complex workflows by connecting plugins visually
- **Type-Safe Architecture**: Built with FastAPI and Pydantic for robust validation
- **Manifest-Driven UI**: Each plugin defines its own interface through JSON manifests

## 🏗️ **Architecture Overview**

### **Core Components:**

1. **FastAPI Backend** (`app/main.py`):
   - REST API with 40+ endpoints
   - Web interface with Jinja2 templates
   - File handling and download management

2. **Plugin System** (`app/core/`):
   - `plugin_manager.py`: Plugin execution and compliance checking
   - `plugin_loader.py`: Dynamic plugin discovery and loading
   - `chain_manager.py`: Chain workflow management
   - `chain_executor.py`: Chain execution engine
   - `chain_storage.py`: Chain persistence

3. **Data Models** (`app/models/`):
   - `plugin.py`: Base plugin classes and validation models
   - `chain.py`: Chain definition and execution models
   - `response.py`: API response structures

4. **Plugin Ecosystem** (`app/plugins/`):
   - 9 pre-built plugins covering various use cases
   - Each plugin has its own directory with `manifest.json` and `plugin.py`

## 🔌 **Plugin Architecture**

### **Plugin Structure:**
Each plugin consists of:

1. **`manifest.json`**: Defines the plugin's UI, inputs, outputs, and metadata
2. **`plugin.py`**: Contains the plugin logic and response model

### **Example Plugin Structure:**
```12:30:app/plugins/text_stat/plugin.py
class TextStatResponse(BasePluginResponse):
    """Pydantic model for text statistics plugin response"""
    character_count: int = Field(..., description="Total number of characters including spaces and punctuation")
    character_count_no_spaces: int = Field(..., description="Total number of characters excluding spaces")
    word_count: int = Field(..., description="Total number of words")
    # ... more fields
```

### **Mandatory Response Model Rule:**
🔒 **ALL PLUGINS MUST DEFINE PYDANTIC RESPONSE MODELS** - This ensures:
- Type safety and validation
- Consistent API structure
- Self-documenting response formats
- Chain compatibility

## 📦 **Available Plugins** (9 total):

1. **`text_stat`**: Text statistics analyzer
2. **`pandoc_converter`**: Document format converter
3. **`json_to_xml`**: JSON to XML converter
4. **`xml_to_json`**: XML to JSON converter
5. **`doc_viewer`**: Document viewer and analyzer
6. **`web_sentence_analyzer`**: Sentence analysis with NLP
7. **`sentence_merger`**: Sentence merging utilities
8. **`context_aware_stopwords`**: Context-aware stopword processing
9. **`bag_of_words`**: Bag-of-words text processing

## 🔗 **Chain Builder System**

The system allows creating complex workflows by:
- **Visual Interface**: Drag-and-drop plugin connections at `/chain-builder`
- **Data Flow Validation**: Ensures output types match input requirements
- **Template System**: Pre-built chains for common workflows
- **Execution History**: Track and analyze chain performance

## 🛠️ **Technology Stack**

### **Backend:**
- **Python 3.9+** with FastAPI
- **Pydantic** for data validation
- **Uvicorn** ASGI server
- **Jinja2** templating

### **Frontend:**
- **TailwindCSS** for styling
- **Vanilla JavaScript** for interactivity
- **PostCSS** for CSS processing

### **Dependencies:**
- **NLP Libraries**: NLTK, spaCy, sentence-transformers
- **Document Processing**: Pandoc, BeautifulSoup4
- **ML Libraries**: scikit-learn, huggingface-hub
- **Web Framework**: FastAPI, aiofiles, python-multipart

## 🐳 **Deployment Options**

The repository includes multiple deployment configurations:
- `Dockerfile` - Production container
- `Dockerfile.dev` - Development container  
- `Dockerfile.simple` - Simplified container
- `docker-compose.yml` - Multi-container setup
- `docker-build.sh` - Build automation script

## 🎯 **Key Features**

1. **Dynamic Plugin Loading**: Runtime plugin discovery without restarts
2. **Type-Safe Validation**: Pydantic ensures all inputs/outputs are validated
3. **File-Based I/O**: Handle file uploads and generate downloadable outputs
4. **Analytics Dashboard**: Track usage, performance, and system metrics
5. **Compliance Checking**: Automatic validation of plugin architecture rules
6. **Chain Management**: Save, load, duplicate, and manage plugin workflows
7. **Template System**: Pre-built chain templates for common use cases

## 🚀 **Getting Started**

The application provides multiple interfaces:
- **Main Interface**: `http://localhost:8000`
- **Chain Builder**: `http://localhost:8000/chain-builder`
- **Plugin Development Guide**: `http://localhost:8000/how-to`
- **Chain Management**: `http://localhost:8000/chains`

This is a well-architected, production-ready system for building extensible web applications with dynamic plugin capabilities and visual workflow creation.