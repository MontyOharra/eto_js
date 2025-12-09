"""
Address Parser Transform Module
Parses a US address string into components (street, city, state, zip)
"""
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel

from shared.types import TransformModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register

logger = logging.getLogger(__name__)


class AddressParserConfig(BaseModel):
    """Configuration for Address Parser"""
    # No configuration needed
    pass


@register
class AddressParser(TransformModule):
    """
    Address Parser transform module
    Parses a US address string into components using the usaddress library
    """

    # Class metadata
    id = "address_parser"
    version = "1.0.0"
    title = "Address Parser"
    description = "Parse US address string into components (street, city, state, zip)"
    category = "Text"
    color = "#0EA5E9"  # Sky blue

    # Configuration model
    ConfigModel = AddressParserConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="address_string",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="address_line_1",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            label="address_line_2",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            label="city",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            label="state",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            label="zip_code",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            label="parse_success",
                            typing=NodeTypeRule(allowed_types=["bool"]),
                            min_count=1,
                            max_count=1
                        )
                    ]
                )
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: AddressParserConfig, context: Any, services: Any = None) -> Dict[str, Any]:
        """
        Execute address parsing

        Args:
            inputs: Dictionary with address_string input
            cfg: Validated configuration
            context: Execution context with ordered inputs/outputs
            services: Not used for this module

        Returns:
            Dictionary with parsed address components
        """
        # Import usaddress here to avoid import errors if not installed
        try:
            import usaddress
        except ImportError:
            raise ImportError(
                "usaddress library is required for address parsing. "
                "Install it with: pip install usaddress"
            )

        # Get input
        input_node_id = list(inputs.keys())[0]
        address_string = inputs[input_node_id]

        # Get output node IDs
        addr_line_1_output = context.outputs[0].node_id
        addr_line_2_output = context.outputs[1].node_id
        city_output = context.outputs[2].node_id
        state_output = context.outputs[3].node_id
        zip_output = context.outputs[4].node_id
        success_output = context.outputs[5].node_id

        # Handle None/empty input
        if not address_string:
            logger.warning("Empty address string provided")
            return {
                addr_line_1_output: "",
                addr_line_2_output: "",
                city_output: "",
                state_output: "",
                zip_output: "",
                success_output: False
            }

        logger.info(f"Parsing address: '{address_string}'")

        # Parse address using usaddress
        try:
            parsed, address_type = usaddress.tag(address_string)
        except usaddress.RepeatedLabelError as e:  # type: ignore[attr-defined]
            # This happens when multiple instances of the same label are found
            logger.error(f"Address parsing failed - ambiguous address: {e}")
            return {
                addr_line_1_output: "",
                addr_line_2_output: "",
                city_output: "",
                state_output: "",
                zip_output: "",
                success_output: False
            }

        # Check if address was successfully parsed
        if address_type == "Ambiguous":
            logger.warning(f"Address type is ambiguous: '{address_string}'")
            # Still try to extract what we can

        # Extract street address components for Line 1
        line_1_parts = []

        # Address number (e.g., "1234")
        if 'AddressNumber' in parsed:
            line_1_parts.append(parsed['AddressNumber'])

        # Street name pre-directional (e.g., "N" in "N Main St")
        if 'StreetNamePreDirectional' in parsed:
            line_1_parts.append(parsed['StreetNamePreDirectional'])

        # Street name (e.g., "Main")
        if 'StreetName' in parsed:
            line_1_parts.append(parsed['StreetName'])

        # Street name post-type (e.g., "St", "Ave", "Blvd")
        if 'StreetNamePostType' in parsed:
            line_1_parts.append(parsed['StreetNamePostType'])

        # Street name post-directional (e.g., "N" in "Main St N")
        if 'StreetNamePostDirectional' in parsed:
            line_1_parts.append(parsed['StreetNamePostDirectional'])

        address_line_1 = " ".join(line_1_parts)

        # Extract address line 2 components (suite, apt, unit, etc.)
        line_2_parts = []

        # Occupancy/Suite info (e.g., "Suite 100")
        if 'OccupancyType' in parsed and 'OccupancyIdentifier' in parsed:
            line_2_parts.append(f"{parsed['OccupancyType']} {parsed['OccupancyIdentifier']}")
        elif 'OccupancyType' in parsed:
            line_2_parts.append(parsed['OccupancyType'])

        # Subaddress info (alternative to occupancy)
        if 'SubaddressType' in parsed and 'SubaddressIdentifier' in parsed:
            line_2_parts.append(f"{parsed['SubaddressType']} {parsed['SubaddressIdentifier']}")
        elif 'SubaddressType' in parsed:
            line_2_parts.append(parsed['SubaddressType'])

        address_line_2 = " ".join(line_2_parts)

        # Extract city
        city = parsed.get('PlaceName', '')

        # Extract state
        state = parsed.get('StateName', '')

        # Extract ZIP code
        zip_code = parsed.get('ZipCode', '')

        # If ZIP+4, combine them
        if 'ZipPlus4' in parsed:
            zip_code = f"{zip_code}-{parsed['ZipPlus4']}"

        return {
            addr_line_1_output: address_line_1,
            addr_line_2_output: address_line_2,
            city_output: city,
            state_output: state,
            zip_output: zip_code
        }
