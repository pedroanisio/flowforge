# Neural Plugin System with Chain Builder

This project is a modern, web-based application that features a dynamic plugin system with visual chain building capabilities, built with FastAPI and Pydantic. Each plugin can define its own user interface and I/O specifications through a simple, yet powerful, manifest-driven architecture. The system automatically discovers and loads plugins at runtime, and allows users to create complex workflows by chaining plugins together visually.

## 🚀 Key Features

- **Dynamic Plugin Loading**: Plugins are discovered and loaded on-the-fly without needing to restart the application.
- **Visual Chain Builder**: Create complex workflows by connecting plugins in a visual interface.
- **Manifest-Driven UI**: Each plugin's UI and inputs are defined in a `manifest.json` file, allowing for flexible and self-describing components.
- **Type-Safe Inputs**: Pydantic ensures all user inputs are validated against the types defined in the plugin's manifest.
- **🔒 Type-Safe Responses**: All plugins must define Pydantic models for their responses, ensuring consistent and validated outputs.
- **Plugin Compliance Checking**: Automatic validation that plugins follow the response model rule with detailed compliance reports.
- **Chain Management**: Save, load, duplicate, and manage plugin chains with execution history and analytics.
- **Template System**: Pre-built chain templates for common workflows.
- **Dependency Checking**: The system automatically checks for required external dependencies (e.g., command-line tools) and reports their status in the UI.
- **File-Based I/O**: Plugins can easily handle file uploads and generate downloadable file outputs.
- **Analytics Dashboard**: Track plugin usage, chain execution statistics, and system performance.
- **🆕 Container Orchestration**: Docker-based service communication for specialized document processing plugins.
- **🆕 Service Discovery**: Automatic detection and communication with Docker containers for advanced processing.
- **🆕 Advanced Document Processing**: Multi-container PDF and document conversion workflows with optimized performance.
- **Modern Tech Stack**: Built with FastAPI, Pydantic, and a responsive web interface.

## 🔒 MANDATORY PLUGIN RESPONSE MODEL RULE

**ALL PLUGINS MUST DEFINE THE PYDANTIC MODEL OF ITS RESPONSE**

This rule ensures:

- ✅ Type safety and validation for all plugin responses
- ✅ Consistent API structure across all plugins  
- ✅ Self-documenting response formats
- ✅ Early detection of response structure issues
- ✅ Better developer experience and debugging
- ✅ Seamless chain compatibility and data flow validation

### Implementation Requirements

Every plugin must:

1. **Inherit from BasePlugin**

   ```python
   from ...models.plugin import BasePlugin, BasePluginResponse
   
   class Plugin(BasePlugin):
       # Your plugin implementation
   ```

2. **Define a Response Model**

   ```python
   class YourPluginResponse(BasePluginResponse):
       result: str = Field(..., description="Your result field")
       count: int = Field(..., description="Some count")
       data: Dict[str, Any] = Field(default={}, description="Additional data")
   ```

3. **Implement get_response_model() Method**

   ```python
   @classmethod
   def get_response_model(cls) -> Type[BasePluginResponse]:
       return YourPluginResponse
   ```

4. **Return Validated Data**

   ```python
   def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
       # Your plugin logic here
       return {
           "result": "processed successfully",
           "count": 42,
           "data": {"additional": "information"}
       }
   ```

### Response Model Benefits

- **Chain Compatibility**: Ensures outputs from one plugin can be safely used as inputs to another
- **Runtime Validation**: Catches data structure issues before they propagate through chains
- **API Documentation**: Auto-generates OpenAPI schemas for plugin responses
- **Type Safety**: Provides IDE support and reduces runtime errors
- **Debugging**: Clear error messages when response validation fails

## 📦 Available Plugins

The application includes **10 pre-built plugins** demonstrating various capabilities:

1. **Text Statistics** (`text_stat`): Analyzes text and provides comprehensive statistics including word count, character count, frequency analysis, and linguistic metrics. ✅ **Compliant**

2. **Pandoc Converter** (`pandoc_converter`): **Enhanced** - Converts documents between formats using Pandoc compiled from source with advanced options support, features validation, and comprehensive error diagnostics. ✅ **Compliant**

3. **🆕 PDF to HTML Converter** (`pdf2html`): **Container-based** - Converts PDF documents to HTML using pdf2htmlEX service in Docker container with Docker socket communication. ✅ **Compliant**

4. **JSON to XML Converter** (`json_to_xml`): Converts JSON data structures to XML format with customizable formatting options. ✅ **Compliant**

5. **XML to JSON Converter** (`xml_to_json`): Converts XML documents to JSON format with structure preservation. ✅ **Compliant**

