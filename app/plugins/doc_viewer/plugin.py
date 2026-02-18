import json
from typing import Dict, Any, Type
from pydantic import BaseModel, Field
from ...models.plugin import BasePlugin, BasePluginResponse
from .models import PrincipiaDocument


class DocViewerResponse(BasePluginResponse):
    """Pydantic model for document viewer plugin response"""
    custom_template: str = Field(..., description="Name of the custom template to use for rendering")
    document: Dict[str, Any] = Field(..., description="Document data for rendering")


class DocViewerInput(BaseModel):
    input_file: Dict[str, Any] = Field(
        ...,
        json_schema_extra={
            "label": "JSON Document",
            "field_type": "file",
            "validation": {"allowed_extensions": ["json"]},
        },
    )


class Plugin(BasePlugin):
    """
    Document Viewer Plugin - Renders a structured JSON document.
    """

    @classmethod
    def get_input_model(cls) -> Type[BaseModel]:
        """Return the canonical input model for this plugin."""
        return DocViewerInput
    
    @classmethod
    def get_response_model(cls) -> Type[BasePluginResponse]:
        """Return the Pydantic model for this plugin's response"""
        return DocViewerResponse
    
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Loads the JSON file and returns the data along with a
        path to the custom template for rendering.
        """
        file_info = data.get("input_file")
        if not file_info:
            raise ValueError("Missing JSON file input")

        try:
            json_content = file_info["content"].decode("utf-8")
            document_data = json.loads(json_content)
            document = PrincipiaDocument(**document_data)
            
            return {
                "custom_template": "doc_viewer_view.html",
                "document": document.model_dump()
            }
        except Exception as e:
            raise ValueError(f"Error processing document: {e}") 
