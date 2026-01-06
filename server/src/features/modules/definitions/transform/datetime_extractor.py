"""
DateTime Extractor Transform Module
Uses OpenAI API to extract date and time information from varied text formats
"""
import logging
import os
import json
from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel

from shared.types import ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.registry import register
from features.modules.base import TransformModule

logger = logging.getLogger(__name__)


class DateTimeExtractorConfig(BaseModel):
    """Configuration for DateTime Extractor"""
    # No configuration needed - uses fixed prompt and outputs
    pass


@register
class DateTimeExtractor(TransformModule):
    """
    DateTime Extractor transform module
    Uses OpenAI API to extract date and time information from varied text formats

    Outputs full datetime objects:
    - time_start: Combined date + start time as datetime
    - time_end: Combined date + end time as datetime

    Handles various customer formats and edge cases:
    - Single time values (infers if it's start or end based on context)
    - "at {time}" format (start_time = end_time)
    - Year inference for dates like "1/2" based on current context
    - Missing date or time values (returns null)
    """

    # Class metadata
    id = "datetime_extractor"
    version = "1.0.0"
    title = "DateTime Extractor"
    description = "Extract time start/end as full datetime objects using AI"
    category = "LLM"
    color = "#F97316"  # Orange

    # Configuration model
    ConfigModel = DateTimeExtractorConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="text",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="time_start",
                            typing=NodeTypeRule(allowed_types=["datetime"]),
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            label="time_end",
                            typing=NodeTypeRule(allowed_types=["datetime"]),
                            min_count=1,
                            max_count=1
                        )
                    ]
                )
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: DateTimeExtractorConfig, context: Any, services: Any = None) -> Dict[str, Any]:
        """
        Execute datetime extraction

        Args:
            inputs: Dictionary with text input
            cfg: Validated configuration (empty for this module)
            context: Execution context with ordered inputs/outputs
            services: Not used for this module

        Returns:
            Dictionary with time_start and time_end as datetime objects
        """
        # Import OpenAI here to avoid import errors if not installed
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai library is required for datetime extraction. "
                "Install it with: pip install openai"
            )

        # Get API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required for datetime extraction. "
                "Please set it in your .env file."
            )

        # Get input text
        input_node_id = list(inputs.keys())[0]
        input_text = inputs[input_node_id]

        # Handle None/empty input
        if not input_text:
            logger.warning("Empty text provided to datetime extractor")
            return {
                context.outputs[0].node_id: None,  # time_start
                context.outputs[1].node_id: None   # time_end
            }

        logger.info(f"Extracting date/time from text: '{input_text}'")

        # Build the extraction prompt
        system_prompt = self._build_system_prompt()

        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)

        try:
            # Call OpenAI API
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": input_text}
                ],
                temperature=0.0,  # Deterministic
                response_format={"type": "json_object"}
            )

            # Parse the JSON response
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("Empty response from LLM")
            extracted_data = json.loads(content)

            logger.info(f"Extracted date/time: {extracted_data}")

        except Exception as e:
            logger.error(f"DateTime extraction failed: {e}")
            raise ValueError(f"DateTime extraction failed: {e}")

        # Extract values from LLM response
        date_value = extracted_data.get("date")
        start_time_value = extracted_data.get("start_time")
        end_time_value = extracted_data.get("end_time")

        # Combine date and times into full datetime objects
        time_start = None
        time_end = None

        if date_value:
            if start_time_value:
                try:
                    time_start = datetime.strptime(
                        f"{date_value} {start_time_value}", "%Y-%m-%d %H:%M"
                    )
                except ValueError:
                    logger.warning(f"Failed to parse start datetime: {date_value} {start_time_value}")

            if end_time_value:
                try:
                    time_end = datetime.strptime(
                        f"{date_value} {end_time_value}", "%Y-%m-%d %H:%M"
                    )
                except ValueError:
                    logger.warning(f"Failed to parse end datetime: {date_value} {end_time_value}")

        # Return mapped to output nodes
        return {
            context.outputs[0].node_id: time_start,  # time_start
            context.outputs[1].node_id: time_end     # time_end
        }

    def _build_system_prompt(self) -> str:
        """Build the system prompt for date/time extraction (token-efficient)."""
        today = datetime.now().strftime("%Y-%m-%d")
        return f"""Extract delivery date/time as JSON: {{date, start_time, end_time}}

Today: {today}
Format: date="YYYY-MM-DD", times="HH:MM" 24h.

Rules:
- NEVER return null. Always provide a best guess for date, start_time, and end_time.
- Year missing: pick year making date nearest to today (e.g., 12/1→1/3 = next year, 12/1→11/28 = same year)
- Date missing: use today's date
- Parse formats: 9am, 9:00, 0900, nine am, noon, ranges (9-5)
- "cutoff" means end_time only (start="09:00")
- "at T": start=end=T
- "by/before T": end=T, start="09:00" (if T is time only)
- "by/before D" (date only, no time): start="09:00", end="17:00"
- "after/from T": start=T, end="17:00"
- No time given: start="09:00", end="17:00"

Return only JSON."""
