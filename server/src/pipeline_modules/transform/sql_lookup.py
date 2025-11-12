"""
SQL Lookup Transform Module
Executes a SQL SELECT query against configured database and returns results
"""
import logging
import re
from typing import Dict, Any, List, Literal, Set
from pydantic import BaseModel, Field
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Token
from sqlparse.tokens import Keyword, DML

from shared.types import TransformModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register

logger = logging.getLogger(__name__)


def _get_column_name(identifier: Identifier) -> str:
    """
    Extract column name or alias from an Identifier token.

    Args:
        identifier: sqlparse Identifier object

    Returns:
        Column name (alias if present, otherwise column name)
    """
    # If there's an alias, use it
    if identifier.has_alias():
        return identifier.get_alias()

    # Otherwise use the real name
    return identifier.get_real_name()


class SqlLookupConfig(BaseModel):
    """Configuration for SQL lookup"""
    sql_template: str = Field(
        description="SQL SELECT query with {input_name} placeholders for inputs and column names/aliases for outputs",
        example="SELECT order_id, customer_name FROM orders WHERE hawb = {hawb_input}"
    )
    database: str = Field(
        default="htc_db",
        description="Database connection to use from available connections"
    )
    on_multiple_rows: Literal["error", "first", "last"] = Field(
        default="error",
        description="How to handle multiple rows"
    )
    on_no_rows: Literal["error", "null"] = Field(
        default="error",
        description="How to handle no rows"
    )


