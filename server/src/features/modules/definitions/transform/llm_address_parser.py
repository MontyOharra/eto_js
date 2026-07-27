"""
LLM Address Parser Transform Module
Extracts a company name and a clean mailing address from a free-text blob,
discarding extraneous content such as order numbers, reference codes, and
contact details.

Customers routinely put non-address text inside the address block of a form
(e.g. "ACME CORP 1234 MAIN ST ORDER #100000 ATTN JOHN 214-555-1212 DALLAS TX
75201"). Rule-based parsing absorbs that text into the address, which then
creates near-duplicate address records downstream. This module strips it at
the pipeline stage, before the value reaches an output channel.
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
You are an address extraction tool for a freight brokerage. You will receive a \
block of text taken from a shipping document. It contains a company name and a \
US mailing address, usually mixed with other content.

Extract ONLY the company/location name and the physical mailing address.

Discard everything else, including:
- order numbers, job numbers, PO numbers, reference numbers, invoice numbers
- HAWB / MAWB / AWB / tracking / pro / BOL / seal numbers
- contact details: phone, fax, email, "ATTN:" lines, contact person names
- delivery instructions, appointment times, hours of operation, notes
- any leading label text such as "SHIP TO:", "CONSIGNEE:", "PICKUP AT:"

Rules:
- Format the address as: Street, City, State ZIP
- Include a suite / unit / apartment / dock / building number ONLY when it is \
genuinely part of the address, placed after the street: "1234 Main St Ste 400, Dallas, TX 75201"
- A number is NOT a suite just because it follows the street or a "#" - order \
and reference numbers are never part of the address
- The company name is the business or location name, not a person's name
- Do NOT guess or fabricate any component. If a value is not present in the \
text, return null for it
- Return null for the address unless you can identify a complete US address \
(street, city, state, ZIP)

Return JSON: {"company_name": "name or null", "address": "Street, City, State ZIP or null"}\
"""

# Reasoning-family models reject an explicit temperature (only the default is
# allowed), so it is omitted for them.
_TEMPERATURE_UNSUPPORTED_PREFIXES = ("gpt-5", "o1", "o3", "o4")


def _supports_temperature(model: str) -> bool:
    """True if the model accepts an explicit temperature parameter."""
    return not model.lower().startswith(_TEMPERATURE_UNSUPPORTED_PREFIXES)


def _normalize(value: Any) -> str:
    """Uppercase and collapse whitespace, matching HTC storage conventions."""
    if value is None:
        return ""
    return " ".join(str(value).split()).upper()


class LlmAddressParserConfig(BaseModel):
    """Configuration for LLM Address Parser"""
    additional_instructions: str = Field(
        default="",
        description=(
            "Extra extraction instructions appended to the built-in rules "
            "(e.g., 'the warehouse name appears below the street address')"
        )
    )
    model: str = Field(
        default="gpt-5-mini",
        description="OpenAI model to use"
    )
    temperature: float = Field(
        default=0.0,
        description="LLM temperature (0 = deterministic). Ignored by reasoning models such as gpt-5."
    )


@register
class LlmAddressParser(BaseModule):
    """
    LLM-powered address extractor.

    Takes a single free-text string and uses an LLM to pull out just the
    company name and mailing address, filtering out order numbers, reference
    codes, contact details, and other non-address content.
    """

    identifier = "llm_address_parser"
    version = "1.0.0"
    title = "LLM Address Parser"
    description = "Extract a company name and clean address from text, filtering out order numbers and contact info"
    category = "LLM"
    kind = "transform"
    color = "#F97316"  # Orange (matches other LLM modules)

    ConfigModel = LlmAddressParserConfig

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
                            label="company_name",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1,
                        ),
                        NodeGroup(
                            label="address",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1,
                        ),
                        NodeGroup(
                            label="parse_success",
                            typing=NodeTypeRule(allowed_types=["bool"]),
                            min_count=1,
                            max_count=1,
                        ),
                    ]
                ),
            )
        )

    def run(
        self,
        inputs: dict[str, Any],
        cfg: LlmAddressParserConfig,
        context: Any,
        access_conn_manager: AccessConnectionManager | None = None,
    ) -> dict[str, Any]:
        company_output = context.outputs[0].node_id
        address_output = context.outputs[1].node_id
        success_output = context.outputs[2].node_id

        # Get input text
        text = ""
        for pin in context.inputs:
            value = inputs.get(pin.node_id)
            if value is not None:
                text = str(value)

        if not text.strip():
            logger.warning("LLM Address Parser: empty input text")
            return {
                company_output: "",
                address_output: "",
                success_output: False,
            }

        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai library is required for LLM address parsing. "
                "Install it with: pip install openai"
            )

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        # Build system prompt with optional extra instructions
        system = SYSTEM_PROMPT
        if cfg.additional_instructions.strip():
            system += f"\n\nAdditional instructions: {cfg.additional_instructions}"

        logger.info(f"LLM Address Parser: model={cfg.model}, text={text!r}")

        client = OpenAI(api_key=api_key)

        request_kwargs: dict[str, Any] = {
            "model": cfg.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            "response_format": {"type": "json_object"},
        }
        if _supports_temperature(cfg.model):
            request_kwargs["temperature"] = cfg.temperature

        try:
            try:
                response = client.chat.completions.create(**request_kwargs)
            except Exception as e:
                # Some models reject an explicit temperature - retry without it
                if "temperature" in request_kwargs and "temperature" in str(e).lower():
                    logger.info(
                        f"Model {cfg.model} rejected the temperature parameter, retrying without it"
                    )
                    request_kwargs.pop("temperature")
                    response = client.chat.completions.create(**request_kwargs)
                else:
                    raise

            content = response.choices[0].message.content
            if content is None:
                raise ValueError("Empty response from LLM")

            parsed = json.loads(content)

        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {e}")
        except Exception as e:
            logger.error(f"LLM address parsing failed: {e}")
            raise ValueError(f"LLM address parsing failed: {e}")

        company_name = _normalize(parsed.get("company_name"))
        address = _normalize(parsed.get("address"))

        if not address:
            logger.warning(f"LLM Address Parser: no address found in {text!r}")

        logger.info(
            f"LLM Address Parser result: company_name={company_name!r}, address={address!r}"
        )

        return {
            company_output: company_name,
            address_output: address,
            success_output: bool(address),
        }