6. **Document Viewer** (`doc_viewer`): Displays and analyzes document content with metadata extraction capabilities. ✅ **Compliant**

7. **Web Sentence Analyzer** (`web_sentence_analyzer`): Advanced sentence analysis with web-based natural language processing features. ✅ **Compliant**

8. **Bag of Words** (`bag_of_words`): Text processing using bag-of-words model for feature extraction. ✅ **Compliant**

9. **Context-Aware Stopwords** (`context_aware_stopwords`): Intelligent stopword removal based on context analysis. ✅ **Compliant**

10. **Sentence Merger** (`sentence_merger`): Advanced sentence combining with configurable merge strategies. ✅ **Compliant**

**Plugin Compliance Status**: Use the compliance checker to verify all plugins follow the response model rule:

```bash
# Check compliance via API
curl http://localhost:8000/api/plugin-compliance
```

## 🐳 Container Orchestration Architecture

### 🏗️ Container-Based Plugin System

The system now supports **advanced container orchestration** for specialized plugins that require dedicated processing environments:

```
┌─────────────────┐    ┌──────────────────────┐
│  Main Web App   │    │  pdf2htmlex-service  │
│  (Neural Plugin │◄──►│  (Conversion Service)│
│   System)       │    │                      │
│                 │    │                      │
│ + Docker CLI    │    │                      │
│ + Docker Socket │    │                      │
└─────────────────┘    └──────────────────────┘
         │                        │
         │                        │
         └────────────────────────┘
              Shared Volume
              (/app/shared)
```

### 🔧 Container Communication Features

- **Docker Socket Access**: Main application communicates with Docker daemon for service orchestration
- **Service Discovery**: Automatic detection of running container services
- **Container Execution**: Execute commands in specialized containers via `docker exec`
- **Shared Storage**: File exchange between containers through mounted volumes
- **Health Monitoring**: Container status monitoring and error handling

### 🛡️ Security Considerations

⚠️ **Important**: The Docker socket mounting provides elevated privileges for container communication:

```yaml
# docker compose.yml - Required for container orchestration
volumes:
  - /var/run/docker.sock:/var/run/docker.sock  # Docker API access
```

**Security measures implemented:**
- Controlled container communication only with designated service containers
- Input validation and sanitization for container commands
- Resource limits and timeout controls
- Isolated execution environments

**Production recommendations:**
- Monitor Docker socket access logs
- Use Docker-in-Docker alternatives if higher security is required
- Implement service mesh for advanced container communication
- Regular security audits of container interactions

## 🔗 Chain Builder

The Chain Builder allows you to create complex workflows by connecting multiple plugins in sequence. Features include:

- **Visual Interface**: Drag-and-drop plugin connection at `/chain-builder`
- **Data Flow Validation**: Ensures output types match input requirements
- **Conditional Logic**: Support for branching and conditional execution
- **Template Library**: Pre-built chains for common use cases
- **Execution History**: Track and analyze chain performance
- **Real-time Monitoring**: Live execution status and progress tracking
- **🆕 Container Support**: Seamlessly integrate container-based plugins in chains

### Creating Chains

1. **Via Web Interface**: Navigate to `/chain-builder` for the visual editor
2. **Via API**: Use the REST API to programmatically create chains
3. **From Templates**: Start with pre-built templates and customize

### Chain Templates

Access pre-built templates for common workflows:

- Document processing pipelines with container-based conversions
- Text analysis workflows with advanced NLP processing
- Data transformation chains with format conversions
- Multi-format document conversion sequences

## ⚙️ Getting Started

### Prerequisites

- Python 3.9+
- Node.js and npm
- Docker and Docker Compose (required for container-based plugins)
- Optional: Pandoc (built from source in Docker)

### Quick Start with Docker (Recommended)

1. Clone the repository:

   ```bash
   git clone https://github.com/pedroanisio/dwp.git
   cd dynamic-web-plugins
   ```

2. **Start all services with Docker Compose:**

   ```bash
   # Start production services (includes container orchestration)
   docker compose up -d
   ```

3. **Access the application:**
   - Main interface: <http://localhost:8000>
   - Chain Builder: <http://localhost:8000/chain-builder>
   - Plugin Development Guide: <http://localhost:8000/how-to>

4. **Verify container services:**
   ```bash
   # Check all services are running
   docker compose ps
   
   # Test container communication
   curl http://localhost:8000/api/plugins
   ```

### Manual Installation (Development)

1. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Install Node.js dependencies:

   ```bash
   npm install
   ```

3. Build CSS:

   ```bash
   npm run build-css
   ```

