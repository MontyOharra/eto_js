"""
String Comparator Modules
All string comparison and boolean evaluation modules
"""
from typing import Dict, Any
from pydantic import BaseModel, Field
import re
from shared.types import ComparatorModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from shared.utils.registry import register


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

    def run(self, inputs: Dict[str, Any], cfg: StringEqualsConfig, context: Any = None) -> Dict[str, Any]:
        value = list(inputs.values())[0]

        if cfg.case_sensitive:
            result = value == cfg.compare_value
        else:
            result = value.lower() == cfg.compare_value.lower()

        return {"result": result}


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

    def run(self, inputs: Dict[str, Any], cfg: StringContainsConfig, context: Any = None) -> Dict[str, Any]:
        text = list(inputs.values())[0]

        if cfg.case_sensitive:
            result = cfg.substring in text
        else:
            result = cfg.substring.lower() in text.lower()

        return {"contains": result}


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

    def run(self, inputs: Dict[str, Any], cfg: StringStartsWithConfig, context: Any = None) -> Dict[str, Any]:
        text = list(inputs.values())[0]

        if cfg.case_sensitive:
            result = text.startswith(cfg.prefix)
        else:
            result = text.lower().startswith(cfg.prefix.lower())

        return {"starts_with": result}


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

    def run(self, inputs: Dict[str, Any], cfg: StringEndsWithConfig, context: Any = None) -> Dict[str, Any]:
        text = list(inputs.values())[0]

        if cfg.case_sensitive:
            result = text.endswith(cfg.suffix)
        else:
            result = text.lower().endswith(cfg.suffix.lower())

        return {"ends_with": result}


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

    def run(self, inputs: Dict[str, Any], cfg: StringMatchesRegexConfig, context: Any = None) -> Dict[str, Any]:
        text = list(inputs.values())[0]

        try:
            result = bool(re.match(cfg.pattern, text))
        except re.error:
            result = False

        return {"matches": result}


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

    def run(self, inputs: Dict[str, Any], cfg: StringIsEmptyConfig, context: Any = None) -> Dict[str, Any]:
        text = list(inputs.values())[0]

        if cfg.trim_whitespace:
            result = len(text.strip()) == 0
        else:
            result = len(text) == 0

        return {"is_empty": result}
