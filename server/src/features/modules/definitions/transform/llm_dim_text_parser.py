"""
LLM Dim Text Parser Transform Module
Parses free-text dimension strings into structured dim objects using an LLM.
Handles formats like "48x40x40 (2), 48x40x46 (4)" and many other variations.
"""
import logging
import os
import json
from typing import Any

from pydantic import BaseModel, Field

from shared.types import ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.registry import register
from features.modules.base import BaseModule
from shared.database.access_connection import AccessConnectionManager

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a logistics data extraction assistant. You will receive a text string \
containing dimension information from a shipping document.

Parse it into a JSON object with a "dims" array. Each entry must have exactly \
these fields:
{
  "length": <number>,
  "width": <number>,
  "height": <number>,
  "qty": <integer>,
  "weight": <number>
}

Rules:
- Return {"dims": [...]}.
- Dimensions are LxWxH in inches unless otherwise stated.
- Map the three dimension values to length, width, height in the order given.
- qty is the piece count for that dimension set. Default to 1 if not specified.
- If per-line weights are provided, include them. If NO weights are present \
in the text, set weight to 0 for every entry.
- Return an empty array [] only if the input is empty or nonsensical.
- Round all numeric values to 3 decimal places.\
"""


class LlmDimTextParserConfig(BaseModel):
    """Configuration for LLM Dim Text Parser"""
    description: str = Field(
        default="",
        description="Optional hint about the dim format (e.g., 'dims are in cm, convert to inches')"
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
class LlmDimTextParser(BaseModule):
    """
    LLM-powered dimension text parser.

    Takes a single free-text string containing dimension info and uses an LLM
    to parse it into a structured list of dim objects.
    """

    identifier = "llm_dim_text_parser"
    version = "1.0.0"
    title = "LLM Dim Text Parser"
    description = "Parse free-text dimension strings into structured dim objects using an LLM"
    category = "LLM"
    kind = "transform"
    color = "#F97316"

    ConfigModel = LlmDimTextParserConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="text",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1,
                        ),
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="dims",
                            typing=NodeTypeRule(allowed_types=["list[dim]"]),
                            min_count=1,
                            max_count=1,
                        )
                    ]
                ),
            )
        )

    def run(
        self,
        inputs: dict[str, Any],
        cfg: LlmDimTextParserConfig,
        context: Any,
        access_conn_manager: AccessConnectionManager | None = None,
    ) -> dict[str, Any]:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai library is required for LLM dim text parsing. "
                "Install it with: pip install openai"
            )

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        # Get input text
        text = ""
        for pin in context.inputs:
            value = inputs.get(pin.node_id)
            if value is not None:
                text = str(value)

        # Build system prompt with optional description hint
        system = SYSTEM_PROMPT
        if cfg.description.strip():
            system += f"\n\nAdditional context: {cfg.description}"

        logger.info(
            f"LLM Dim Text Parser: model={cfg.model}, text={text!r}"
        )

        client = OpenAI(api_key=api_key)

        try:
            response = client.chat.completions.create(
                model=cfg.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": text},
                ],
                temperature=cfg.temperature,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if content is None:
                raise ValueError("Empty response from LLM")

            parsed = json.loads(content)
            raw_dims = parsed.get("dims", [])
            logger.info(f"LLM Dim Text Parser result: {raw_dims}")

        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {e}")
        except Exception as e:
            logger.error(f"LLM dim text parsing failed: {e}")
            raise ValueError(f"LLM dim text parsing failed: {e}")

        # Validate and normalize
        dim_list = []
        for raw in raw_dims:
            if not isinstance(raw, dict):
                logger.warning(f"Skipping non-dict dim entry: {raw}")
                continue
            dim_list.append({
                "length": round(float(raw.get("length", 0)), 3),
                "width": round(float(raw.get("width", 0)), 3),
                "height": round(float(raw.get("height", 0)), 3),
                "qty": int(raw.get("qty", 1)),
                "weight": round(float(raw.get("weight", 0)), 3),
            })

        output_node_id = context.outputs[0].node_id
        return {output_node_id: dim_list}
