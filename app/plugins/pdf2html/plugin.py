from pathlib import Path
import subprocess
import tempfile
from typing import Dict, Any, Type, List, Literal
import os
import shutil
import logging
import uuid
import time
from pydantic import BaseModel, Field
from ...models.plugin import BasePlugin, BasePluginResponse

# Set up logging
logger = logging.getLogger(__name__)

class Pdf2HtmlResponse(BasePluginResponse):
    """Pydantic model for PDF to HTML converter plugin response"""
    file_path: str = Field(..., description="Path to the converted HTML file")
    file_name: str = Field(..., description="Name of the converted HTML file")
    conversion_details: Dict[str, Any] = Field(default={}, description="Details about the conversion process")
    docker_info: Dict[str, Any] = Field(default={}, description="Information about Docker container execution")


class Pdf2HtmlInput(BaseModel):
    input_file: Dict[str, Any] = Field(
        ...,
        json_schema_extra={
            "label": "Upload PDF File",
            "field_type": "file",
            "validation": {"allowed_extensions": ["pdf"]},
            "help": "Select a PDF file to convert to HTML format",
        },
    )
    zoom: float = Field(
        default=1.3,
        gt=0,
        json_schema_extra={
            "label": "Zoom Level",
            "field_type": "number",
            "placeholder": "1.3",
            "help": "Zoom level for better rendering quality (e.g., 1.0 = 100%, 1.3 = 130%)",
        },
    )
    embed_css: bool = Field(
        default=True,
        json_schema_extra={
            "label": "Embed CSS",
            "field_type": "checkbox",
            "help": "Embed CSS styles in the HTML file for better portability",
        },
    )
    embed_javascript: bool = Field(
        default=True,
        json_schema_extra={
            "label": "Embed JavaScript",
            "field_type": "checkbox",
            "help": "Embed JavaScript into the HTML file. Disabling this can reduce file size but may break functionality.",
        },
    )
    optimize_text: bool = Field(
        default=True,
        json_schema_extra={
            "label": "Optimize Text",
            "field_type": "checkbox",
            "help": "Reduces the number of HTML elements used for text, which can significantly shrink file size.",
        },
    )
    embed_images: bool = Field(
        default=True,
        json_schema_extra={
            "label": "Embed Images",
            "field_type": "checkbox",
            "help": "Embed images directly in the HTML file as base64 data",
        },
    )
    output_filename: str = Field(
        default="",
        json_schema_extra={
            "label": "Output Filename (optional)",
            "field_type": "text",
            "placeholder": "document.html",
            "help": "Specify custom output filename. If empty, uses original PDF name with .html extension",
        },
    )
    font_format: Literal["woff", "ttf", "otf", "svg"] = Field(
        default="woff",
        json_schema_extra={
            "label": "Font Format",
            "field_type": "select",
            "options": ["woff", "ttf", "otf", "svg"],
            "help": "Font format used in the generated HTML.",
        },
    )
    printing: int = Field(
        default=0,
        ge=0,
        le=1,
        json_schema_extra={
            "label": "Printing Mode",
            "field_type": "number",
            "help": "Set to 1 to enable print-optimized output.",
        },
    )
    font_size_multiplier: float = Field(
        default=4.0,
        gt=0,
        json_schema_extra={
            "label": "Font Size Multiplier",
            "field_type": "number",
            "help": "Multiplier for font size precision in output rendering.",
        },
    )