4. Start services:

   ```bash
   # Start container services first
   docker compose up -d pdf2htmlex-service
   
   # Start the web application
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### 🚀 Docker Build Options

The project includes **multiple Docker configurations** optimized for different use cases:

#### Production Build (Pandoc from Source)
```bash
# Multi-stage build with Pandoc compiled from source
docker compose up -d
```

- **Features**: Latest Pandoc with full data files, container orchestration
- **Build Time**: 10-20 minutes (cached builds ~2 minutes)
- **Port**: 8000

#### Development Build (System Pandoc)
```bash
# Fast build with system Pandoc
docker compose -f docker compose.yml --profile dev up -d
```

- **Features**: Quick development iteration, container orchestration
- **Build Time**: 2-3 minutes
- **Port**: 8002 (if available)

#### Simple Build (Basic Features)
```bash
# Lightweight build
docker compose --profile simple up -d
```

- **Features**: Basic functionality, faster startup
- **Build Time**: 1-2 minutes
- **Port**: 8001 (if available)

## 🔌 Developing a New Plugin

Creating a new plugin requires following the **mandatory response model rule**. You can create either **direct plugins** or **container-based plugins**.

### Standard Plugin Development

1. **Create Plugin Directory**

   ```bash
   mkdir app/plugins/your_plugin_name
   cd app/plugins/your_plugin_name
   ```

2. **Create manifest.json**

   ```json
   {
     "id": "your_plugin_name",
     "name": "Your Plugin Display Name",
     "version": "1.0.0",
     "description": "Description of what your plugin does",
     "author": "Your Name",
     "inputs": [
       {
         "name": "input_field",
         "label": "Input Label",
         "field_type": "text",
         "required": true,
         "placeholder": "Enter value..."
       }
     ],
     "output": {
       "name": "result",
       "description": "Plugin output description"
     },
     "dependencies": ["optional", "external", "tools"],
     "tags": ["category", "keywords"]
   }
   ```

3. **Create plugin.py with Response Model**

   ```python
   from typing import Dict, Any, Type
   from pydantic import Field
   from ...models.plugin import BasePlugin, BasePluginResponse

   class YourPluginResponse(BasePluginResponse):
       """Response model for your plugin"""
       result: str = Field(..., description="Processing result")
       metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")

   class Plugin(BasePlugin):
       """Your plugin implementation"""
       
       @classmethod
       def get_response_model(cls) -> Type[BasePluginResponse]:
           return YourPluginResponse
       
       def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
           # Your plugin logic here
           input_value = data.get('input_field', '')
           
           # Process the input
           processed_result = f"Processed: {input_value}"
           
           return {
               "result": processed_result,
               "metadata": {
                   "input_length": len(input_value),
                   "processing_time": "0.1s"
               }
           }
   ```

### 🆕 Container-Based Plugin Development

For plugins requiring specialized environments (like pdf2htmlEX), you can use container orchestration:

1. **Add Container Service to docker compose.yml**

   ```yaml
   your-service:
     image: your/specialized-tool:latest
     volumes:
       - conversion_shared:/shared
     command: ["/bin/sh", "-c", "while true; do sleep 30; done"]
     networks:
       - plugin-network
   ```

2. **Implement Container Communication**

   ```python
   import subprocess
   import shutil
   from pathlib import Path

   class Plugin(BasePlugin):
       def _check_your_service_dependency(self) -> Dict[str, Any]:
           """Custom dependency checker for container service"""
           try:
               result = subprocess.run(
                   ["docker", "ps", "--filter", "name=your-service", "--format", "{{.Names}}"],
                   capture_output=True, text=True, timeout=10
               )
               return {
                   "service_available": bool(result.stdout.strip()),
                   "container_name": result.stdout.strip()
               }
           except Exception as e:
               return {"service_available": False, "error": str(e)}
       
       def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
           # Check service availability
           service_info = self._check_your_service_dependency()
           if not service_info["service_available"]:
               raise RuntimeError("Container service not available")
           
           # Execute command in container
           container_name = service_info["container_name"]
           result = subprocess.run([
               "docker", "exec", container_name,
               "your-command", "--input", "/shared/input.file"
           ], capture_output=True, text=True)
           
           # Process results...
           return {"result": "processed", "container_info": service_info}
   ```

3. **Add Service Dependency to Manifest**

   ```json
   {
     "dependencies": {
       "external": [
         {
           "name": "your-service",
           "help": "Container service must be running via docker compose"
         }
       ]
     }
   }
   ```

### Container Plugin Examples

See `app/plugins/pdf2html/` for a complete container-based plugin implementation with:
- Docker service communication
- Shared volume file processing
- Service health monitoring
- Comprehensive error handling
- Architecture documentation

## 📁 Project Structure

```
├── requirements.txt                    # Python dependencies
├── package.json                       # Node.js dependencies and scripts
├── docker compose.yml                 # 🆕 Multi-container orchestration with services
├── Dockerfile                         # 🆕 Multi-stage build with Pandoc from source
├── Dockerfile.dev                     # Development container
├── Dockerfile.simple                  # Simple container for basic features
├── tailwind.config.js                 # Tailwind CSS configuration
├── postcss.config.js                  # PostCSS configuration
└── app/
    ├── main.py                         # FastAPI application entry point
    ├── models/
    │   ├── __init__.py
    │   ├── plugin.py                  # Plugin models + BasePlugin + BasePluginResponse
    │   ├── response.py                # API response models
    │   └── chain.py                   # Chain definition models
    ├── core/
    │   ├── __init__.py
    │   ├── plugin_loader.py           # Plugin discovery and loading
    │   ├── plugin_manager.py          # 🆕 Enhanced plugin execution + container orchestration
    │   ├── chain_manager.py           # Chain execution and management
    │   ├── chain_executor.py          # Chain execution engine
    │   └── chain_storage.py           # Chain persistence layer
    ├── plugins/
    │   ├── __init__.py
    │   ├── text_stat/                 # Text statistics plugin
    │   ├── pandoc_converter/          # 🆕 Enhanced document converter with advanced options
    │   ├── pdf2html/                  # 🆕 Container-based PDF to HTML converter
    │   │   ├── plugin.py              # Docker service communication
    │   │   ├── manifest.json          # Service dependencies
    │   │   └── README.md              # Architecture documentation
    │   ├── json_to_xml/               # JSON to XML converter
    │   ├── xml_to_json/               # XML to JSON converter
    │   ├── doc_viewer/                # Document viewer plugin
    │   ├── web_sentence_analyzer/     # Sentence analysis plugin
    │   ├── bag_of_words/              # Bag of words text processing
    │   ├── context_aware_stopwords/   # Context-aware stopword removal
    │   └── sentence_merger/           # Sentence merging with strategies
    ├── static/
    │   ├── css/
    │   │   ├── dist/                  # Compiled CSS
    │   │   └── src/                   # Source CSS files
    │   ├── js/
    │   │   └── chain-builder.js       # Enhanced chain builder with container support
    │   └── favicon.ico
    ├── templates/
    │   ├── base.html                  # Base template
    │   ├── index.html                 # Homepage
    │   ├── plugin.html                # Plugin execution page
    │   ├── result.html                # Results display
    │   ├── chain_builder.html         # Chain builder interface
    │   ├── chains.html                # Chain management
    │   └── how-to.html                # Development guide
    ├── data/                          # Data storage directory
    │   ├── chains/                    # Saved chains
    │   ├── downloads/                 # Generated files
    │   └── templates/                 # Chain templates
    └── shared/                        # 🆕 Container shared volume for file processing
