"""
Number Comparator Modules
All number comparison and boolean evaluation modules
"""
from typing import Dict, Any, Union
from pydantic import BaseModel, Field
from shared.models import ComparatorModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from shared.utils.registry import register


# Number Equals
class NumberEqualsConfig(BaseModel):
    compare_value: Union[int, float] = Field(..., description="Value to compare against")
    tolerance: float = Field(0.0001, description="Tolerance for float comparison (ignored for ints)")

@register
class NumberEquals(ComparatorModule):
    id = "number_equals"
    version = "1.0.0"
    title = "Number Equals"
    description = "Check if input number equals a configured value"
    category = "Number"
    color = "#F59E0B"  # Orange
    ConfigModel = NumberEqualsConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="value",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["int", "float"])
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

    def run(self, inputs: Dict[str, Any], cfg: NumberEqualsConfig, context: Any = None) -> Dict[str, Any]:
        value = list(inputs.values())[0]

        if isinstance(value, float) or isinstance(cfg.compare_value, float):
            result = abs(value - cfg.compare_value) <= cfg.tolerance
        else:
            result = value == cfg.compare_value

        return {"result": result}


# Number Greater Than
class NumberGreaterThanConfig(BaseModel):
    threshold: Union[int, float] = Field(..., description="Threshold value")

@register
class NumberGreaterThan(ComparatorModule):
    id = "number_greater_than"
    version = "1.0.0"
    title = "Number Greater Than"
    description = "Check if input number is greater than a threshold"
    category = "Number"
    color = "#F59E0B"  # Orange
    ConfigModel = NumberGreaterThanConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="value",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["int", "float"])
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

    def run(self, inputs: Dict[str, Any], cfg: NumberGreaterThanConfig, context: Any = None) -> Dict[str, Any]:
        value = list(inputs.values())[0]
        result = value > cfg.threshold
        return {"result": result}


# Number Less Than
class NumberLessThanConfig(BaseModel):
    threshold: Union[int, float] = Field(..., description="Threshold value")

@register
class NumberLessThan(ComparatorModule):
    id = "number_less_than"
    version = "1.0.0"
    title = "Number Less Than"
    description = "Check if input number is less than a threshold"
    category = "Number"
    color = "#F59E0B"  # Orange
    ConfigModel = NumberLessThanConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="value",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["int", "float"])
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

    def run(self, inputs: Dict[str, Any], cfg: NumberLessThanConfig, context: Any = None) -> Dict[str, Any]:
        value = list(inputs.values())[0]
        result = value < cfg.threshold
        return {"result": result}


# Number In Range
class NumberInRangeConfig(BaseModel):
    min: Union[int, float] = Field(..., description="Minimum value (inclusive if inclusive=True)")
    max: Union[int, float] = Field(..., description="Maximum value (inclusive if inclusive=True)")
    inclusive: bool = Field(True, description="Whether range bounds are inclusive")

@register
class NumberInRange(ComparatorModule):
    id = "number_in_range"
    version = "1.0.0"
    title = "Number In Range"
    description = "Check if input number is within a specified range"
    category = "Number"
    color = "#F59E0B"  # Orange
    ConfigModel = NumberInRangeConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="value",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["int", "float"])
                    )
                ]),
                outputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="in_range",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["bool"])
                    )
                ])
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: NumberInRangeConfig, context: Any = None) -> Dict[str, Any]:
        value = list(inputs.values())[0]

        if cfg.inclusive:
            result = cfg.min <= value <= cfg.max
        else:
            result = cfg.min < value < cfg.max

        return {"in_range": result}


# Number Is Even
class NumberIsEvenConfig(BaseModel):
    pass  # No configuration needed

@register
class NumberIsEven(ComparatorModule):
    id = "number_is_even"
    version = "1.0.0"
    title = "Number Is Even"
    description = "Check if input integer is even"
    category = "Number"
    color = "#F59E0B"  # Orange
    ConfigModel = NumberIsEvenConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="number",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["int"])
                    )
                ]),
                outputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="is_even",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["bool"])
                    )
                ])
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: NumberIsEvenConfig, context: Any = None) -> Dict[str, Any]:
        number = list(inputs.values())[0]
        result = number % 2 == 0
        return {"is_even": result}


# Number Is Odd
class NumberIsOddConfig(BaseModel):
    pass  # No configuration needed

@register
class NumberIsOdd(ComparatorModule):
    id = "number_is_odd"
    version = "1.0.0"
    title = "Number Is Odd"
    description = "Check if input integer is odd"
    category = "Number"
    color = "#F59E0B"  # Orange
    ConfigModel = NumberIsOddConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="number",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["int"])
                    )
                ]),
                outputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="is_odd",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["bool"])
                    )
                ])
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: NumberIsOddConfig, context: Any = None) -> Dict[str, Any]:
        number = list(inputs.values())[0]
        result = number % 2 != 0
        return {"is_odd": result}
