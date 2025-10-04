"""
Date Comparator Modules
All datetime comparison and boolean evaluation modules
"""
from typing import Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, date
from src.features.modules.core.contracts import ComparatorModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from src.features.modules.core.registry import register


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

    def run(self, inputs: Dict[str, Any], cfg: DateBeforeConfig, context: Any = None) -> Dict[str, Any]:
        input_date = list(inputs.values())[0]

        # Parse compare_date
        try:
            if 'T' in cfg.compare_date:
                compare_date = datetime.fromisoformat(cfg.compare_date)
            else:
                compare_date = datetime.strptime(cfg.compare_date, "%Y-%m-%d")
        except ValueError:
            return {"is_before": False}

        # Ensure input_date is datetime
        if isinstance(input_date, str):
            try:
                input_date = datetime.fromisoformat(input_date)
            except ValueError:
                return {"is_before": False}

        result = input_date < compare_date
        return {"is_before": result}


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

    def run(self, inputs: Dict[str, Any], cfg: DateAfterConfig, context: Any = None) -> Dict[str, Any]:
        input_date = list(inputs.values())[0]

        # Parse compare_date
        try:
            if 'T' in cfg.compare_date:
                compare_date = datetime.fromisoformat(cfg.compare_date)
            else:
                compare_date = datetime.strptime(cfg.compare_date, "%Y-%m-%d")
        except ValueError:
            return {"is_after": False}

        # Ensure input_date is datetime
        if isinstance(input_date, str):
            try:
                input_date = datetime.fromisoformat(input_date)
            except ValueError:
                return {"is_after": False}

        result = input_date > compare_date
        return {"is_after": result}


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

    def run(self, inputs: Dict[str, Any], cfg: DateInRangeConfig, context: Any = None) -> Dict[str, Any]:
        input_date = list(inputs.values())[0]

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
        except ValueError:
            return {"in_range": False}

        # Ensure input_date is datetime
        if isinstance(input_date, str):
            try:
                input_date = datetime.fromisoformat(input_date)
            except ValueError:
                return {"in_range": False}

        if cfg.inclusive:
            result = start_date <= input_date <= end_date
        else:
            result = start_date < input_date < end_date

        return {"in_range": result}


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

    def run(self, inputs: Dict[str, Any], cfg: DateIsTodayConfig, context: Any = None) -> Dict[str, Any]:
        input_date = list(inputs.values())[0]

        # Ensure input_date is datetime
        if isinstance(input_date, str):
            try:
                input_date = datetime.fromisoformat(input_date)
            except ValueError:
                return {"is_today": False}

        # Get today's date
        today = date.today()

        # Extract date component from input and compare
        if isinstance(input_date, datetime):
            input_date_only = input_date.date()
        else:
            input_date_only = input_date

        result = input_date_only == today
        return {"is_today": result}
