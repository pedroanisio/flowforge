import subprocess
import shutil
import logging
import re
from pathlib import Path
from typing import Dict, Any, Type, List, Union, Literal
from pydantic import BaseModel, Field
from ...models.plugin import BasePlugin

# Import all components from refactored modules
from .models import (
    ProcessingConfig, InputFileInfo, ProcessingContext, 
    PandocConverterResponse
)
from .services import (
    MemoryMonitor, FileHandler, PandocExecutor, 
    TextExtractor, ChunkingService
)
from .strategies import (
    SingleFileStrategy, ChunkedStrategy, TextExtractionStrategy
)

# Set up logging
logger = logging.getLogger(__name__)


class PandocConverterInput(BaseModel):
    input_file: Dict[str, Any] = Field(
        ...,
        json_schema_extra={
            "label": "Upload File",
            "field_type": "file",
            "validation": {"allowed_extensions": ["epub", "html", "md", "docx", "odt", "rtf", "latex"]},
        },
    )
    output_format: Literal[
        "plain",
        "asciidoc",
        "pdf",
        "html5",
        "docbook5",
        "epub",
        "markdown",
        "markdown_mmd",
        "markdown_strict",
        "json",
    ] = Field(
        ...,
        json_schema_extra={
            "label": "Output Format",
            "field_type": "select",
            "options": [
                "plain",
                "asciidoc",
                "pdf",
                "html5",
                "docbook5",
                "epub",
                "markdown",
                "markdown_mmd",
                "markdown_strict",
                "json",
            ],
        },
    )
    self_contained: bool = Field(
        default=False,
        json_schema_extra={
            "label": "Self-Contained",
            "field_type": "checkbox",
            "help": "For HTML output, this embeds all assets like images and CSS into a single portable file.",
        },
    )
    advanced_options: Union[str, List[str], None] = Field(
        default=None,
        json_schema_extra={
            "label": "Advanced Options",
            "field_type": "textarea",
            "placeholder": "--verbose --columns=72 --toc --reference-links",
            "help": "Additional pandoc command-line options. Enter space-separated options like '--verbose --columns=72 --toc=true --toc-depth=3'. Use quotes for values with spaces. Security validated to prevent injection attacks.",
        },
    )
    features: Union[str, List[str], None] = Field(
        default=None,
        json_schema_extra={
            "label": "Format Features",
            "field_type": "textarea",
            "placeholder": "smart, -raw_html, +pipe_tables",
            "help": "Enable or disable pandoc format features. Use '+feature' to enable or '-feature' to disable. Multiple features can be separated by commas or spaces. If no +/- prefix is given, '+' (enable) is assumed.",
        },
    )


