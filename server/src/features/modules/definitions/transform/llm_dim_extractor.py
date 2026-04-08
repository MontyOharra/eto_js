"""
LLM Dim Extractor Transform Module
Parses free-text pieces, dimensions, and weight strings into structured dim objects
using an LLM to handle the wide variety of formats found in logistics documents.
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
You are a logistics data extraction assistant. You will receive three text fields \
from a shipping document: pieces/quantity text, dimensions text, and weight text.

Parse them into a JSON array of dimension objects. Each object must have exactly \
these fields:
{
  "length": <number>,
  "width": <number>,
  "height": <number>,
  "qty": <integer>,
  "weight": <number>
}

Rules:
- Return {"dims": [...]}, where dims is the array of dimension objects.
- Dimensions are in inches, weight is in pounds (lbs) unless otherwise specified.
- If dimensions are given as LxWxH, map them to length, width, height in that order.
- If multiple dimension lines exist, create one object per unique dimension set.
- Distribute weight proportionally across dimension sets by piece count if only a \
total weight is given. Round weight to 3 decimal places.
- qty is the number of pieces for that dimension set.
- If a value truly cannot be determined, use 0.
- Return an empty array [] only if ALL inputs are empty or nonsensical.\
"""


class LlmDimExtractorConfig(BaseModel):
    """Configuration for LLM Dim Extractor"""
    model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model to use"
    )
    temperature: float = Field(
        default=0.0,
        description="LLM temperature (0 = deterministic)"
    )


@register
class LlmDimExtractor(BaseModule):
    """
    LLM-powered dimension parser.

    Takes free-text pieces, dimensions, and weight strings and uses an LLM
    to parse them into a structured list of dim objects.
    """

    identifier = "llm_dim_extractor"
    version = "1.0.0"
    title = "LLM Dim Extractor"
    description = "Parse free-text pieces, dimensions, and weight into structured dim objects using an LLM"
    category = "LLM"
    kind = "transform"
    color = "#F97316"

    ConfigModel = LlmDimExtractorConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="pcs_text",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1,
                        ),
                        NodeGroup(
                            label="dims_text",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1,
                        ),
                        NodeGroup(
                            label="weight_text",
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
        cfg: LlmDimExtractorConfig,
        context: Any,
        access_conn_manager: AccessConnectionManager | None = None,
    ) -> dict[str, Any]:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai library is required for LLM dim extraction. "
                "Install it with: pip install openai"
            )

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        # Read inputs by group index
        pcs_text = ""
        dims_text = ""
        weight_text = ""
        for pin in context.inputs:
            value = inputs.get(pin.node_id)
            text = str(value) if value is not None else ""
            if pin.group_index == 0:
                pcs_text = text
            elif pin.group_index == 1:
                dims_text = text
            elif pin.group_index == 2:
                weight_text = text

        user_prompt = (
            f"Pieces: {pcs_text}\n"
            f"Dimensions: {dims_text}\n"
            f"Weight: {weight_text}"
        )

        logger.info(
            f"LLM Dim Extractor: model={cfg.model}, "
            f"pcs={pcs_text!r}, dims={dims_text!r}, weight={weight_text!r}"
        )

        client = OpenAI(api_key=api_key)

        try:
            response = client.chat.completions.create(
                model=cfg.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=cfg.temperature,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if content is None:
                raise ValueError("Empty response from LLM")

            parsed = json.loads(content)
            raw_dims = parsed.get("dims", [])
            logger.info(f"LLM Dim Extractor result: {raw_dims}")

        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {e}")
        except Exception as e:
            logger.error(f"LLM dim extraction failed: {e}")
            raise ValueError(f"LLM dim extraction failed: {e}")

        # Validate and normalize each dim object
        dim_list = []
        for raw in raw_dims:
            if not isinstance(raw, dict):
                logger.warning(f"Skipping non-dict dim entry: {raw}")
                continue
            dim_list.append({
                "length": round(float(raw.get("length", 0)), 3),
                "width": round(float(raw.get("width", 0)), 3),
                "height": round(float(raw.get("height", 0)), 3),
                "qty": int(raw.get("qty", 0)),
                "weight": round(float(raw.get("weight", 0)), 3),
            })

        output_node_id = context.outputs[0].node_id
        return {output_node_id: dim_list}
