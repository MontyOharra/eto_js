"""
String Comparator Modules
All string comparison and boolean evaluation modules
"""
from typing import Dict, Any
from pydantic import BaseModel, Field
import re
from shared.types import ComparatorModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register


# String Equals
class StringEqualsConfig(BaseModel):
    compare_value: str = Field(..., description="Value to compare against")
    case_sensitive: bool = Field(True, description="Whether comparison is case-sensitive")

@register
class StringEquals(ComparatorModule):
    id = "string_equals"
    version = "1.0.0"
    title = "String Equals"
    description = "Check if input string equals a configured value"
    category = "String"
    color = "#3B82F6"  # Blue
    ConfigModel = StringEqualsConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="value",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    )
                ]),
                outputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="result",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["bool"])
                    )
                ])
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: StringEqualsConfig, context: Any) -> Dict[str, Any]:
        # Extract input
        input_node_id = list(inputs.keys())[0]
        value = inputs[input_node_id]

        # Get output node_id from context
        output_node_id = context.outputs[0].node_id

        # Handle None
        if value is None:
            return {output_node_id: False}

        # Validate input type
        if not isinstance(value, str):
            raise TypeError(f"Expected str, got {type(value).__name__}")

        # Perform comparison
        if cfg.case_sensitive:
            result = value == cfg.compare_value
        else:
            result = value.lower() == cfg.compare_value.lower()

        return {output_node_id: result}


# String Contains
class StringContainsConfig(BaseModel):
    substring: str = Field(..., description="Substring to search for")
    case_sensitive: bool = Field(True, description="Whether search is case-sensitive")

@register
class StringContains(ComparatorModule):
    id = "string_contains"
    version = "1.0.0"
    title = "String Contains"
    description = "Check if input string contains a substring"
    category = "String"
    color = "#3B82F6"  # Blue
    ConfigModel = StringContainsConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="text",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    )
                ]),
                outputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="contains",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["bool"])
                    )
                ])
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: StringContainsConfig, context: Any) -> Dict[str, Any]:
        # Extract input
        input_node_id = list(inputs.keys())[0]
        text = inputs[input_node_id]

        # Get output node_id from context
        output_node_id = context.outputs[0].node_id

        # Handle None
        if text is None:
            return {output_node_id: False}

        # Validate input type
        if not isinstance(text, str):
            raise TypeError(f"Expected str, got {type(text).__name__}")

        # Perform contains check
        if cfg.case_sensitive:
            result = cfg.substring in text
        else:
            result = cfg.substring.lower() in text.lower()

        return {output_node_id: result}


# String Starts With
class StringStartsWithConfig(BaseModel):
    prefix: str = Field(..., description="Prefix to check for")
    case_sensitive: bool = Field(True, description="Whether check is case-sensitive")

@register
class StringStartsWith(ComparatorModule):
    id = "string_starts_with"
    version = "1.0.0"
    title = "String Starts With"
    description = "Check if input string starts with a prefix"
    category = "String"
    color = "#3B82F6"  # Blue
    ConfigModel = StringStartsWithConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="text",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    )
                ]),
                outputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="starts_with",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["bool"])
                    )
                ])
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: StringStartsWithConfig, context: Any) -> Dict[str, Any]:
        # Extract input
        input_node_id = list(inputs.keys())[0]
        text = inputs[input_node_id]

        # Get output node_id from context
        output_node_id = context.outputs[0].node_id

        # Handle None
        if text is None:
            return {output_node_id: False}

        # Validate input type
        if not isinstance(text, str):
            raise TypeError(f"Expected str, got {type(text).__name__}")

        # Perform starts with check
        if cfg.case_sensitive:
            result = text.startswith(cfg.prefix)
        else:
            result = text.lower().startswith(cfg.prefix.lower())

        return {output_node_id: result}


# String Ends With
class StringEndsWithConfig(BaseModel):
    suffix: str = Field(..., description="Suffix to check for")
    case_sensitive: bool = Field(True, description="Whether check is case-sensitive")

@register
class StringEndsWith(ComparatorModule):
    id = "string_ends_with"
    version = "1.0.0"
    title = "String Ends With"
    description = "Check if input string ends with a suffix"
    category = "String"
    color = "#3B82F6"  # Blue
    ConfigModel = StringEndsWithConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="text",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    )
                ]),
                outputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="ends_with",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["bool"])
                    )
                ])
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: StringEndsWithConfig, context: Any) -> Dict[str, Any]:
        # Extract input
        input_node_id = list(inputs.keys())[0]
        text = inputs[input_node_id]

        # Get output node_id from context
        output_node_id = context.outputs[0].node_id

        # Handle None
        if text is None:
            return {output_node_id: False}

        # Validate input type
        if not isinstance(text, str):
            raise TypeError(f"Expected str, got {type(text).__name__}")

        # Perform ends with check
        if cfg.case_sensitive:
            result = text.endswith(cfg.suffix)
        else:
            result = text.lower().endswith(cfg.suffix.lower())

        return {output_node_id: result}


# String Regex Match
class StringMatchesRegexConfig(BaseModel):
    pattern: str = Field(..., description="Regular expression pattern to match")

@register
class StringMatchesRegex(ComparatorModule):
    id = "string_matches_regex"
    version = "1.0.0"
    title = "String Matches Regex"
    description = "Check if input string matches a regular expression pattern"
    category = "String"
    color = "#3B82F6"  # Blue
    ConfigModel = StringMatchesRegexConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="text",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    )
                ]),
                outputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="matches",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["bool"])
                    )
                ])
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: StringMatchesRegexConfig, context: Any) -> Dict[str, Any]:
        # Extract input
        input_node_id = list(inputs.keys())[0]
        text = inputs[input_node_id]

        # Get output node_id from context
        output_node_id = context.outputs[0].node_id

        # Handle None
        if text is None:
            return {output_node_id: False}

        # Validate input type
        if not isinstance(text, str):
            raise TypeError(f"Expected str, got {type(text).__name__}")

        # Perform regex match
        try:
            result = bool(re.match(cfg.pattern, text))
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{cfg.pattern}': {str(e)}")

        return {output_node_id: result}


# String Is Empty
class StringIsEmptyConfig(BaseModel):
    trim_whitespace: bool = Field(True, description="Whether to trim whitespace before checking")

@register
class StringIsEmpty(ComparatorModule):
    id = "string_is_empty"
    version = "1.0.0"
    title = "String Is Empty"
    description = "Check if input string is empty or contains only whitespace"
    category = "String"
    color = "#3B82F6"  # Blue
    ConfigModel = StringIsEmptyConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="text",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    )
                ]),
                outputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="is_empty",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["bool"])
                    )
                ])
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: StringIsEmptyConfig, context: Any) -> Dict[str, Any]:
        # Extract input
        input_node_id = list(inputs.keys())[0]
        text = inputs[input_node_id]

        # Get output node_id from context
        output_node_id = context.outputs[0].node_id

        # Handle None - None is considered "empty"
        if text is None:
            return {output_node_id: True}

        # Validate input type
        if not isinstance(text, str):
            raise TypeError(f"Expected str, got {type(text).__name__}")

        # Check if empty
        if cfg.trim_whitespace:
            result = len(text.strip()) == 0
        else:
            result = len(text) == 0

        return {output_node_id: result}