```

## 🌐 API Endpoints

### Core Plugin Endpoints

- `GET /` - Web interface homepage
- `GET /plugin/{plugin_id}` - Plugin interaction page
- `GET /how-to` - Plugin development guide
- `POST /plugin/{plugin_id}/execute` - Execute plugin (web form)

### Plugin API Endpoints

- `GET /api/plugins` - List all available plugins
- `GET /api/plugin/{plugin_id}` - Get plugin information
- `GET /api/plugin/{plugin_id}/schema` - Get plugin input/output schema
- `POST /api/plugin/{plugin_id}/execute` - Execute plugin (JSON API)
- `POST /api/refresh-plugins` - Refresh plugin list
- `GET /api/plugin-compliance` - **Enhanced** - Check plugin compliance status with container service health

### Chain Management Endpoints

- `GET /chain-builder` - Visual chain builder interface
- `GET /chains` - Chain management interface
- `GET /api/chains` - List all chains
- `POST /api/chains` - Create new chain
- `GET /api/chains/search` - Search chains
- `GET /api/chains/{chain_id}` - Get specific chain
- `PUT /api/chains/{chain_id}` - Update chain
- `DELETE /api/chains/{chain_id}` - Delete chain
- `POST /api/chains/{chain_id}/duplicate` - Duplicate chain
- `POST /api/chains/validate` - Validate chain definition
- `POST /api/chains/{chain_id}/execute` - Execute chain **with container support**
- `GET /api/chains/{chain_id}/history` - Get execution history
- `GET /api/chains/{chain_id}/analytics` - Get chain analytics
- `GET /api/chains/{chain_id}/connections/{source_node_id}` - Get compatible connections

### Template Management Endpoints

- `GET /api/templates` - List available templates
- `GET /api/templates/{template_id}` - Get specific template
- `POST /api/templates/{template_id}/create-chain` - Create chain from template

### System Endpoints

- `GET /api/system/analytics` - System-wide analytics

### Example API Usage

```bash
# List all plugins (includes container-based plugins)
curl http://localhost:8000/api/plugins

