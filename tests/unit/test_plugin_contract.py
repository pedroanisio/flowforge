from typing import Any, Dict, Type

import pytest
from pydantic import BaseModel, Field, ValidationError

from app.core.plugin_manager import PluginManager
from app.models.plugin import (
    BasePlugin,
    BasePluginResponse,
    InputField,
    InputFieldType,
    OutputFormat,
    PluginManifest,
    model_json_schema,
)


class ExampleInput(BaseModel):
    text: str = Field(
        ...,
        min_length=3,
        max_length=100,
        json_schema_extra={
            "label": "Input Text",
            "field_type": "textarea",
            "placeholder": "Type your text",
            "help": "Minimum three characters.",
        },
    )
    include_meta: bool = Field(default=False)


class ExampleResponse(BasePluginResponse):
    ok: bool
    text_length: int


class ExamplePlugin(BasePlugin):
    @classmethod
    def get_input_model(cls) -> Type[BaseModel]:
        return ExampleInput

    @classmethod
    def get_response_model(cls) -> Type[BasePluginResponse]:
        return ExampleResponse

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {"ok": True, "text_length": len(data["text"])}


def test_derive_input_fields_from_input_model():
    fields = ExamplePlugin.derive_input_fields()
    assert len(fields) == 2

    text_field = next(field for field in fields if field.name == "text")
    assert text_field.label == "Input Text"
    assert text_field.field_type == InputFieldType.TEXTAREA
    assert text_field.required is True
    assert text_field.placeholder == "Type your text"
    assert text_field.help_text == "Minimum three characters."
    assert text_field.validation["min_length"] == 3
    assert text_field.validation["max_length"] == 100


def test_run_validates_input_model():
    plugin = ExamplePlugin()

    result = plugin.run({"text": "hello"})
    assert result == {"ok": True, "text_length": 5}

    with pytest.raises(ValidationError):
        plugin.run({"text": "hi"})


def test_manifest_runtime_parity_reports_drift():
    manifest = PluginManifest(
        id="example",
        name="Example",
        version="1.0.0",
        description="example",
        inputs=[
            InputField(
                name="text",
                label="Text",
                field_type=InputFieldType.TEXT,
                required=True,
            ),
            InputField(
                name="ghost",
                label="Ghost",
                field_type=InputFieldType.TEXT,
                required=False,
            ),
        ],
        output=OutputFormat(
            name="example",
            description="example output",
            schema={
                "type": "object",
                "properties": {
                    "ok": {"type": "boolean"},
                    "extra_field": {"type": "string"},
                },
                "required": ["ok", "extra_field"],
            },
        ),
    )

    warnings = PluginManager._check_manifest_contract_parity(
        manifest=manifest,
        plugin_class=ExamplePlugin,
        response_model=ExamplePlugin.get_response_model(),
    )

    assert any("input manifest is missing fields declared at runtime: include_meta" in warning for warning in warnings)
    assert any("input manifest has fields not declared at runtime: ghost" in warning for warning in warnings)
    assert any("output manifest has fields not declared at runtime: extra_field" in warning for warning in warnings)


def test_manifest_runtime_parity_clean_when_aligned():
    manifest = PluginManifest(
        id="example",
        name="Example",
        version="1.0.0",
        description="example",
        inputs=ExamplePlugin.derive_input_fields(),
        output=OutputFormat(
            name="example",
            description="example output",
            schema=model_json_schema(ExampleResponse),
        ),
    )

    warnings = PluginManager._check_manifest_contract_parity(
        manifest=manifest,
        plugin_class=ExamplePlugin,
        response_model=ExamplePlugin.get_response_model(),
    )

    assert warnings == []


def test_migrated_plugins_define_input_model():
    from app.plugins.text_stat.plugin import Plugin as TextStatPlugin
    from app.plugins.bag_of_words.plugin import Plugin as BagOfWordsPlugin

    assert TextStatPlugin.get_input_model() is not None
    assert BagOfWordsPlugin.get_input_model() is not None
