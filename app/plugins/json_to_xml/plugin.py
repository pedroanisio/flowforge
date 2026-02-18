import json
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Type
import tempfile
from pathlib import Path
from pydantic import BaseModel, Field
from ...models.plugin import BasePlugin, BasePluginResponse

# Use the pandoc library for parsing
import pandoc
from pandoc.types import (
    Pandoc, Meta, Block, Inline, Str, Space, Code, Emph, Strong, SoftBreak,
    LineBreak, Para, Plain, Header, CodeBlock, BulletList, BlockQuote, Div,
    RawBlock, RawInline, Link, Image, Span, HorizontalRule, Table
)

def _emit_inlines(parent: ET.Element, lst: List[Inline], ignore_line_breaks: bool = False):
    for inl in lst:
        if isinstance(inl, Str):
            parent.text = (parent.text or "") + inl[0]
        elif isinstance(inl, Space):
            parent.text = (parent.text or "") + " "
        elif isinstance(inl, Code):
            attr, text = inl
            ET.SubElement(parent, "C").text = text
        elif isinstance(inl, Emph):
            e = ET.SubElement(parent, "E")
            _emit_inlines(e, inl[0], ignore_line_breaks)
        elif isinstance(inl, Strong):
            s = ET.SubElement(parent, "S")
            _emit_inlines(s, inl[0], ignore_line_breaks)
        elif isinstance(inl, (SoftBreak, LineBreak)):
            if not ignore_line_breaks:
                ET.SubElement(parent, "BR")
        elif isinstance(inl, RawInline):
            format_obj, text = inl
            ET.SubElement(parent, "Raw", format=format_obj[0]).text = text
        elif isinstance(inl, Link):
            attr, inlines, target = inl
            href, title = target
            a = ET.SubElement(parent, "A", href=href, title=title)
            _emit_inlines(a, inlines, ignore_line_breaks)
        elif isinstance(inl, Image):
            attr, inlines, target = inl
            src, title = target
            alt_text = pandoc.write(inlines, format='plain').strip()
            ET.SubElement(parent, "IMG", src=src, title=title, alt=alt_text)
        elif isinstance(inl, Span):
            attr, inlines = inl
            s = ET.SubElement(parent, "SPAN")
            _emit_inlines(s, inlines, ignore_line_breaks)
        else:
            ET.SubElement(parent, "U", t=type(inl).__name__)

def _emit(root: ET.Element, node: Block, ignore_line_breaks: bool = False):
    if isinstance(node, (Para, Plain)):
        elem = ET.SubElement(root, "P")
        _emit_inlines(elem, node[0], ignore_line_breaks)
    elif isinstance(node, Header):
        level, attr, inlines = node
        elem = ET.SubElement(root, "H", l=str(level))
        _emit_inlines(elem, inlines, ignore_line_breaks)
    elif isinstance(node, CodeBlock):
        attr, text = node
        lang = attr[1][0] if attr[1] else ""
        ET.SubElement(root, "C", l=lang).text = text
    elif isinstance(node, BulletList):
        l = ET.SubElement(root, "L")
        for item in node[0]:
            i = ET.SubElement(l, "I")
            for blk in item:
                _emit(i, blk, ignore_line_breaks)
    elif isinstance(node, BlockQuote):
        q = ET.SubElement(root, "Q")
        for blk in node[0]:
            _emit(q, blk, ignore_line_breaks)
    elif isinstance(node, Div):
        attr, blocks = node
        div_elem = ET.SubElement(root, "DIV")
        for blk in blocks:
            _emit(div_elem, blk, ignore_line_breaks)
    elif isinstance(node, RawBlock):
        format_obj, text = node
        ET.SubElement(root, "RawBlock", format=format_obj[0]).text = text
    elif isinstance(node, HorizontalRule):
        ET.SubElement(root, "HR")
    elif isinstance(node, Table):
        # For now, just a placeholder for tables
        ET.SubElement(root, "Table").text = "[Table content]"
    else:
        ET.SubElement(root, "U", t=type(node).__name__)


class JsonToXmlResponse(BasePluginResponse):
    """Pydantic model for JSON to XML converter plugin response"""
    file_path: str = Field(..., description="Path to the converted XML file")
    file_name: str = Field(..., description="Name of the converted XML file")


class JsonToXmlInput(BaseModel):
    input_file: Dict[str, Any] = Field(
        ...,
        json_schema_extra={
            "label": "Pandoc JSON File",
            "field_type": "file",
            "validation": {"allowed_extensions": ["json"]},
            "help": "Upload a Pandoc JSON file (e.g., one generated with 'pandoc -t json -o output.json').",
        },
    )
    ignore_line_breaks: bool = Field(
        default=True,
        json_schema_extra={
            "label": "Ignore Line Breaks",
            "field_type": "checkbox",
            "help": "If checked, soft and hard line breaks will be ignored, resulting in more compact paragraphs.",
        },
    )


class Plugin(BasePlugin):
    """Pandoc JSON to Mini XML Plugin - Converts Pandoc JSON documents into minimal XML format"""

    @classmethod
    def get_input_model(cls) -> Type[BaseModel]:
        """Return the canonical input model for this plugin."""
        return JsonToXmlInput
    
    @classmethod
    def get_response_model(cls) -> Type[BasePluginResponse]:
        """Return the Pydantic model for this plugin's response"""
        return JsonToXmlResponse
    
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        file_info = data.get("input_file")
        if not file_info:
            raise ValueError("Missing JSON file input")

        try:
            ignore_line_breaks = data.get("ignore_line_breaks", False)
            json_string = file_info["content"].decode("utf-8")
            api_version = []
            
            temp_dir = tempfile.mkdtemp()
            input_filename = Path(file_info["filename"])
            output_filename = f"{input_filename.stem}.xml"
            output_path = Path(temp_dir) / output_filename
            
            try:
                raw_doc = json.loads(json_string)
                if isinstance(raw_doc, dict):
                    api_version = raw_doc.get("pandoc-api-version", [])
                doc = pandoc.read(json_string, format='json')
                
                meta, blocks = doc
                root = ET.Element("D", v=".".join(map(str, api_version)))
                
                ET.SubElement(root, "M")
                xml_blocks = ET.SubElement(root, "B")
                
                for blk in blocks:
                    _emit(xml_blocks, blk, ignore_line_breaks)
                
                ET.indent(root)
                xml_output = ET.tostring(root, encoding="unicode")

            except Exception:
                root = ET.Element("D")
                ET.SubElement(root, "B").text = json_string
                ET.indent(root)
                xml_output = ET.tostring(root, encoding="unicode")

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(xml_output)

            return {
                "file_path": str(output_path),
                "file_name": output_filename
            }

        except Exception as e:
            raise RuntimeError(f"An unexpected error occurred during XML conversion: {e}") 