# Check plugin compliance (includes container health)
curl http://localhost:8000/api/plugin-compliance

# Execute text statistics plugin
curl -X POST http://localhost:8000/api/plugin/text_stat/execute \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world! This is a test."}'

# 🆕 Execute container-based PDF to HTML conversion
curl -X POST http://localhost:8000/api/plugin/pdf2html/execute \
  -F "input_file=@document.pdf" \
  -F "zoom=1.5" \
  -F "embed_css=true"

# List all chains
curl http://localhost:8000/api/chains

# Create a new chain
curl -X POST http://localhost:8000/api/chains \
  -H "Content-Type: application/json" \
  -d '{"name": "My Workflow", "description": "Custom processing workflow"}'

# Execute a chain (supports container-based plugins)
curl -X POST http://localhost:8000/api/chains/chain_id/execute \
  -H "Content-Type: application/json" \
  -d '{"input_data": "your data here"}'
```

## 🏗️ Architecture

### Plugin System Architecture

- **Discovery**: Scans plugin directories for manifests automatically
- **Loading**: Dynamically imports plugin modules at runtime
- **Compliance Checking**: Validates plugins follow response model requirements
- **Validation**: Validates inputs against plugin schemas using Pydantic
- **Response Validation**: Ensures plugin outputs match declared response models
- **Execution**: Runs plugin logic with error handling and result capture
- **🆕 Container Orchestration**: Docker service-based plugin execution with inter-container communication

### Chain Builder Architecture

- **Visual Editor**: Web-based drag-and-drop interface for chain creation
- **Execution Engine**: Processes chains with data flow validation
- **Storage Layer**: Persists chains and execution history
- **Analytics Engine**: Tracks performance metrics and usage statistics
- **Template System**: Manages reusable chain templates
- **🆕 Container Integration**: Seamless integration of container-based plugins in chains

### Validation System

- **Manifest Validation**: Pydantic models ensure valid plugin definitions
- **Input Validation**: Runtime validation of user inputs against schemas
- **Plugin Compliance**: Ensures plugins inherit from BasePlugin and define response models
- **Output Validation**: Validates plugin outputs against declared Pydantic response models
- **Chain Validation**: Ensures data compatibility between connected plugins
- **🆕 Container Health Validation**: Monitors Docker service availability and health

### UI Generation

- **Dynamic Forms**: HTML forms generated from plugin manifests
- **Type-Aware Rendering**: Different input types render with appropriate controls
- **Responsive Design**: Modern, mobile-friendly interface
- **Real-time Updates**: Live feedback during plugin and chain execution
- **🆕 Container Status Display**: Visual indicators for container service health

## 🔍 Plugin Compliance Checking

### API Compliance Check

Get detailed compliance reports for all plugins including container services:

```bash
curl http://localhost:8000/api/plugin-compliance
```

Response includes:

- Total plugin count and compliance percentage
- List of compliant plugins with response models
- List of non-compliant plugins with specific issues
- **🆕 Container service health status**
- **🆕 Docker service dependency information**
- Migration instructions and example code

### Compliance Requirements

All plugins must:

1. **Inherit from BasePlugin**
2. **Define a response model inheriting from BasePluginResponse**
3. **Implement get_response_model() class method**
4. **Return data that validates against the response model**
5. **Handle errors gracefully with appropriate response structure**
6. **🆕 For container-based plugins**: Implement custom dependency checking for service health

### Migration Guide for Existing Plugins

If you have non-compliant plugins, follow these steps:

1. **Add Response Model**

   ```python
   class YourPluginResponse(BasePluginResponse):
       # Define your response fields here
       pass
   ```

2. **Update Plugin Class**

   ```python
   class Plugin(BasePlugin):  # Ensure BasePlugin inheritance
       @classmethod
       def get_response_model(cls) -> Type[BasePluginResponse]:
           return YourPluginResponse
   ```

3. **Validate Execute Method**

   ```python
   def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
       # Ensure return data matches your response model
       return {"field1": "value1", "field2": "value2"}
   ```

4. **🆕 Add Container Support (Optional)**

   ```python
   def _check_your_service_dependency(self) -> Dict[str, Any]:
       """Custom dependency checker for container services"""
       # Implement container health checking
       pass
   ```

## 📊 Analytics and Monitoring

### Chain Analytics

Track chain performance with detailed metrics:

- Execution frequency and success rates
- Average execution time per chain
- Error patterns and failure analysis
- Resource usage statistics
- **🆕 Container execution performance metrics**
- **🆕 Service communication latency tracking**

### System Analytics

Monitor overall system health:

- Plugin usage statistics
- Popular chain templates
- System performance metrics
- User activity patterns
- **🆕 Container service uptime and health**
- **🆕 Docker resource utilization**

### Access Analytics

- **Chain-specific**: `GET /api/chains/{chain_id}/analytics`
- **System-wide**: `GET /api/system/analytics`
- **Execution History**: `GET /api/chains/{chain_id}/history`

## 🎨 Customization

### Adding New Field Types

1. Update `InputFieldType` enum in `models/plugin.py`
2. Add rendering logic in `templates/plugin.html`
3. Add validation logic in `core/plugin_manager.py`
4. Update chain builder to handle new field types

### Custom Result Display

- Modify `templates/result.html` for specialized result rendering
- Add plugin-specific display logic using template conditionals
- Create custom CSS classes for enhanced visualization

### Chain Builder Customization

- Extend `static/js/chain-builder.js` for custom node types
- Add custom connection validation logic
- Implement specialized chain execution patterns
- **🆕 Add container-specific UI components**

### Styling and Theming

- Customize `static/css/src/main.css` for visual modifications
- Modify Tailwind configuration in `tailwind.config.js`
- Add custom components and layouts

## 🧪 Testing

### Test Plugin Compliance

```bash
# Check if all plugins are compliant (includes container health)
curl http://localhost:8000/api/plugin-compliance
```

### Test Individual Plugins

```bash
# Test the Text Statistics Plugin
curl -X POST http://localhost:8000/api/plugin/text_stat/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The quick brown fox jumps over the lazy dog. This sentence contains every letter of the alphabet!"
  }'

