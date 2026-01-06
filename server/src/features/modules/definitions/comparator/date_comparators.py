"""
Date Comparator Modules
All datetime comparison and boolean evaluation modules
"""
from typing import Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, date
from shared.types import ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.registry import register
from features.modules.base import ComparatorModule


# Date Before
class DateBeforeConfig(BaseModel):
    compare_date: str = Field(..., description="Date to compare against (ISO format YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")

@register
class DateBefore(ComparatorModule):
    id = "date_before"
    version = "1.0.0"
    title = "Date Before"
    description = "Check if input date is before a configured date"
    category = "Date"
    color = "#A855F7"  # Purple
    ConfigModel = DateBeforeConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="date",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["datetime"])
                    )
                ]),
                outputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="is_before",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["bool"])
                    )
                ])
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: DateBeforeConfig, context: Any, services: Any = None) -> Dict[str, Any]:
        # Extract input
        input_node_id = list(inputs.keys())[0]
        input_date = inputs[input_node_id]

        # Get output node_id from context
        output_node_id = context.outputs[0].node_id

        # Handle None
        if input_date is None:
            return {output_node_id: False}

        # Parse compare_date
        try:
            if 'T' in cfg.compare_date:
                compare_date = datetime.fromisoformat(cfg.compare_date)
            else:
                compare_date = datetime.strptime(cfg.compare_date, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"Invalid compare_date format '{cfg.compare_date}': {str(e)}")

        # Ensure input_date is datetime
        if isinstance(input_date, str):
            try:
                input_date = datetime.fromisoformat(input_date)
            except ValueError as e:
                raise ValueError(f"Invalid input date format: {str(e)}")
        elif not isinstance(input_date, datetime):
            raise TypeError(f"Expected datetime or str, got {type(input_date).__name__}")

        result = input_date < compare_date
        return {output_node_id: result}


# Date After
class DateAfterConfig(BaseModel):
    compare_date: str = Field(..., description="Date to compare against (ISO format YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")

@register
class DateAfter(ComparatorModule):
    id = "date_after"
    version = "1.0.0"
    title = "Date After"
    description = "Check if input date is after a configured date"
    category = "Date"
    color = "#A855F7"  # Purple
    ConfigModel = DateAfterConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="date",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["datetime"])
                    )
                ]),
                outputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="is_after",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["bool"])
                    )
                ])
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: DateAfterConfig, context: Any, services: Any = None) -> Dict[str, Any]:
        # Extract input
        input_node_id = list(inputs.keys())[0]
        input_date = inputs[input_node_id]

        # Get output node_id from context
        output_node_id = context.outputs[0].node_id

        # Handle None
        if input_date is None:
            return {output_node_id: False}

        # Parse compare_date
        try:
            if 'T' in cfg.compare_date:
                compare_date = datetime.fromisoformat(cfg.compare_date)
            else:
                compare_date = datetime.strptime(cfg.compare_date, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"Invalid compare_date format '{cfg.compare_date}': {str(e)}")

        # Ensure input_date is datetime
        if isinstance(input_date, str):
            try:
                input_date = datetime.fromisoformat(input_date)
            except ValueError as e:
                raise ValueError(f"Invalid input date format: {str(e)}")
        elif not isinstance(input_date, datetime):
            raise TypeError(f"Expected datetime or str, got {type(input_date).__name__}")

        result = input_date > compare_date
        return {output_node_id: result}


# Date In Range
class DateInRangeConfig(BaseModel):
    start_date: str = Field(..., description="Start date (ISO format YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")
    end_date: str = Field(..., description="End date (ISO format YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")
    inclusive: bool = Field(True, description="Whether range bounds are inclusive")

@register
class DateInRange(ComparatorModule):
    id = "date_in_range"
    version = "1.0.0"
    title = "Date In Range"
    description = "Check if input date is within a specified date range"
    category = "Date"
    color = "#A855F7"  # Purple
    ConfigModel = DateInRangeConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="date",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["datetime"])
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

    def run(self, inputs: Dict[str, Any], cfg: DateInRangeConfig, context: Any, services: Any = None) -> Dict[str, Any]:
        # Extract input
        input_node_id = list(inputs.keys())[0]
        input_date = inputs[input_node_id]

        # Get output node_id from context
        output_node_id = context.outputs[0].node_id

        # Handle None
        if input_date is None:
            return {output_node_id: False}

        # Parse dates
        try:
            if 'T' in cfg.start_date:
                start_date = datetime.fromisoformat(cfg.start_date)
            else:
                start_date = datetime.strptime(cfg.start_date, "%Y-%m-%d")

            if 'T' in cfg.end_date:
                end_date = datetime.fromisoformat(cfg.end_date)
            else:
                end_date = datetime.strptime(cfg.end_date, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"Invalid date range format: {str(e)}")

        # Validate range
        if start_date > end_date:
            raise ValueError(f"Invalid date range: start_date ({cfg.start_date}) is after end_date ({cfg.end_date})")

        # Ensure input_date is datetime
        if isinstance(input_date, str):
            try:
                input_date = datetime.fromisoformat(input_date)
            except ValueError as e:
                raise ValueError(f"Invalid input date format: {str(e)}")
        elif not isinstance(input_date, datetime):
            raise TypeError(f"Expected datetime or str, got {type(input_date).__name__}")

        # Check range
        if cfg.inclusive:
            result = start_date <= input_date <= end_date
        else:
            result = start_date < input_date < end_date

        return {output_node_id: result}


# Date Is Today
class DateIsTodayConfig(BaseModel):
    pass  # No configuration needed - will compare to current date

@register
class DateIsToday(ComparatorModule):
    id = "date_is_today"
    version = "1.0.0"
    title = "Date Is Today"
    description = "Check if input date is today's date (compares date only, ignoring time)"
    category = "Date"
    color = "#A855F7"  # Purple
    ConfigModel = DateIsTodayConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="date",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["datetime"])
                    )
                ]),
                outputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="is_today",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["bool"])
                    )
                ])
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: DateIsTodayConfig, context: Any, services: Any = None) -> Dict[str, Any]:
        # Extract input
        input_node_id = list(inputs.keys())[0]
        input_date = inputs[input_node_id]

        # Get output node_id from context
        output_node_id = context.outputs[0].node_id

        # Handle None
        if input_date is None:
            return {output_node_id: False}

        # Ensure input_date is datetime
        if isinstance(input_date, str):
            try:
                input_date = datetime.fromisoformat(input_date)
            except ValueError as e:
                raise ValueError(f"Invalid input date format: {str(e)}")
        elif not isinstance(input_date, (datetime, date)):
            raise TypeError(f"Expected datetime, date, or str, got {type(input_date).__name__}")

        # Get today's date
        today = date.today()

        # Extract date component from input and compare
        if isinstance(input_date, datetime):
            input_date_only = input_date.date()
        else:
            input_date_only = input_date

        result = input_date_only == today
        return {output_node_id: result}
