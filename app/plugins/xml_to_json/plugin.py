import xml.etree.ElementTree as ET
from typing import List, Union, Optional, Dict, Any, Type
import tempfile
from pathlib import Path
from pydantic import BaseModel, Field
from ...models.plugin import BasePlugin, BasePluginResponse

from .models import (
    PrincipiaDocument, DocumentMetadata, ContentBlock, InlineContent,
    TextNode, EmphasisNode, StructuralNode, RawHtmlNode, HeadingNode,
    ParagraphNode, DivNode, QuoteNode
)

def parse_element(element: ET.Element) -> List[Union[ContentBlock, InlineContent]]:
    nodes = []
    if element.text and element.text.strip():
        nodes.append(TextNode(content=element.text.strip()))

    for child in element:
        tag = child.tag
        if tag == "H":
            nodes.append(HeadingNode(
                level=int(child.attrib.get('l', 0)),
                content=parse_element(child)
            ))
        elif tag == "P":
            s_tag = child.find('S')
            label = s_tag.text.strip() if s_tag is not None and s_tag.text else None
            nodes.append(ParagraphNode(
                semantic_label=label,
                content=parse_element(child)
            ))
        elif tag == "DIV":
            nodes.append(DivNode(content=parse_element(child)))
        elif tag == "Q":
            nodes.append(QuoteNode(content=parse_element(child)))
        elif tag in ("RawBlock", "Raw"):
             if child.text and child.text.strip():
                nodes.append(RawHtmlNode(content=child.text.strip()))
        elif tag == "E":
            if child.text and child.text.strip():
                nodes.append(EmphasisNode(content=child.text.strip()))
        elif tag == "U":
            nodes.append(StructuralNode(element_type=child.attrib.get('t', 'Unknown')))
        elif tag == "S": 
            pass
            
        if child.tail and child.tail.strip():
            nodes.append(TextNode(content=child.tail.strip()))
    return nodes

def extract_metadata(root: ET.Element) -> DocumentMetadata:
    meta = {}
    for p_tag in root.findall('.//P[S]'):
        label_tag = p_tag.find('S')
        if label_tag is not None and label_tag.text:
            label = label_tag.text.strip().lower().replace(' ', '_')
            content = "".join(p_tag.itertext()).replace(label_tag.text, "").strip()
            if ':' in content:
                content = content.split(':', 1)[1].strip()
            meta[label] = content
    return DocumentMetadata(**meta)

def create_structured_dataset(xml_content: str) -> PrincipiaDocument:
    root = ET.fromstring(xml_content)
    body_element = root.find('B')
    if body_element is None:
        raise ValueError("Could not find the main <B> content block in the XML.")
    metadata = extract_metadata(body_element)
    parsed_body = parse_element(body_element)
    return PrincipiaDocument(metadata=metadata, body=parsed_body)


class XmlToJsonResponse(BasePluginResponse):
    """Pydantic model for XML to JSON converter plugin response"""
    file_path: str = Field(..., description="Path to the converted JSON file")
    file_name: str = Field(..., description="Name of the converted JSON file")


class XmlToJsonInput(BaseModel):
    input_file: Dict[str, Any] = Field(
        ...,
        json_schema_extra={
            "label": "XML Source File",
            "field_type": "file",
            "validation": {"allowed_extensions": ["xml"]},
            "help": "Upload the XML file to be parsed into a structured JSON document.",
        },
    )


class Plugin(BasePlugin):
    """XML to Structured JSON Plugin - Converts XML documents into structured JSON format"""

    @classmethod
    def get_input_model(cls) -> Type[BaseModel]:
        """Return the canonical input model for this plugin."""
        return XmlToJsonInput
    
    @classmethod
    def get_response_model(cls) -> Type[BasePluginResponse]:
        """Return the Pydantic model for this plugin's response"""
        return XmlToJsonResponse
    
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        file_info = data.get("input_file")
        if not file_info:
            raise ValueError("Missing XML file input")

        xml_content = file_info["content"].decode("utf-8")
        structured_doc = create_structured_dataset(xml_content)
        
        json_output = structured_doc.model_dump_json(indent=2)
        
        temp_dir = tempfile.mkdtemp()
        input_filename = Path(file_info["filename"])
        output_filename = f"{input_filename.stem}.json"
        output_path = Path(temp_dir) / output_filename
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_output)
            
        return {
            "file_path": str(output_path),
            "file_name": output_filename
        } 