# Test the Enhanced Pandoc Converter with advanced options
curl -X POST http://localhost:8000/api/plugin/pandoc_converter/execute \
  -F "input_file=@document.md" \
  -F "output_format=html" \
  -F "advanced_options=--standalone --toc"

# 🆕 Test container-based PDF to HTML conversion
curl -X POST http://localhost:8000/api/plugin/pdf2html/execute \
  -F "input_file=@document.pdf" \
  -F "zoom=1.3" \
  -F "embed_css=true" \
  -F "embed_javascript=true"
```

### Test Chain Execution

```bash
# Validate a chain definition
curl -X POST http://localhost:8000/api/chains/validate \
  -H "Content-Type: application/json" \
  -d '{"chain_definition": "your_chain_json_here"}'

# Execute a chain (supports container-based plugins)
curl -X POST http://localhost:8000/api/chains/your_chain_id/execute \
  -H "Content-Type: application/json" \
  -d '{"input_data": "test input"}'
```

### 🆕 Test Container Services

```bash
# Check container service health
docker compose ps

# Test container communication
docker exec web docker ps --filter "name=pdf2htmlex-service"

# Monitor container logs
docker compose logs -f pdf2htmlex-service
```

## 🐳 Docker Deployment with Advanced Container Orchestration

The project includes **advanced Docker configuration** with **multi-stage builds**, **container orchestration**, and **service communication**. This setup includes several Docker-specific optimizations and container-based plugin architecture.

### 🔧 Docker Architecture & Container Orchestration

The Docker setup uses **multi-container orchestration** with several key components:

1. **Main Web Application**: FastAPI app with Docker socket access
2. **pdf2htmlex-service**: Specialized PDF conversion container
3. **Shared Volumes**: File exchange between containers
4. **Service Network**: Container communication network

#### Key Docker Features & Optimizations:

- **Multi-stage build**: Builds Pandoc from source for optimal performance (~800MB savings)
- **Container Orchestration**: Multiple specialized service containers
- **Docker Socket Communication**: Inter-container command execution
- **Service Discovery**: Automatic container detection and health monitoring
- **Shared Volumes**: Efficient file processing between containers
- **BuildKit caching**: Leverages Docker layer caching for faster rebuilds
- **Health checks**: Ensures both application and container services are functional

### 🐳 Container Communication & Docker Socket

The application includes **Docker socket mounting** for advanced container orchestration:

#### Docker Socket Features:

- **Service Discovery**: Automatically detects and communicates with other Docker services
- **Container Orchestration**: Execute commands in sibling containers via `docker exec`
- **Dynamic Service Management**: Monitor and interact with companion services
- **PDF Conversion Service**: Communicates with `pdf2htmlex-service` container for document processing

#### Container Architecture:

```yaml
# docker compose.yml - Container orchestration
services:
  web:
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock  # Docker API access
      - conversion_shared:/app/shared               # Shared processing volume
  
  pdf2htmlex-service:
    image: pdf2htmlex/pdf2htmlex:0.18.8.rc2-master-20200820-ubuntu-20.04-x86_64
    volumes:
      - conversion_shared:/shared                   # Shared processing volume