class Plugin(BasePlugin):
    """PDF to HTML Converter Plugin - Converts PDF files to HTML using pdf2htmlEX in Docker"""

    @classmethod
    def get_input_model(cls) -> Type[BaseModel]:
        """Return the canonical input model for this plugin."""
        return Pdf2HtmlInput
    
    @classmethod
    def get_response_model(cls) -> Type[BasePluginResponse]:
        """Return the Pydantic model for this plugin's response"""
        return Pdf2HtmlResponse
    
    def _ensure_downloads_directory(self) -> Path:
        """Ensure downloads directory exists and return its path"""
        downloads_dir = Path("/app/data/downloads")
        downloads_dir.mkdir(parents=True, exist_ok=True)
        return downloads_dir
    
    def _ensure_shared_directory(self) -> Path:
        """Ensure shared directory exists and return its path"""
        shared_dir = Path("/app/shared")
        shared_dir.mkdir(parents=True, exist_ok=True)
        return shared_dir
    
    def _move_to_downloads(self, temp_file_path: Path, original_filename: str) -> Path:
        """Move file from temp directory to permanent downloads directory"""
        downloads_dir = self._ensure_downloads_directory()
        
        # Create unique filename to avoid conflicts
        unique_id = str(uuid.uuid4())[:8]
        file_stem = temp_file_path.stem
        file_suffix = temp_file_path.suffix
        safe_filename = f"{file_stem}_{unique_id}{file_suffix}"
        
        permanent_path = downloads_dir / safe_filename
        
        # Move the file
        shutil.move(str(temp_file_path), str(permanent_path))
        logger.info(f"Moved output file to permanent location: {permanent_path}")
        
        return permanent_path
    
    def _validate_input_file(self, filename: str, content: bytes) -> Dict[str, Any]:
        """Validate input PDF file and return diagnostics"""
        file_size = len(content)
        file_ext = Path(filename).suffix.lower()
        
        diagnostics = {
            "filename": filename,
            "file_size": file_size,
            "file_extension": file_ext,
            "size_mb": round(file_size / (1024 * 1024), 2)
        }
        
        # Check for potential issues
        if file_size == 0:
            raise ValueError("Input PDF file is empty")
        if file_size > 500 * 1024 * 1024:  # 500MB limit for PDFs
            raise ValueError(f"Input PDF file too large: {diagnostics['size_mb']}MB (max 500MB)")
        if file_ext != '.pdf':
            raise ValueError(f"Invalid file extension: {file_ext}. Only PDF files are supported.")
            
        return diagnostics
    
    def _check_pdf2htmlex_service(self) -> Dict[str, Any]:
        """Check if pdf2htmlEX service container is available and get its actual name"""
        service_info = {
            "service_available": False,
            "container_name": None,
            "error_message": None
        }
        
        try:
            # Get the service host from environment or use default
            service_host = os.environ.get("PDF2HTMLEX_SERVICE_HOST", "pdf2htmlex-service")
            
            # Find the actual container name using docker ps
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={service_host}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                actual_container_name = result.stdout.strip()
                service_info["service_available"] = True
                service_info["container_name"] = actual_container_name
                logger.info(f"pdf2htmlEX service found: {actual_container_name}")
            else:
                service_info["error_message"] = f"pdf2htmlEX service container not found or not running"
                
        except FileNotFoundError:
            service_info["error_message"] = "Docker command not available"
        except subprocess.TimeoutExpired:
            service_info["error_message"] = "Docker command timed out"
        except Exception as e:
            service_info["error_message"] = f"Error checking pdf2htmlEX service: {e}"
        
        return service_info
    
    def _check_pdf2htmlex_service_dependency(self) -> Dict[str, Any]:
        """Custom dependency checker method for plugin manager"""
        return self._check_pdf2htmlex_service()
    
    def _to_bool(self, value) -> bool:
        """Convert various value types to boolean (handles web form inputs)"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on', 'checked')
        if isinstance(value, (int, float)):
            return bool(value)
        return bool(value)  # fallback
    
    def _execute_pdf2htmlex_in_service(self, container_name: str, input_filename: str, 
                                      zoom: float, embed_css: bool, embed_javascript: bool, 
                                      embed_images: bool, optimize_text: bool, font_format: str,
                                      printing: int, font_size_multiplier: float) -> Dict[str, Any]:
        """Execute pdf2htmlEX in the service container via docker exec"""
        
        # Build pdf2htmlEX command
        pdf2htmlex_cmd = ["pdf2htmlEX"]
        
        # Add options
        if zoom and zoom > 0:
            pdf2htmlex_cmd.extend(["--zoom", str(zoom)])
        
        pdf2htmlex_cmd.append(f"--embed-css={int(embed_css)}")
        pdf2htmlex_cmd.append(f"--embed-javascript={int(embed_javascript)}")
        pdf2htmlex_cmd.append(f"--embed-image={int(embed_images)}")
        pdf2htmlex_cmd.append(f"--optimize-text={int(optimize_text)}")
        pdf2htmlex_cmd.append(f"--font-format={font_format}")
        pdf2htmlex_cmd.append(f"--printing={printing}")
        pdf2htmlex_cmd.append(f"--font-size-multiplier={font_size_multiplier}")

        # Set destination directory and add input file
        pdf2htmlex_cmd.extend(["--dest-dir", "/shared"])
        pdf2htmlex_cmd.append(input_filename)
        
        # Build docker exec command
        docker_cmd = ["docker", "exec", container_name] + pdf2htmlex_cmd
        
        logger.info(f"Executing pdf2htmlEX: {' '.join(pdf2htmlex_cmd)}")
        
        # Execute the command
        start_time = time.time()
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
            check=False
        )
        execution_time = time.time() - start_time
        
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "execution_time": execution_time,
            "command": ' '.join(pdf2htmlex_cmd)
        }
    

    
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        input_file_info = data.get("input_file")
        
        # Convert zoom to float if it's a string (from web form)
        zoom_raw = data.get("zoom", 1.3)
        try:
            zoom = float(zoom_raw) if zoom_raw is not None else 1.3
        except (ValueError, TypeError):
            zoom = 1.3  # fallback to default
            
        # Convert boolean parameters (web forms may send strings)
        embed_css = self._to_bool(data.get("embed_css", True))
        embed_javascript = self._to_bool(data.get("embed_javascript", True))
        embed_images = self._to_bool(data.get("embed_images", True))
        optimize_text = self._to_bool(data.get("optimize_text", True))
        output_filename = data.get("output_filename", "").strip()

        # Get other optimization parameters with defaults
        font_format = data.get("font_format", "woff")
        printing = data.get("printing", 0)
        font_size_multiplier = data.get("font_size_multiplier", 4.0)

        if not input_file_info:
            raise ValueError("Missing input PDF file")

        shared_dir = None
        
        try:
            # Check pdf2htmlEX service availability
            service_info = self._check_pdf2htmlex_service()
            if not service_info["service_available"]:
                error_msg = "pdf2htmlEX conversion service is not available."
                if service_info["error_message"]:
                    error_msg += f"\n\nError: {service_info['error_message']}"
                error_msg += "\n\n🔧 Solutions:"
                error_msg += "\n  • Ensure docker-compose services are running"
                error_msg += "\n  • Check: docker-compose ps"
                error_msg += "\n  • Restart services: docker-compose up -d"
                raise RuntimeError(error_msg)
            
            # Get shared directory
            shared_dir = self._ensure_shared_directory()
            logger.info(f"Using shared directory: {shared_dir}")
            
            # Handle both streaming (temp_path) and legacy (content) input formats
            input_filename = input_file_info["filename"]
            
            if "temp_path" in input_file_info:
                # New streaming format - file already on disk
                temp_input_path = Path(input_file_info["temp_path"])
                
                # Move to our shared directory for processing by service
                input_path = shared_dir / input_filename
                shutil.move(str(temp_input_path), str(input_path))
                logger.info(f"Moved streamed file to shared directory: {input_path}")

                # For validation, we need to read the content temporarily
                with open(input_path, "rb") as f:
                    input_file_content = f.read()

            elif "content" in input_file_info:
                # Legacy format - content in memory
                input_file_content = input_file_info["content"]
                
                # Write input file to shared directory
                input_path = shared_dir / input_filename
                with open(input_path, "wb") as f:
                    f.write(input_file_content)
                logger.info(f"Wrote legacy content to shared directory: {input_path}")
            else:
                raise ValueError("Input file data is missing. 'input_file' must contain either 'temp_path' or 'content'.")
            
            file_diagnostics = self._validate_input_file(input_filename, input_file_content)
            logger.info(f"Input PDF file diagnostics: {file_diagnostics}")
            
            # Determine output filename
            if not output_filename:
                output_filename = f"{Path(input_filename).stem}.html"
            elif not output_filename.endswith('.html'):
                output_filename += '.html'
            
            # Execute pdf2htmlEX in the service container
            container_name = service_info["container_name"]
            conversion_result = self._execute_pdf2htmlex_in_service(
                container_name, input_filename, zoom, embed_css, embed_javascript, embed_images,
                optimize_text, font_format, printing, font_size_multiplier
            )
            
            # Check if conversion was successful
            if conversion_result["returncode"] != 0:
                # Prepare detailed error information
                error_details = {
                    "command": conversion_result["command"],
                    "exit_code": conversion_result["returncode"],
                    "stdout": conversion_result["stdout"],
                    "stderr": conversion_result["stderr"],
                    "execution_time": conversion_result["execution_time"],
                    "service_info": service_info,
                    "input_file": file_diagnostics
                }
                
                # Create user-friendly error message
                error_msg = f"pdf2htmlEX conversion failed with exit code {conversion_result['returncode']}"
                
                if conversion_result["stderr"]:
                    error_msg += f"\n\nError Details:\n{conversion_result['stderr']}"
                
                if conversion_result["stdout"]:
                    error_msg += f"\n\nOutput:\n{conversion_result['stdout']}"
                
                # Add specific guidance based on common issues
                if "Permission denied" in conversion_result["stderr"]:
                    error_msg += "\n\n💡 Permission issues detected:"
                    error_msg += "\n  • Check shared volume permissions"
                    error_msg += "\n  • Restart docker-compose services"
                
                if "No such file or directory" in conversion_result["stderr"]:
                    error_msg += "\n\n💡 File not found issues:"
                    error_msg += "\n  • PDF file may be corrupted"
                    error_msg += "\n  • Check if the PDF can be opened normally"
                    error_msg += "\n  • Verify shared volume is properly mounted"
                
                # Log detailed error for debugging
                logger.error(f"pdf2htmlEX conversion failed: {error_details}")
                
                raise RuntimeError(error_msg)
            
            # Find the generated HTML file in shared directory
            html_files = list(shared_dir.glob("*.html"))
            if not html_files:
                raise RuntimeError("pdf2htmlEX completed successfully but no HTML file was created")
            
            # Use the first HTML file found (should be only one)
            generated_html_path = html_files[0]
            final_output_filename = output_filename if output_filename else generated_html_path.name
            
            # Get output file size for diagnostics
            output_size = generated_html_path.stat().st_size
            
            # Move file to permanent downloads directory BEFORE cleanup
            permanent_file_path = self._move_to_downloads(generated_html_path, final_output_filename)
            
            # Prepare conversion details
            conversion_details = {
                "input_file": file_diagnostics,
                "output_file": {
                    "filename": final_output_filename,
                    "size_bytes": output_size,
                    "size_mb": round(output_size / (1024 * 1024), 2)
                },
                "conversion_settings": {
                    "zoom": zoom,
                    "embed_css": embed_css,
                    "embed_javascript": embed_javascript,
                    "embed_images": embed_images,
                    "optimize_text": optimize_text,
                    "font_format": font_format,
                    "printing": printing,
                    "font_size_multiplier": font_size_multiplier
                },
                "execution_time_seconds": round(conversion_result["execution_time"], 2),
                "conversion_successful": True,
                "shared_directory": str(shared_dir),
                "permanent_location": str(permanent_file_path),
                "pdf2htmlex_command": conversion_result["command"]
            }
            
            # Add service info to response
            docker_response_info = {
                "service_container": service_info.get("container_name"),
                "execution_time": conversion_result["execution_time"],
                "exit_code": conversion_result["returncode"],
                "service_available": service_info["service_available"]
            }
            
            logger.info(f"PDF to HTML conversion successful: {conversion_details}")
            
            return {
                "file_path": str(permanent_file_path),
                "file_name": final_output_filename,
                "conversion_details": conversion_details,
                "docker_info": docker_response_info
            }
            
        except subprocess.TimeoutExpired:
            error_msg = "pdf2htmlEX conversion timed out (10 minutes). The PDF file may be too large or complex."
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
        except Exception as e:
            logger.error(f"Unexpected error in pdf2htmlEX conversion: {e}")
            raise RuntimeError(f"An unexpected error occurred during conversion: {e}")
            
        finally:
            # Clean up shared directory files (keep directory)
            if shared_dir and shared_dir.exists():
                try:
                    # Remove PDF and any leftover HTML files from shared directory
                    for file_path in shared_dir.glob("*"):
                        if file_path.is_file():
                            file_path.unlink()
                            logger.info(f"Cleaned up shared file: {file_path.name}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up shared directory files: {cleanup_error}") 
