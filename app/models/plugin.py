from typing import Dict, Any, List, Optional, Union, Type, Set
from pydantic import BaseModel, Field
from enum import Enum
from abc import ABC, abstractmethod


class InputFieldType(str, Enum):
    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    SELECT = "select"
    CHECKBOX = "checkbox"
    FILE = "file"


class InputField(BaseModel):
    name: str = Field(..., description="Field name used as identifier")
    label: str = Field(..., description="Human-readable label for the field")
    field_type: InputFieldType = Field(..., description="Type of input field")
    required: bool = Field(default=True, description="Whether this field is required")
    placeholder: Optional[str] = Field(default=None, description="Placeholder text")
    options: Optional[List[str]] = Field(default=None, description="Options for select fields")
    default_value: Optional[Union[str, int, bool]] = Field(default=None, description="Default value")
    validation: Optional[Dict[str, Any]] = Field(default=None, description="Validation rules")
    help_text: Optional[str] = Field(default=None, description="Help text for the field", alias="help")


class OutputFormat(BaseModel):
    name: str = Field(..., description="Output format name")
    description: str = Field(..., description="Description of the output")
    schema_definition: Optional[Dict[str, Any]] = Field(default=None, description="JSON schema for output validation", alias="schema")


class Dependency(BaseModel):
    name: str
    help_text: Optional[str] = Field(default=None, alias="help")


class PluginDependencies(BaseModel):
    external: Optional[List[Dependency]] = None
    python: Optional[List[Dependency]] = None


class PluginManifest(BaseModel):
    id: str = Field(..., description="Unique plugin identifier")
    name: str = Field(..., description="Human-readable plugin name")
    version: str = Field(..., description="Plugin version")
    description: str = Field(..., description="Plugin description")
    author: Optional[str] = Field(default=None, description="Plugin author")
    inputs: List[InputField] = Field(..., description="Input field definitions")
    output: OutputFormat = Field(..., description="Output format specification")
    tags: Optional[List[str]] = Field(default=None, description="Plugin tags for categorization")
    dependencies: Optional[PluginDependencies] = Field(default=None, description="Plugin dependencies")

    class Config:
        extra = "allow"


class PluginInput(BaseModel):
    plugin_id: str
    data: Dict[str, Any]


class PluginOutput(BaseModel):
    plugin_id: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BasePluginResponse(BaseModel):
    """Base class for all plugin response models"""
    pass


def _model_validate(model_cls: Type[BaseModel], data: Dict[str, Any]) -> BaseModel:
    """Validate a payload against a Pydantic model across v1/v2 APIs."""
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(data)
    return model_cls(**data)


def _model_dump(model_instance: BaseModel) -> Dict[str, Any]:
    """Dump a Pydantic model instance across v1/v2 APIs."""
    if hasattr(model_instance, "model_dump"):
        return model_instance.model_dump()
    return model_instance.dict()


def model_json_schema(model_cls: Type[BaseModel]) -> Dict[str, Any]:
    """Return JSON schema for a Pydantic model across v1/v2 APIs."""
    if hasattr(model_cls, "model_json_schema"):
        return model_cls.model_json_schema()
    return model_cls.schema()


def get_model_fields(model_cls: Type[BaseModel]) -> Dict[str, Any]:
    """Return model fields map across v1/v2 APIs."""
    if hasattr(model_cls, "model_fields"):
        return model_cls.model_fields
    return getattr(model_cls, "__fields__", {})


def is_pydantic_model_class(model_cls: Any) -> bool:
    """Check whether an object is a Pydantic model class."""
    return isinstance(model_cls, type) and issubclass(model_cls, BaseModel)