@register
class SqlLookup(TransformModule):
    """
    SQL Lookup transform module

    Executes a SQL SELECT query against a configured database connection.

    Input pins are matched to {placeholder} syntax in the SQL template.
    Output pins are matched to column names or aliases from the SELECT clause.

    Example:
        SQL: "SELECT order_id, customer_name AS cust FROM orders WHERE hawb = {hawb_input}"

        Required pins:
        - Input: hawb_input
        - Outputs: order_id, cust

    The module uses parameterized queries for SQL injection safety.
    """

    # Class metadata
    id = "sql_lookup"
    version = "1.0.0"
    title = "SQL Lookup"
    description = "Execute SQL SELECT query and return single row result"
    category = "Database"
    color = "#8B5CF6"  # Purple

    # Configuration model
    ConfigModel = SqlLookupConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="param",
                            min_count=1,
                            max_count=20,
                            typing=NodeTypeRule(allowed_types=["str", "int", "float", "bool"])
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="field",
                            min_count=1,
                            max_count=20,
                            typing=NodeTypeRule(allowed_types=["str", "int", "float", "bool", "datetime"])
                        )
                    ]
                )
            )
        )

    @classmethod
    def config_schema(cls) -> Dict[str, Any]:
        """
        Generate config schema with dynamic database connection enum.

        Injects available database connections from ServiceContainer
        into the 'database' field enum so the frontend renders a dropdown.
        """
        # Get base schema from Pydantic model
        schema = cls.ConfigModel.model_json_schema()

        # Try to inject available database connections
        try:
            from shared.services.service_container import ServiceContainer

            if ServiceContainer.is_initialized():
                # Get available connection names from ServiceContainer
                available_connections = list(ServiceContainer._connection_managers.keys())

                if available_connections:
                    # Inject as enum for dropdown rendering
                    schema['properties']['database']['enum'] = available_connections
                    logger.debug(f"Injected database connections into schema: {available_connections}")

                    # Update default if current default not in available connections
                    current_default = schema['properties']['database'].get('default')
                    if current_default and current_default not in available_connections:
                        # Use first available connection as fallback
                        schema['properties']['database']['default'] = available_connections[0]
                        logger.debug(f"Updated default database to: {available_connections[0]}")
                else:
                    logger.warning("No database connections available in ServiceContainer")
            else:
                logger.warning("ServiceContainer not initialized yet - cannot inject database connections")

        except Exception as e:
            logger.warning(f"Could not inject database connections into schema: {e}")
            # Schema will still work, just won't have enum (will be text input instead)

        return schema

    @staticmethod
    def _extract_placeholders(sql_template: str) -> Set[str]:
        """
        Extract {placeholder} names from SQL template.

        Args:
            sql_template: SQL query with {placeholder} syntax

        Returns:
            Set of placeholder names
        """
        return set(re.findall(r'\{(\w+)\}', sql_template))

    @staticmethod
    def _extract_select_columns(sql_template: str) -> List[str]:
        """
        Parse SELECT clause to extract column names and aliases.

        Args:
            sql_template: SQL SELECT query

        Returns:
            List of column names/aliases

        Raises:
            ValueError: If SELECT * is used or parsing fails
        """
        # Parse SQL
        parsed = sqlparse.parse(sql_template)
        if not parsed:
            raise ValueError("Failed to parse SQL query")

        statement = parsed[0]

        # Find SELECT keyword and get columns
        columns = []
        in_select = False

        for token in statement.tokens:
            # Skip whitespace and comments
            if token.is_whitespace or token.ttype in (sqlparse.tokens.Comment.Single, sqlparse.tokens.Comment.Multiline):
                continue

            # Check for SELECT keyword
            if token.ttype is DML and token.value.upper() == 'SELECT':
                in_select = True
                continue

            # If we're past SELECT, look for column list
            if in_select:
                if token.ttype is Keyword:
                    # Hit FROM or another keyword, done with columns
                    break

                if isinstance(token, IdentifierList):
                    # Multiple columns
                    for identifier in token.get_identifiers():
                        columns.append(_get_column_name(identifier))
                elif isinstance(token, Identifier):
                    # Single column
                    columns.append(_get_column_name(token))
                elif token.ttype not in (sqlparse.tokens.Whitespace, sqlparse.tokens.Punctuation):
                    # Single token column (no alias)
                    col_name = token.value.strip()
                    if col_name == '*':
                        raise ValueError("SELECT * is not supported. Please explicitly list column names.")
                    columns.append(col_name)

        if not columns:
            raise ValueError("No columns found in SELECT clause")

        return columns

    @staticmethod
    def _build_sql_statement(sql_template: str, input_values: Dict[str, Any]) -> str:
        """
        Build final SQL statement by replacing {placeholders} with actual values.

        Args:
            sql_template: SQL query with {placeholder} syntax
            input_values: Dict mapping placeholder names to their values

        Returns:
            SQL statement with values substituted
        """
        sql = sql_template

        for placeholder, value in input_values.items():
            # Format value based on type for SQL
            if isinstance(value, str):
                # Escape single quotes and wrap in quotes
                formatted_value = f"'{value.replace("'", "''")}'"
            elif value is None:
                formatted_value = "NULL"
            elif isinstance(value, bool):
                formatted_value = "1" if value else "0"
            else:
                # int, float, etc.
                formatted_value = str(value)

            # Replace placeholder
            sql = sql.replace(f"{{{placeholder}}}", formatted_value)

        return sql

    @staticmethod
    def _get_default_value_for_type(type_str: str) -> Any:
        """
        Get default dummy value for a given type.

        Args:
            type_str: Type name ("str", "int", "float", "bool", "datetime")

        Returns:
            Default value for that type
        """
        defaults = {
            "str": "",
            "int": 0,
            "float": 0.0,
            "bool": False,
            "datetime": None  # Could use datetime.now() but None is simpler
        }
        return defaults.get(type_str, None)

    def run(self, inputs: Dict[str, Any], cfg: SqlLookupConfig, context: Any, services: Any = None) -> Dict[str, Any]:
        """
        Execute SQL lookup query.

        Currently builds and prints the SQL statement, returns dummy values.
        Actual database execution will be implemented after custom Access connector is built.

        Args:
            inputs: Dictionary with input values keyed by node_id
            cfg: Configuration (sql_template, database, on_multiple_rows, on_no_rows)
            context: Execution context with I/O metadata
            services: Service container (not used yet)

        Returns:
            Dictionary with dummy output values keyed by node_id
        """
        logger.info(f"[SQL LOOKUP] Starting execution with database: {cfg.database}")

        # Step 1: Extract placeholders from SQL template
        placeholders = self._extract_placeholders(cfg.sql_template)
        logger.info(f"[SQL LOOKUP] Found {len(placeholders)} placeholders: {placeholders}")

        # Step 2: Parse SELECT clause to get expected output columns
        try:
            expected_columns = self._extract_select_columns(cfg.sql_template)
            logger.info(f"[SQL LOOKUP] Found {len(expected_columns)} output columns: {expected_columns}")
        except ValueError as e:
            raise RuntimeError(f"Failed to parse SELECT clause: {e}")

        # Step 3: Build name-to-pin mappings
        logger.info(f"[SQL LOOKUP DEBUG] context.inputs raw: {context.inputs}")
        for pin in context.inputs:
            logger.info(f"[SQL LOOKUP DEBUG] Input pin: node_id={pin.node_id}, name={pin.name}, type={pin.type}, group_index={pin.group_index}, position_index={pin.position_index}")

        input_name_to_pin = {pin.name: pin for pin in context.inputs}
        output_name_to_pin = {pin.name: pin for pin in context.outputs}

        logger.info(f"[SQL LOOKUP] Input pins: {list(input_name_to_pin.keys())}")
        logger.info(f"[SQL LOOKUP] Output pins: {list(output_name_to_pin.keys())}")

        # Step 4: Validate all placeholders have matching input pins
        missing_inputs = placeholders - set(input_name_to_pin.keys())
        if missing_inputs:
            raise RuntimeError(
                f"SQL template references placeholders that don't exist as input pins: {missing_inputs}. "
                f"Available input pins: {list(input_name_to_pin.keys())}"
            )

        # Step 5: Validate all output columns have matching output pins
        missing_outputs = set(expected_columns) - set(output_name_to_pin.keys())
        if missing_outputs:
            raise RuntimeError(
                f"SELECT clause references columns that don't exist as output pins: {missing_outputs}. "
                f"Available output pins: {list(output_name_to_pin.keys())}"
            )

        # Step 6: Build input values dict (placeholder name -> actual value)
        input_values = {}
        for placeholder in placeholders:
            pin = input_name_to_pin[placeholder]
            value = inputs[pin.node_id]
            input_values[placeholder] = value
            logger.info(f"[SQL LOOKUP] Input '{placeholder}' = {value} (type: {type(value).__name__})")

        # Step 7: Build the final SQL statement
        final_sql = self._build_sql_statement(cfg.sql_template, input_values)

        # Step 8: Print to console
        logger.info("=" * 80)
        logger.info("[SQL LOOKUP] GENERATED SQL STATEMENT:")
        logger.info(final_sql)
        logger.info("=" * 80)
        print("\n" + "=" * 80)
        print("[SQL LOOKUP] GENERATED SQL STATEMENT:")
        print(final_sql)
        print("=" * 80 + "\n")

        # Step 9: Return dummy values for outputs based on their types
        outputs = {}
        for column_name in expected_columns:
            pin = output_name_to_pin[column_name]
            dummy_value = self._get_default_value_for_type(pin.type)
            outputs[pin.node_id] = dummy_value
            logger.info(f"[SQL LOOKUP] Output '{column_name}' = {dummy_value} (type: {pin.type})")

        logger.info(f"[SQL LOOKUP] Execution complete (dummy mode)")
        return outputs