class Plugin(BasePlugin):
    """Pandoc File Converter Plugin - Converts files between markup formats using Pandoc"""
    
    def __init__(self):
        # Initialize service components
        self.memory_monitor = MemoryMonitor()
        self.file_handler = FileHandler()
        self.pandoc_executor = PandocExecutor(self.memory_monitor)
        self.text_extractor = TextExtractor()
        self.chunking_service = ChunkingService()
        
        # Initialize processing strategies
        self.single_file_strategy = SingleFileStrategy(self.pandoc_executor, self.memory_monitor)
        self.chunked_strategy = ChunkedStrategy(
            self.pandoc_executor, self.memory_monitor, self.chunking_service, self.text_extractor
        )
        self.text_extraction_strategy = TextExtractionStrategy(self.text_extractor, self.memory_monitor)

    @classmethod
    def get_input_model(cls) -> Type[BaseModel]:
        """Return the canonical input model for this plugin."""
        return PandocConverterInput
    
    @classmethod
    def get_response_model(cls) -> Type[PandocConverterResponse]:
        """Return the Pydantic model for this plugin's response"""
        return PandocConverterResponse
    
    def _parse_input_data(self, data: Dict[str, Any]) -> tuple:
        """Parse and validate input data"""
        input_file_info = data.get("input_file")
        output_format = data.get("output_format")
        self_contained = data.get("self_contained", False)
        advanced_options = data.get("advanced_options")
        features = data.get("features")

        if not input_file_info or not output_format:
            raise ValueError("Missing input file or output format")
            
        return input_file_info, output_format, self_contained, advanced_options, features
    
    def _setup_input_file(self, input_file_info: Dict[str, Any], temp_dir: Path) -> InputFileInfo:
        """Setup input file and return file info"""
        input_filename = input_file_info["filename"]
        
        if "temp_path" in input_file_info:
            # New streaming format - file already on disk
            temp_input_path = Path(input_file_info["temp_path"])
            file_size = input_file_info["size"]
            
            # Move to our temp directory for processing
            input_path = temp_dir / input_filename
            shutil.move(str(temp_input_path), str(input_path))
            logger.info(f"Moved streamed file to processing directory: {input_path}")
        else:
            # Legacy format - content in memory
            input_file_content = input_file_info["content"]
            file_size = len(input_file_content)
            
            # Write input file to temp directory
            input_path = temp_dir / input_filename
            with open(input_path, "wb") as f:
                f.write(input_file_content)
            logger.info(f"Wrote legacy content to processing directory: {input_path}")
        
        # Validate input file
        file_info = self.file_handler.validate_input(input_filename, file_size)
        file_info.path = input_path  # Set the actual path
        
        return file_info
    
    def _create_processing_config(self, advanced_options: List[str], features: List[str]) -> ProcessingConfig:
        """Create processing configuration from input parameters"""
        # Validate advanced options and features
        validated_advanced_options = self._validate_advanced_options(advanced_options)
        validated_features = self._validate_and_process_features(features)
        
        return ProcessingConfig(
            advanced_options=validated_advanced_options,
            features=validated_features
        )
    
    def _select_strategy(self, file_info: InputFileInfo, config: ProcessingConfig):
        """Select appropriate processing strategy based on file characteristics"""
        file_size = file_info.size
        file_ext = file_info.extension
        
        # For very large HTML files, use direct text extraction
        if file_size > config.text_extraction_threshold and file_ext.lower() == '.html':
            logger.info(f"Large HTML file detected ({file_info.size_mb}MB), using text extraction strategy")
            return self.text_extraction_strategy
        
        # For medium-large HTML files, use chunking
        elif self.chunking_service.should_chunk(file_size, file_ext, config.chunking_threshold):
            logger.info(f"Medium-large file detected ({file_info.size_mb}MB), using chunked strategy")
            return self.chunked_strategy
        
        # For normal files, use single file processing
        else:
            logger.info(f"Standard file size ({file_info.size_mb}MB), using single file strategy")
            return self.single_file_strategy
    
    def _create_processing_context(self, file_info: InputFileInfo, config: ProcessingConfig, 
                                 temp_dir: Path, output_format: str, complete_output_format: str,
                                 self_contained: bool) -> ProcessingContext:
        """Create processing context"""
        return ProcessingContext(
            input_info=file_info,
            config=config,
            temp_dir=temp_dir,
            output_format=output_format,
            complete_output_format=complete_output_format,
            self_contained=self_contained
        )
    
    def _format_response(self, result, permanent_file_path: Path,
                        pandoc_version: str, context: ProcessingContext) -> Dict[str, Any]:
        """Format the final response"""
        # Get output size from permanent file location (since temp file was moved)
        output_size = permanent_file_path.stat().st_size if permanent_file_path and permanent_file_path.exists() else 0
        
        conversion_details = {
            "pandoc_version": pandoc_version,
            "input_file": {
                "filename": context.input_info.filename,
                "file_size": context.input_info.size,
                "file_extension": context.input_info.extension,
                "size_mb": context.input_info.size_mb
            },
            "output_format": context.output_format,
            "complete_output_format": context.complete_output_format,
            "output_file": {
                "filename": permanent_file_path.name if permanent_file_path else "",
                "size_bytes": output_size,
                "size_mb": round(output_size / (1024 * 1024), 2)
            },
            "advanced_options_used": context.config.advanced_options,
            "features_used": context.config.features,
            "conversion_successful": result.success,
            "permanent_location": str(permanent_file_path),
            "processing_method": result.method.value,
            "chunk_count": result.chunk_count,
            "success_rate": result.success_rate,
            "memory_monitoring": result.memory_monitoring
        }
        
        return {
            "file_path": str(permanent_file_path),
            "file_name": permanent_file_path.name if permanent_file_path else "",
            "conversion_details": conversion_details
        }
    
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Main execute method - clean and focused"""
        temp_dir = None
        
        try:
            # 1. Parse and validate input
            input_file_info, output_format, self_contained, advanced_options, features = self._parse_input_data(data)
            
            # 2. Setup temporary directory and input file
            temp_dir = self.file_handler.setup_temp_directory()
            file_info = self._setup_input_file(input_file_info, temp_dir)
            
            # 3. Create processing configuration
            config = self._create_processing_config(advanced_options, features)
            
            # 4. Build complete output format
            complete_output_format = self._build_output_format_with_features(output_format, config.features)
            
            # 5. Create processing context
            context = self._create_processing_context(
                file_info, config, temp_dir, output_format, complete_output_format, self_contained
            )
            
            # 6. Select and execute processing strategy
            strategy = self._select_strategy(file_info, config)
            result = strategy.process(context)
            
            # 7. Handle processing result
            if not result.success:
                raise RuntimeError(result.error or "Processing failed")
            
            # 8. Verify output file exists before moving
            if not result.output_path or not result.output_path.exists():
                raise RuntimeError(f"Output file was not created or does not exist: {result.output_path}")
            
            logger.info(f"Successfully created output file: {result.output_path} ({result.output_path.stat().st_size} bytes)")
            
            # 9. Move output to permanent location
            permanent_file_path = self.file_handler.move_to_downloads(result.output_path, result.output_path.name)
            
            # 10. Verify permanent file exists
            if not permanent_file_path.exists():
                raise RuntimeError(f"Failed to move file to permanent location: {permanent_file_path}")
            
            logger.info(f"File successfully moved to permanent location: {permanent_file_path}")
            
            # 11. Get pandoc version for diagnostics
            pandoc_version = self.pandoc_executor.get_version()
            
            # 12. Format and return response
            return self._format_response(result, permanent_file_path, pandoc_version, context)
            
        except subprocess.TimeoutExpired:
            error_msg = "Processing timed out. The file may be too large or complex."
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
        except Exception as e:
            logger.error(f"Unexpected error in conversion: {e}")
            if temp_dir and temp_dir.exists():
                logger.error(f"Temp directory contents: {list(temp_dir.iterdir()) if temp_dir.exists() else 'Directory does not exist'}")
            raise RuntimeError(f"An unexpected error occurred during conversion: {e}")
            
        finally:
            # Clean up temporary directory
            if temp_dir:
                self.file_handler.cleanup(temp_dir)
    
    def _validate_advanced_options(self, advanced_options: Union[str, List[str], None]) -> List[str]:
        """Validate and parse advanced pandoc options"""
        if not advanced_options:
            return []
        
        # Convert to list if string
        if isinstance(advanced_options, str):
            # Split by spaces, but preserve quoted arguments
            import shlex
            try:
                options_list = shlex.split(advanced_options)
            except ValueError as e:
                raise ValueError(f"Invalid advanced_options format: {e}")
        else:
            options_list = advanced_options.copy()
        
        # Security validation: check for dangerous patterns
        dangerous_patterns = [
            r'[;&|`$]',  # Shell metacharacters
            r'\.\./',     # Directory traversal
            r'--?[io]$',  # Input/output flags that could override our files
            r'--input',
            r'--output',
        ]
        
        validated_options = []
        for option in options_list:
            if not isinstance(option, str):
                raise ValueError(f"All advanced options must be strings, got: {type(option)}")
            
            # Check for dangerous patterns
            for pattern in dangerous_patterns:
                if re.search(pattern, option):
                    raise ValueError(f"Advanced option contains potentially dangerous content: '{option}'")
            
            # Don't allow overriding critical options
            if option.startswith(('-o', '--output')):
                raise ValueError(f"Cannot override output option: '{option}'")
            
            validated_options.append(option.strip())
        
        return validated_options
    
    def _validate_and_process_features(self, features: Union[str, List[str], None]) -> List[str]:
        """Validate and process pandoc features (e.g., +smart, -raw_html)"""
        if not features:
            return []
        
        # Convert to list if string
        if isinstance(features, str):
            # Split by commas or spaces
            features_list = [f.strip() for f in re.split(r'[,\s]+', features) if f.strip()]
        else:
            features_list = features.copy()
        
        validated_features = []
        for feature in features_list:
            if not isinstance(feature, str):
                raise ValueError(f"All features must be strings, got: {type(feature)}")
            
            feature = feature.strip()
            if not feature:
                continue
            
            # Validate feature format
            if not re.match(r'^[+-]?[a-zA-Z_][a-zA-Z0-9_]*$', feature):
                raise ValueError(f"Invalid feature format: '{feature}'. Features should be alphanumeric with optional +/- prefix")
            
            # Ensure feature has +/- prefix
            if not feature.startswith(('+', '-')):
                # Default to enabling the feature
                feature = '+' + feature
            
            validated_features.append(feature)
        
        return validated_features
    
    def _build_output_format_with_features(self, base_format: str, features: List[str]) -> str:
        """Build the complete output format string with features"""
        if not features:
            return base_format
        
        # Combine base format with features
        format_with_features = base_format + ''.join(features)
        return format_with_features
    