```

#### Container Communication Examples:

- **PDF Processing**: Web app executes `docker exec pdf2htmlex-service pdf2htmlEX [options]`
- **Service Health Checks**: Monitors container status via Docker API  
- **Dynamic Container Discovery**: Finds containers by service name patterns
- **File Processing**: Shared volume file exchange for processing workflows

#### Security Configuration:

⚠️ **Important**: Docker socket access provides elevated privileges. Production considerations:

- **Controlled Access**: Commands executed only in designated service containers
- **Input Validation**: All container commands are validated and sanitized
- **Resource Limits**: Container-based resource management and timeouts
- **Monitoring**: Container access logging and health monitoring
- **Network Isolation**: Services communicate through dedicated Docker networks

#### Supported Plugin Architectures:

1. **Direct Plugins**: Traditional in-process plugin execution
2. **Container-based Plugins**: Plugins that delegate work to specialized containers
3. **Service Communication**: Inter-container communication for complex workflows
4. **Hybrid Chains**: Chains mixing direct and container-based plugins

### 🚀 Quick Start

Start the application with Docker Compose:

```bash
# Build and run production version (Pandoc from source + container orchestration)
docker compose up -d --build

# View logs for all services
docker compose logs -f
```

### 📦 Build Options

#### Production Build (Recommended for deployment)
```bash
# Build production image with custom Pandoc from source + container services
docker compose up -d --build
```

- **Pandoc Version**: 3.7.0.2 (latest stable, built from source with full data files)
- **Container Services**: pdf2htmlex-service, shared volumes, service discovery
- **Build Time**: 10-20 minutes (first build), ~2 minutes (cached)
- **Image Size**: ~500MB (optimized multi-stage build)
- **Port**: 8000

#### Development Build (Fast for development)
```bash
# Build development image with system Pandoc + container services
docker compose -f docker compose.yml --profile dev up -d --build
```

- **Pandoc Version**: System package (usually 2.x)
- **Container Services**: Full container orchestration
- **Build Time**: 2-3 minutes
- **Image Size**: ~300MB
- **Port**: 8002 (if available)

#### Simple Build (Basic features, no containers)
```bash
# Build simple image without container orchestration
docker compose --profile simple up -d --build
```

- **Features**: Basic plugins only (no container-based plugins)
- **Build Time**: 1-2 minutes
- **Image Size**: ~250MB
- **Port**: 8001 (if available)

### 🛠️ Advanced Docker Usage

```bash
# Start specific services
docker compose up -d pdf2htmlex-service  # PDF service only
docker compose up -d web                 # Production web app

# Monitor all services
docker compose ps
docker compose logs -f

# Container service testing
docker exec web docker ps --filter "name=pdf2htmlex-service"
docker exec pdf2htmlex-service pdf2htmlEX --help

# Clean up Docker resources
docker compose down
docker system prune
```

### 🔍 Container Service Configuration

- **`docker compose.yml`**: Multi-container orchestration with service dependencies
- **`Dockerfile`**: Production multi-stage build with Pandoc from source
- **`Dockerfile.dev`**: Development build with system packages
- **`Dockerfile.simple`**: Simplified build without container services
- **`.dockerignore`**: Optimized build context

### 🎯 Why Container Orchestration?

Building with container orchestration provides several advantages:

1. **Specialized Environments**: Isolated environments for complex tools (pdf2htmlEX, etc.)
2. **Scalability**: Individual service scaling and resource management
3. **Maintainability**: Separate concerns and easier updates
4. **Security**: Process isolation and controlled access
5. **Performance**: Optimized containers for specific tasks
6. **Flexibility**: Easy addition of new container-based services

### 📊 Performance Comparison

| Build Type | Features | Build Time | Image Size | Container Services | Plugin Count |
|------------|----------|------------|------------|-------------------|-------------|
| Production | Pandoc from source, full containers | 15 min | 500MB | 2 services | 10 plugins |
| Development | System Pandoc, full containers | 3 min | 300MB | 2 services | 10 plugins |
| Simple | Basic features, no containers | 2 min | 250MB | 1 service | 9 plugins |

### 🔧 Troubleshooting Container Issues

**Container Service Not Starting:**
```bash
# Check service status
docker compose ps

# Check service logs
docker compose logs pdf2htmlex-service

# Restart services
docker compose restart pdf2htmlex-service
```

**Docker Socket Permission Issues:**
```bash
# Check Docker socket permissions
ls -la /var/run/docker.sock

# Fix permissions (Linux)
sudo chmod 666 /var/run/docker.sock

# Or add user to docker group
sudo usermod -aG docker $USER
```

**Container Communication Failures:**
```bash
# Test container discovery
docker exec web docker ps --filter "name=pdf2htmlex-service"

