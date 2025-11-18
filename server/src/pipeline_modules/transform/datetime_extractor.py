"""
DateTime Extractor Transform Module
Uses OpenAI API to extract date and time information from varied text formats
"""
import logging
import os
import json
from typing import Dict, Any
from pydantic import BaseModel

from shared.types import TransformModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register

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

    Always extracts:
    - date: The date in ISO 8601 format (YYYY-MM-DD)
    - start_time: Start time in ISO 8601 format (HH:MM:SS)
    - end_time: End time in ISO 8601 format (HH:MM:SS)

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
    description = "Extract date and time from varied text formats using AI"
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
                            label="date",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            label="start_time",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            label="end_time",
                            typing=NodeTypeRule(allowed_types=["str"]),
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
            Dictionary with date, start_time, and end_time outputs
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
                context.outputs[0].node_id: None,  # date
                context.outputs[1].node_id: None,  # start_time
                context.outputs[2].node_id: None   # end_time
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
            extracted_data = json.loads(response.choices[0].message.content)

            logger.info(f"Extracted date/time: {extracted_data}")

        except Exception as e:
            logger.error(f"DateTime extraction failed: {e}")
            raise ValueError(f"DateTime extraction failed: {e}")

        # Extract values
        date_value = extracted_data.get("date")
        start_time_value = extracted_data.get("start_time")
        end_time_value = extracted_data.get("end_time")

        # Return mapped to output nodes
        return {
            context.outputs[0].node_id: date_value,       # date
            context.outputs[1].node_id: start_time_value, # start_time
            context.outputs[2].node_id: end_time_value    # end_time
        }

    def _build_system_prompt(self) -> str:
        """Build the system prompt for date/time extraction (token-efficient)."""
        return """Extract delivery date/time as JSON: {date, start_time, end_time}

Format: date="YYYY-MM-DD", times="HH:MM" 24h. Use null if unknown.

Rules:
- Infer year for partial dates (use next year if date passed)
- Parse formats: 9am, 9:00, 0900, nine am, noon, ranges (9-5)
- "at T": start=end=T
- "by/before T": end=T, start="09:00"
- "after/from T": start=T, end="16:00"
- No time given: start="09:00", end="16:00"

Return only JSON."""
