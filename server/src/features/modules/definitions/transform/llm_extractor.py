"""
LLM Extractor Transform Module
General-purpose LLM module with variable text inputs and variable typed outputs.
Uses a user-defined prompt template with {input_label} placeholders.
Output schema is auto-generated from the output pin definitions.
"""
import logging
import os
import json
import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from shared.types import ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.registry import register
from features.modules.base import BaseModule
from shared.database.access_connection import AccessConnectionManager

logger = logging.getLogger(__name__)


# Type descriptions used in the LLM schema prompt
TYPE_SCHEMA_HINTS = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean (true/false)",
    "datetime": 'ISO 8601 datetime string (e.g., "2026-04-05T23:00:00")',
}


class LlmExtractorConfig(BaseModel):
    """Configuration for LLM Extractor"""
    prompt_template: str = Field(
        description=(
            "Prompt with {input_pin_label} placeholders. "
            "Output structure is auto-generated from output pins."
        )
    )
    model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model to use"
    )
    temperature: float = Field(
        default=0.0,
        description="LLM temperature (0 = deterministic)"
    )


@register
class LlmExtractor(BaseModule):
    """
    General-purpose LLM extraction module.

    Takes variable text inputs, substitutes them into a user-defined prompt,
    and uses the LLM to extract structured data matching the output pin schema.
    """

    identifier = "llm_extractor"
    version = "1.0.0"
    title = "LLM Extractor"
    description = "Extract structured data from text using an LLM with a custom prompt"
    category = "LLM"
    kind = "transform"
    color = "#F97316"  # Orange (matches existing LLM module)

    ConfigModel = LlmExtractorConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="input",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=None,
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="output",
                            typing=NodeTypeRule(
                                allowed_types=["str", "int", "float", "bool", "datetime"]
                            ),
                            min_count=1,
                            max_count=None,
                        )
                    ]
                ),
            )
        )

    @classmethod
    def validate_config(
        cls,
        cfg: BaseModel,
        inputs: list[Any],
        outputs: list[Any],
        services: Any = None,
    ) -> list[str]:
        """Validate that prompt template placeholders match input pin labels."""
        errors = []
        prompt = cfg.prompt_template

        # Find all {placeholder} references in the prompt
        placeholders = set(re.findall(r"\{(\w+)\}", prompt))

        # Build set of available input labels
        input_labels = set()
        for pin in inputs:
            label = pin.get("name") if isinstance(pin, dict) else getattr(pin, "name", None)
            if label:
                input_labels.add(label)

        # Check for placeholders that don't match any input
        unknown = placeholders - input_labels
        if unknown:
            errors.append(
                f"Prompt references unknown inputs: {', '.join(sorted(unknown))}. "
                f"Available inputs: {', '.join(sorted(input_labels))}"
            )

        return errors

    def run(
        self,
        inputs: dict[str, Any],
        cfg: LlmExtractorConfig,
        context: Any,
        access_conn_manager: AccessConnectionManager | None = None,
    ) -> dict[str, Any]:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai library is required for LLM extraction. "
                "Install it with: pip install openai"
            )

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        # Build input label -> value mapping
        input_values = {}
        for pin in context.inputs:
            value = inputs.get(pin.node_id)
            input_values[pin.name] = value if value is not None else ""

        # Substitute placeholders in the prompt template
        try:
            user_prompt = cfg.prompt_template.format(**input_values)
        except KeyError as e:
            raise ValueError(f"Prompt references unknown input: {e}")

        # Build output schema from output pins
        output_schema = {}
        for pin in context.outputs:
            type_hint = TYPE_SCHEMA_HINTS.get(pin.type, "string")
            output_schema[pin.name] = type_hint

        # Build system prompt with output schema
        schema_lines = [f'  "{name}": {hint}' for name, hint in output_schema.items()]
        schema_str = "{\n" + ",\n".join(schema_lines) + "\n}"

        system_prompt = (
            "You are a data extraction assistant. "
            "Extract the requested information and return ONLY valid JSON "
            f"matching this exact schema:\n\n{schema_str}\n\n"
            "Rules:\n"
            "- Return ONLY the JSON object, no other text.\n"
            "- Use null if a value cannot be determined.\n"
            "- For datetime fields, use ISO 8601 format.\n"
            "- For boolean fields, use true/false."
        )

        logger.info(
            f"LLM Extractor: model={cfg.model}, "
            f"inputs={list(input_values.keys())}, "
            f"outputs={list(output_schema.keys())}"
        )
        logger.debug(f"LLM Extractor prompt: {user_prompt}")

        # Call OpenAI API
        client = OpenAI(api_key=api_key)

        try:
            response = client.chat.completions.create(
                model=cfg.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=cfg.temperature,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if content is None:
                raise ValueError("Empty response from LLM")

            extracted = json.loads(content)
            logger.info(f"LLM Extractor result: {extracted}")

        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {e}")
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            raise ValueError(f"LLM extraction failed: {e}")

        # Map extracted values to output pins with type coercion
        result = {}
        for pin in context.outputs:
            raw_value = extracted.get(pin.name)
            result[pin.node_id] = self._coerce_value(raw_value, pin.type, pin.name)

        return result

    @staticmethod
    def _coerce_value(value: Any, target_type: str, field_name: str) -> Any:
        """Coerce an LLM-extracted value to the target pin type."""
        if value is None:
            return None

        try:
            if target_type == "str":
                return str(value)

            if target_type == "int":
                return int(float(value))

            if target_type == "float":
                return float(value)

            if target_type == "bool":
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes")
                return bool(value)

            if target_type == "datetime":
                if isinstance(value, datetime):
                    return value
                if isinstance(value, str):
                    # Try ISO 8601 first, then common formats
                    for fmt in (
                        "%Y-%m-%dT%H:%M:%S",
                        "%Y-%m-%dT%H:%M",
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%d %H:%M",
                        "%Y-%m-%d",
                    ):
                        try:
                            return datetime.strptime(value, fmt)
                        except ValueError:
                            continue
                    raise ValueError(f"Cannot parse datetime: {value}")

            # Fallback: return as-is
            return value

        except (ValueError, TypeError) as e:
            logger.warning(
                f"Failed to coerce '{field_name}' value {value!r} to {target_type}: {e}"
            )
            return None