class BasePlugin(ABC):
    """
    Base class for all plugins. 
    
    RULE: All plugins MUST define a Pydantic model for their response by implementing
    the get_response_model() method and ensure their execute() method returns data
    that validates against this model.
    """

    @classmethod
    def get_input_model(cls) -> Optional[Type[BaseModel]]:
        """
        Optional canonical input contract for this plugin.

        Plugins can migrate incrementally by returning a Pydantic input model.
        If omitted, input validation falls back to manifest validation.
        """
        return None

    @classmethod
    def get_ui_fields(cls) -> Optional[List[InputField]]:
        """
        Optional UI field contract.

        When omitted but get_input_model() is provided, fields are derived from
        the input model schema and field metadata.
        """
        return None
    
    @abstractmethod
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the plugin with the given input data.
        
        Args:
            data: Input data dictionary. For plugins that handle files, the 'input_file'
                  key will contain a dictionary with either a 'temp_path' (for files
                  on disk) or 'content' (for in-memory file data). Plugins MUST
                  handle both cases gracefully.
            
        Returns:
            Dictionary that MUST validate against the model returned by get_response_model()
        """
        pass
    
    @classmethod
    @abstractmethod
    def get_response_model(cls) -> Type[BasePluginResponse]:
        """
        Return the Pydantic model class that defines the structure of this plugin's response.
        
        This is REQUIRED for all plugins. The response from execute() must validate
        against this model.
        
        Returns:
            Pydantic model class inheriting from BasePluginResponse
        """
        pass
    
    def validate_response(self, response_data: Dict[str, Any]) -> BasePluginResponse:
        """
        Validate the response data against the plugin's response model.
        
        Args:
            response_data: The response data to validate
            
        Returns:
            Validated response model instance
            
        Raises:
            ValidationError: If the response doesn't match the model
        """
        response_model = self.get_response_model()
        return _model_validate(response_model, response_data)

    def validate_input(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate raw input against optional class-level input model.

        Returns a normalized dictionary for backward compatibility with
        execute(self, data: Dict[str, Any]).
        """
        input_model = self.get_input_model()
        if not input_model:
            return dict(raw_data)

        validated = _model_validate(input_model, raw_data)
        return _model_dump(validated)

    def run(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Unified plugin execution path: validate input, execute, validate output.
        """
        normalized_input = self.validate_input(raw_data)
        result = self.execute(normalized_input)
        validated_output = self.validate_response(result)
        return _model_dump(validated_output)

    @classmethod
    def get_contract_schema(cls) -> Dict[str, Any]:
        """
        Return canonical contract payload for parity checks and manifest generation.
        """
        contract: Dict[str, Any] = {
            "output_schema": model_json_schema(cls.get_response_model())
        }
        input_model = cls.get_input_model()
        if input_model:
            contract["input_schema"] = model_json_schema(input_model)
            contract["input_fields"] = [
                field.model_dump(by_alias=True, exclude_none=True)
                if hasattr(field, "model_dump")
                else field.dict(by_alias=True, exclude_none=True)
                for field in cls.derive_input_fields()
            ]
        return contract

    @classmethod
    def derive_input_fields(cls) -> List[InputField]:
        """
        Derive InputField metadata from the canonical class contract.
        """
        explicit_fields = cls.get_ui_fields()
        if explicit_fields is not None:
            return explicit_fields

        input_model = cls.get_input_model()
        if not input_model:
            return []

        schema = model_json_schema(input_model)
        properties = schema.get("properties", {})
        required_fields: Set[str] = set(schema.get("required", []))
        model_fields = get_model_fields(input_model)
        derived_fields: List[InputField] = []

        for field_name, field_schema in properties.items():
            model_field = model_fields.get(field_name)
            extras = cls._get_field_extras(model_field)
            field_type = extras.get("field_type") or cls._infer_field_type(field_schema, extras)
            options = extras.get("options")
            enum_values = field_schema.get("enum")
            if options is None and enum_values:
                options = [str(item) for item in enum_values]

            validation = cls._extract_validation_rules(field_schema, extras)
            label = extras.get("label") or field_schema.get("title") or field_name.replace("_", " ").title()

            derived_fields.append(
                InputField(
                    name=field_name,
                    label=label,
                    field_type=field_type,
                    required=field_name in required_fields,
                    placeholder=extras.get("placeholder"),
                    options=options,
                    default_value=field_schema.get("default"),
                    validation=validation or None,
                    help=extras.get("help"),
                )
            )

        return derived_fields

    @staticmethod
    def _infer_field_type(field_schema: Dict[str, Any], extras: Dict[str, Any]) -> InputFieldType:
        schema_type = field_schema.get("type")
        if isinstance(schema_type, list):
            non_null_types = [item for item in schema_type if item != "null"]
            schema_type = non_null_types[0] if non_null_types else "string"

        if field_schema.get("enum") or extras.get("options"):
            return InputFieldType.SELECT
        if schema_type in ("integer", "number"):
            return InputFieldType.NUMBER
        if schema_type == "boolean":
            return InputFieldType.CHECKBOX
        if extras.get("format") == "binary" or field_schema.get("format") == "binary":
            return InputFieldType.FILE
        if schema_type in ("array", "object"):
            return InputFieldType.TEXTAREA
        return InputFieldType.TEXT

    @staticmethod
    def _extract_validation_rules(field_schema: Dict[str, Any], extras: Dict[str, Any]) -> Dict[str, Any]:
        rules = dict(extras.get("validation", {})) if isinstance(extras.get("validation"), dict) else {}
        mapping = {
            "minimum": "min",
            "maximum": "max",
            "minLength": "min_length",
            "maxLength": "max_length",
            "pattern": "pattern",
            "minItems": "min_items",
            "maxItems": "max_items",
        }
        for schema_key, validation_key in mapping.items():
            if schema_key in field_schema and validation_key not in rules:
                rules[validation_key] = field_schema[schema_key]
        return rules

    @staticmethod
    def _get_field_extras(field_info: Any) -> Dict[str, Any]:
        if field_info is None:
            return {}

        json_schema_extra = getattr(field_info, "json_schema_extra", None)
        if isinstance(json_schema_extra, dict):
            return json_schema_extra

        legacy_field_info = getattr(field_info, "field_info", None)
        if legacy_field_info is None:
            return {}

        legacy_extra = getattr(legacy_field_info, "extra", None)
        if isinstance(legacy_extra, dict):
            return legacy_extra

        legacy_json_extra = getattr(legacy_field_info, "json_schema_extra", None)
        if isinstance(legacy_json_extra, dict):
            return legacy_json_extra

        return {}
