"""
Number Comparator Modules
All number comparison and boolean evaluation modules
"""
from typing import Dict, Any, Union
from pydantic import BaseModel, Field
from shared.types import ComparatorModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
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

    def run(self, inputs: Dict[str, Any], cfg: NumberEqualsConfig, context: Any) -> Dict[str, Any]:
        # Extract input
        input_node_id = list(inputs.keys())[0]
        value = inputs[input_node_id]

        # Get output node_id from context
        output_node_id = context.outputs[0].node_id

        # Validate input type
        if not isinstance(value, (int, float)):
            raise TypeError(f"Expected int or float, got {type(value).__name__}")

        # Perform comparison
        if isinstance(value, float) or isinstance(cfg.compare_value, float):
            result = abs(value - cfg.compare_value) <= cfg.tolerance
        else:
            result = value == cfg.compare_value

        return {output_node_id: result}


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
        import math

        # Get the single input value (there should be exactly one)
        if not inputs:
            raise ValueError("No input provided to number comparison")

        # Get the input node_id and value
        input_node_id = list(inputs.keys())[0]
        value = inputs[input_node_id]

        # Get the output node_id from context
        if context and hasattr(context, 'outputs') and context.outputs:
            output_node_id = context.outputs[0].node_id
        else:
            # Fallback to generic output key
            output_node_id = "result"

        # Handle None
        if value is None:
            # None is not greater than any number
            return {output_node_id: False}

        # Validate input is a number (should always be due to type constraints)
        if not isinstance(value, (int, float)):
            raise TypeError(f"Expected int or float, got {type(value).__name__}")

        # Handle special float values
        if math.isnan(value):
            # NaN comparisons always return False
            return {output_node_id: False}

        if math.isinf(value):
            # Positive infinity is greater than any finite threshold
            # Negative infinity is not greater than any threshold
            if value > 0:  # Positive infinity
                return {output_node_id: not math.isinf(cfg.threshold) or cfg.threshold < 0}
            else:  # Negative infinity
                return {output_node_id: False}

        # Handle threshold being infinity or NaN
        if math.isnan(cfg.threshold):
            # Comparison with NaN is always False
            return {output_node_id: False}

        # Perform the comparison
        result = value > cfg.threshold

        return {output_node_id: result}


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

    def run(self, inputs: Dict[str, Any], cfg: NumberLessThanConfig, context: Any) -> Dict[str, Any]:
        import math

        # Extract input
        input_node_id = list(inputs.keys())[0]
        value = inputs[input_node_id]

        # Get output node_id from context
        output_node_id = context.outputs[0].node_id

        # Handle None
        if value is None:
            return {output_node_id: False}

        # Validate input type
        if not isinstance(value, (int, float)):
            raise TypeError(f"Expected int or float, got {type(value).__name__}")

        # Handle special float values
        if math.isnan(value):
            return {output_node_id: False}

        if math.isinf(value):
            if value < 0:  # Negative infinity
                return {output_node_id: not (math.isinf(cfg.threshold) and cfg.threshold < 0)}
            else:  # Positive infinity
                return {output_node_id: False}

        # Handle threshold being infinity or NaN
        if math.isnan(cfg.threshold):
            return {output_node_id: False}

        # Perform the comparison
        result = value < cfg.threshold

        return {output_node_id: result}


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

    def run(self, inputs: Dict[str, Any], cfg: NumberInRangeConfig, context: Any) -> Dict[str, Any]:
        import math

        # Extract input
        input_node_id = list(inputs.keys())[0]
        value = inputs[input_node_id]

        # Get output node_id from context
        output_node_id = context.outputs[0].node_id

        # Handle None
        if value is None:
            return {output_node_id: False}

        # Validate input type
        if not isinstance(value, (int, float)):
            raise TypeError(f"Expected int or float, got {type(value).__name__}")

        # Handle NaN - always outside any range
        if math.isnan(value):
            return {output_node_id: False}

        # Handle infinity
        if math.isinf(value):
            if math.isinf(cfg.min) or math.isinf(cfg.max):
                # Special case: if range bounds include infinity
                if cfg.inclusive:
                    result = cfg.min <= value <= cfg.max
                else:
                    result = cfg.min < value < cfg.max
            else:
                # Finite range, infinite value = not in range
                result = False
            return {output_node_id: result}

        # Normal range check
        if cfg.inclusive:
            result = cfg.min <= value <= cfg.max
        else:
            result = cfg.min < value < cfg.max

        return {output_node_id: result}


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

    def run(self, inputs: Dict[str, Any], cfg: NumberIsEvenConfig, context: Any) -> Dict[str, Any]:
        # Extract input
        input_node_id = list(inputs.keys())[0]
        number = inputs[input_node_id]

        # Get output node_id from context
        output_node_id = context.outputs[0].node_id

        # Validate input type
        if not isinstance(number, int):
            raise TypeError(f"Expected int, got {type(number).__name__}")

        result = number % 2 == 0
        return {output_node_id: result}


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

    def run(self, inputs: Dict[str, Any], cfg: NumberIsOddConfig, context: Any) -> Dict[str, Any]:
        # Extract input
        input_node_id = list(inputs.keys())[0]
        number = inputs[input_node_id]

        # Get output node_id from context
        output_node_id = context.outputs[0].node_id

        # Validate input type
        if not isinstance(number, int):
            raise TypeError(f"Expected int, got {type(number).__name__}")

        result = number % 2 != 0
        return {output_node_id: result}