# Test shared volumes
ls -la /app/shared/
docker exec pdf2htmlex-service ls -la /shared/

# Check network connectivity
docker network ls
docker network inspect dynamic-web-plugins_plugin-network
```

**Memory Issues During Build:**
```bash
# Increase Docker memory limit to 4GB+ in Docker Desktop
# Or use development build which requires less memory
   docker compose -f docker compose.yml --profile dev up -d --build
```

**Container Health Check Failures:**
```bash
# Check application health
curl http://localhost:8000/api/plugins

# Check container service health
curl http://localhost:8000/api/plugin-compliance

# Manual container testing
docker exec pdf2htmlex-service pdf2htmlEX --help
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. **Ensure any new plugins follow the response model rule**
4. **Run compliance checker**: `curl http://localhost:8000/api/plugin-compliance`
5. **Test container services**: `docker compose ps` and verify all services are healthy
6. Test thoroughly (plugins, chains, container communication, and UI)
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Submit a pull request

### Contribution Guidelines

- All plugins must be compliant with response model requirements
- **Container-based plugins** must include comprehensive documentation
- Include comprehensive tests for new features (including container integration tests)
- Update documentation for any API changes
- Follow existing code style and patterns
- Add chain templates for common use cases
- **Document container dependencies** and service requirements

## 📄 License

This project is provided as a demonstration of FastAPI + Pydantic plugin architecture patterns with advanced chain building capabilities and container orchestration.

## 🔍 Troubleshooting

### Plugin Issues

**Plugin Not Loading:**

- Check `manifest.json` syntax and required fields
- Ensure plugin inherits from `BasePlugin`
- Verify plugin implements `get_response_model()` method
- Ensure `plugin.py` has a `Plugin` class with `execute` method
- Check plugin directory structure matches requirements
- **🆕 For container plugins**: Verify container service dependencies in manifest

**Plugin Compliance Issues:**

- Run compliance check: `curl http://localhost:8000/api/plugin-compliance`
- Ensure response model inherits from `BasePluginResponse`
- Verify `execute()` returns data matching the response model schema
- Check that all required fields are properly defined
- **🆕 Container plugins**: Implement custom dependency checking methods

**Validation Errors:**

- Check input field types match manifest definitions
- Ensure required fields are provided in requests
- Validate JSON schema syntax in manifests
- Verify plugin response validation against defined models

### Chain Builder Issues

**Chain Not Executing:**

- Validate chain definition using `/api/chains/validate`
- Check data type compatibility between connected plugins
- Verify all required inputs are provided
- Check execution history for error details
- **🆕 Container chains**: Ensure all container services are running

**Connection Issues:**

- Use `/api/chains/{chain_id}/connections/{source_node_id}` to check compatibility
- Ensure output types match input requirements
- Verify plugin response models are properly defined

**Performance Issues:**

- Monitor execution times in chain analytics
- Check system analytics for resource usage
- Optimize plugin logic for large inputs
- Consider caching for frequently used chains
- **🆕 Container performance**: Monitor container resource usage and scaling

### 🆕 Container Service Issues

**Service Not Available:**

- Check container status: `docker compose ps`
- Restart services: `docker compose restart [service-name]`
- Check service logs: `docker compose logs -f [service-name]`
- Verify Docker socket access: `docker exec web docker ps`

**Container Communication Failures:**

- Test service discovery: `docker exec web docker ps --filter "name=service-name"`
- Check shared volumes: `ls -la /app/shared/`
- Verify network connectivity: `docker network inspect plugin-network`
- Monitor container logs during execution

**Resource Issues:**

- Check Docker resource limits: `docker stats`
- Monitor disk space: `df -h`
- Clean up unused containers: `docker system prune`
- Scale services if needed: `docker compose up --scale service-name=2`

### System Issues

**Response Model Validation Failures:**

- Verify plugin response data matches the defined Pydantic model
- Check field types and required fields in response model
- Use compliance checker to identify specific validation issues
- Ensure all plugins return valid response structures

**Database/Storage Issues:**

- Check file permissions in `app/data/` directories 
- Verify chain storage integrity
- Clear temporary files if disk space is low
- Check execution history logs for patterns
- **🆕 Shared volumes**: Ensure proper permissions on `/app/shared/`

**Dependencies:**

- Ensure all external tools are accessible
- Check Python package versions match requirements.txt
- Verify Node.js dependencies are properly installed
- Test external tool availability in plugin manifests
- **🆕 Container dependencies**: Verify all container services are running and healthy

For additional support, check the execution logs, container logs, and use the built-in analytics to identify patterns in errors or performance issues. The container orchestration adds complexity but provides powerful capabilities for specialized processing workflows.
