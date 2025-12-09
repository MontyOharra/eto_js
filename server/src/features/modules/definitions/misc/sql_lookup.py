"""
SQL Lookup Transform Module
Executes a SQL SELECT query against configured database and returns results
"""
import logging
import re
from typing import Dict, Any, List, Literal, Set, Tuple
from pydantic import BaseModel, Field
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Token, Where
from sqlparse.tokens import Keyword, DML

from shared.types import MiscModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
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
        return identifier.get_alias() or str(identifier)

    # Otherwise use the real name
    return identifier.get_real_name() or str(identifier)


class SqlLookupConfig(BaseModel):
    """Configuration for SQL lookup"""
    sql_template: str = Field(
        description="SQL SELECT query with {input_name} placeholders for inputs and column names/aliases for outputs",
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
class SqlLookup(MiscModule):
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
    color = "#EAB308"  # Yellow

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
                # Get available business database connections (excludes 'main' system DB)
                data_db_manager = ServiceContainer._data_database_manager
                if data_db_manager:
                    available_connections = data_db_manager.list_databases()
                else:
                    available_connections = []

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

    @classmethod
    def validate_config(cls, cfg: SqlLookupConfig, inputs: List[Any], outputs: List[Any], services: Any = None) -> List[str]:
        """
        Validate SQL lookup configuration.

        Checks:
        1. SQL template can be parsed
        2. Placeholders in SQL match input pin names
        3. Column names/aliases in SELECT match output pin names
        4. Table referenced in SQL exists in the selected database (if services provided)

        Args:
            cfg: Validated config instance
            inputs: List of input pins for this module instance
            outputs: List of output pins for this module instance
            services: Optional services container for database access

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        logger.info(f"[SQL LOOKUP VALIDATE_CONFIG] Starting validation")
        logger.info(f"[SQL LOOKUP VALIDATE_CONFIG] SQL template: {cfg.sql_template}")
        logger.info(f"[SQL LOOKUP VALIDATE_CONFIG] Database: {cfg.database}")
        logger.info(f"[SQL LOOKUP VALIDATE_CONFIG] Services available: {services is not None}")

        # Extract placeholders from SQL template
        try:
            placeholders = cls._extract_placeholders(cfg.sql_template)
            logger.info(f"[SQL LOOKUP VALIDATE_CONFIG] Extracted placeholders: {placeholders}")
        except Exception as e:
            logger.error(f"[SQL LOOKUP VALIDATE_CONFIG] Failed to extract placeholders: {e}")
            return [f"Failed to extract placeholders from SQL: {e}"]

        # Parse SELECT clause to get expected output columns
        try:
            expected_columns = cls._extract_select_columns(cfg.sql_template)
            logger.info(f"[SQL LOOKUP VALIDATE_CONFIG] Extracted columns: {expected_columns}")
        except ValueError as e:
            logger.error(f"[SQL LOOKUP VALIDATE_CONFIG] Failed to parse SELECT: {e}")
            return [f"Failed to parse SELECT clause: {e}"]
        except Exception as e:
            logger.error(f"[SQL LOOKUP VALIDATE_CONFIG] Unexpected error parsing SQL: {e}")
            return [f"Unexpected error parsing SQL: {e}"]

        # Build name-to-pin mappings
        input_names = {pin.name for pin in inputs if pin.name}  # Filter out empty names
        output_names = {pin.name for pin in outputs if pin.name}  # Filter out empty names

        logger.info(f"[SQL LOOKUP VALIDATE_CONFIG] Input pin names: {input_names}")
        logger.info(f"[SQL LOOKUP VALIDATE_CONFIG] Output pin names: {output_names}")

        # Validate all placeholders have matching input pins
        missing_inputs = placeholders - input_names
        if missing_inputs:
            errors.append(
                f"SQL template references placeholders that don't match input pin names: {sorted(missing_inputs)}. "
                f"Available input pins: {sorted(input_names)}"
            )

        # Validate all output columns have matching output pins
        missing_outputs = set(expected_columns) - output_names
        if missing_outputs:
            errors.append(
                f"SELECT clause references columns that don't match output pin names: {sorted(missing_outputs)}. "
                f"Available output pins: {sorted(output_names)}"
            )

        # Warn if there are extra inputs/outputs not used in SQL (not an error, just informational)
        # This helps users catch typos or unused pins
        unused_inputs = input_names - placeholders
        if unused_inputs:
            # This is just a warning, not an error - could be logged but not block validation
            logger.info(f"[SQL LOOKUP VALIDATION] Unused input pins (not referenced in SQL): {sorted(unused_inputs)}")

        unused_outputs = output_names - set(expected_columns)
        if unused_outputs:
            # This is just a warning, not an error
            logger.info(f"[SQL LOOKUP VALIDATION] Unused output pins (not in SELECT clause): {sorted(unused_outputs)}")

        # Validate table exists in database (if services available)
        if services:
            try:
                logger.info(f"[SQL LOOKUP VALIDATION] Checking if table exists in database '{cfg.database}'")
                table_name = cls._extract_table_name(cfg.sql_template)
                logger.info(f"[SQL LOOKUP VALIDATION] Extracted table name: {table_name}")

                if table_name:
                    db_connection = services.get_connection(cfg.database)
                    if not cls._table_exists(db_connection, table_name):
                        errors.append(f"Table '{table_name}' does not exist in database '{cfg.database}'")
                    else:
                        logger.info(f"[SQL LOOKUP VALIDATION] Table '{table_name}' exists in database '{cfg.database}'")
                else:
                    logger.warning("[SQL LOOKUP VALIDATION] Could not extract table name from SQL template")
            except Exception as e:
                logger.error(f"[SQL LOOKUP VALIDATION] Error checking table existence: {e}")
                errors.append(f"Failed to validate table existence: {e}")
        else:
            logger.info("[SQL LOOKUP VALIDATION] Skipping table validation (services not available)")

        return errors

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

        logger.info(f"[SQL LOOKUP] Parsing SQL: {sql_template}")
        logger.info(f"[SQL LOOKUP] Token breakdown:")

        for token in statement.tokens:
            logger.info(f"  Token: type={token.ttype}, value={repr(token.value)}, class={type(token).__name__}")

            # Skip whitespace and comments
            if token.is_whitespace or token.ttype in (sqlparse.tokens.Comment.Single, sqlparse.tokens.Comment.Multiline):
                continue

            # Check for SELECT keyword
            if token.ttype is DML and token.value.upper() == 'SELECT':
                in_select = True
                logger.info(f"    -> Found SELECT keyword")
                continue

            # If we're past SELECT, look for column list
            if in_select:
                if token.ttype is Keyword:
                    # Hit FROM or another keyword, done with columns
                    logger.info(f"    -> Hit keyword {token.value.upper()}, stopping column extraction")
                    break

                # Check for WHERE clause or other SQL clauses
                if isinstance(token, Where):
                    logger.info(f"    -> Hit WHERE clause, stopping column extraction")
                    break

                if isinstance(token, IdentifierList):
                    # Multiple columns
                    logger.info(f"    -> Found IdentifierList")
                    for identifier in token.get_identifiers():
                        col_name = _get_column_name(identifier)
                        columns.append(col_name)
                        logger.info(f"      -> Extracted column: {col_name}")
                elif isinstance(token, Identifier):
                    # Single column
                    col_name = _get_column_name(token)
                    columns.append(col_name)
                    logger.info(f"    -> Found Identifier, extracted column: {col_name}")
                elif token.ttype not in (sqlparse.tokens.Whitespace, sqlparse.tokens.Punctuation):
                    # Single token column (no alias)
                    col_name = token.value.strip()
                    if col_name == '*':
                        raise ValueError("SELECT * is not supported. Please explicitly list column names.")
                    columns.append(col_name)
                    logger.info(f"    -> Found single token column: {col_name}")

        logger.info(f"[SQL LOOKUP] Extracted columns: {columns}")

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
    def _convert_to_parameterized_sql(sql_template: str) -> Tuple[str, List[str]]:
        """
        Convert SQL template with {placeholder} syntax to parameterized SQL with ? placeholders.

        Args:
            sql_template: SQL with {placeholder} syntax

        Returns:
            Tuple of (parameterized_sql, ordered_placeholder_names)

        Example:
            Input: "SELECT * FROM users WHERE id={user_id} AND status={status}"
            Output: ("SELECT * FROM users WHERE id=? AND status=?", ["user_id", "status"])
        """
        import re

        # Find all {placeholder} occurrences in order
        placeholder_pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
        matches = re.finditer(placeholder_pattern, sql_template)

        # Track placeholders in the order they appear
        ordered_placeholders = []
        for match in matches:
            placeholder_name = match.group(1)
            ordered_placeholders.append(placeholder_name)

        # Replace all {placeholder} with ? in the SQL
        parameterized_sql = re.sub(placeholder_pattern, '?', sql_template)

        return parameterized_sql, ordered_placeholders

    @staticmethod
    def _convert_to_type(value: Any, target_type: str) -> Any:
        """
        Convert database value to target output type.

        Args:
            value: Value from database (could be None)
            target_type: Target type ("str", "int", "float", "bool", "datetime")

        Returns:
            Converted value, or None if input is None

        Raises:
            ValueError: If conversion fails
        """
        # Handle NULL/None
        if value is None:
            return None

        try:
            if target_type == "str":
                return str(value)
            elif target_type == "int":
                return int(value)
            elif target_type == "float":
                return float(value)
            elif target_type == "bool":
                # Handle various boolean representations
                if isinstance(value, bool):
                    return value
                if isinstance(value, (int, float)):
                    return bool(value)
                if isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes', 'y', 't')
                return bool(value)
            elif target_type == "datetime":
                # If already datetime, return as-is
                if hasattr(value, 'year'):  # datetime-like object
                    return value
                # If string, try parsing (database driver usually handles this)
                if isinstance(value, str):
                    from datetime import datetime
                    # Try common formats
                    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"]:
                        try:
                            return datetime.strptime(value, fmt)
                        except ValueError:
                            continue
                    raise ValueError(f"Could not parse datetime from: {value}")
                return value
            else:
                # Unknown type, return as-is
                logger.warning(f"Unknown target type '{target_type}', returning value as-is")
                return value

        except (ValueError, TypeError) as e:
            logger.error(f"Failed to convert {value} (type: {type(value).__name__}) to {target_type}: {e}")
            raise ValueError(f"Type conversion failed for {value} -> {target_type}: {e}")

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

    @staticmethod
    def _extract_table_name(sql_template: str) -> str | None:
        """
        Extract table name from SQL query.

        Args:
            sql_template: SQL SELECT query

        Returns:
            Table name if found, None otherwise (without brackets or quotes)
        """
        try:
            # Parse SQL
            parsed = sqlparse.parse(sql_template)
            if not parsed:
                return None

            statement = parsed[0]

            # Find FROM keyword and get next identifier
            from_seen = False
            for token in statement.tokens:
                if from_seen and isinstance(token, sqlparse.sql.Identifier):
                    # Return the table name (first part before any alias)
                    table_name = str(token.get_real_name())
                    # Remove SQL Server brackets and quotes
                    return table_name.strip('[]"\'')
                elif token.ttype is sqlparse.tokens.Keyword and token.value.upper() == 'FROM':
                    from_seen = True
                elif from_seen and token.ttype is not sqlparse.tokens.Whitespace:
                    # Could be a direct name token instead of Identifier
                    token_value = str(token).strip()
                    # Remove any alias (split on space)
                    table_name = token_value.split()[0]
                    # Remove SQL Server brackets and quotes
                    return table_name.strip('[]"\'')

            return None
        except Exception as e:
            logger.error(f"Failed to extract table name from SQL: {e}")
            return None

    @staticmethod
    def _table_exists(db_connection: Any, table_name: str) -> bool:
        """
        Check if a table exists in the database.

        Args:
            db_connection: Database connection (pyodbc connection)
            table_name: Name of the table to check

        Returns:
            True if table exists, False otherwise
        """
        try:
            # Use pyodbc cursor.tables() method to check if table exists
            with db_connection.cursor() as cursor:
                # Get all tables
                tables = cursor.tables(tableType='TABLE').fetchall()
                # Check if our table exists (case-insensitive comparison)
                table_names = [row.table_name.lower() for row in tables]
                return table_name.lower() in table_names
        except Exception as e:
            logger.error(f"Failed to check if table '{table_name}' exists: {e}")
            raise

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

        # Step 7: Convert SQL template to parameterized form
        parameterized_sql, param_names = self._convert_to_parameterized_sql(cfg.sql_template)
        logger.info(f"[SQL LOOKUP] Parameterized SQL: {parameterized_sql}")
        logger.info(f"[SQL LOOKUP] Parameters (in order): {param_names}")

        # Step 8: Build parameter tuple in correct order
        param_values = tuple(input_values[name] for name in param_names)
        logger.info(f"[SQL LOOKUP] Parameter values: {param_values}")

        # Step 9: Get database connection from services
        if not services:
            raise RuntimeError("Services container not available - cannot access database connections")

        try:
            db_connection = services.get_connection(cfg.database)
            logger.info(f"[SQL LOOKUP] Retrieved connection for database: {cfg.database}")
        except Exception as e:
            raise RuntimeError(f"Failed to get database connection '{cfg.database}': {e}")

        # Step 10: Execute parameterized query
        try:
            logger.info("=" * 80)
            logger.info("[SQL LOOKUP] Executing parameterized SQL query...")
            logger.info(f"SQL: {parameterized_sql}")
            logger.info(f"Params: {param_values}")
            logger.info("=" * 80)

            with db_connection.cursor() as cursor:
                cursor.execute(parameterized_sql, param_values)
                rows = cursor.fetchall()
                # Capture column information before cursor closes
                # cursor.description is a list of tuples: [(col_name, type_code, ...), ...]
                column_info = cursor.description if cursor.description else []

            logger.info(f"[SQL LOOKUP] Query returned {len(rows)} row(s)")

        except Exception as e:
            logger.error(f"[SQL LOOKUP] Query execution failed: {e}")
            raise RuntimeError(f"SQL query execution failed: {e}")

        # Step 11: Handle result cardinality based on configuration
        if len(rows) == 0:
            # No rows returned
            if cfg.on_no_rows == "error":
                raise RuntimeError("SQL query returned no rows (on_no_rows='error')")
            # Return None/null for all outputs
            logger.info("[SQL LOOKUP] No rows returned, returning None for all outputs")
            outputs = {}
            for column_name in expected_columns:
                pin = output_name_to_pin[column_name]
                outputs[pin.node_id] = None
            return outputs

        if len(rows) > 1:
            # Multiple rows returned
            if cfg.on_multiple_rows == "error":
                raise RuntimeError(f"SQL query returned {len(rows)} rows (on_multiple_rows='error')")
            elif cfg.on_multiple_rows == "first":
                row = rows[0]
                logger.info(f"[SQL LOOKUP] Multiple rows returned, using first row")
            else:  # "last"
                row = rows[-1]
                logger.info(f"[SQL LOOKUP] Multiple rows returned, using last row")
        else:
            row = rows[0]

        # Step 12: Map row columns to outputs with type conversion
        outputs = {}
        try:
            for column_name in expected_columns:
                pin = output_name_to_pin[column_name]

                # Access column value by name (case-insensitive for Access)
                try:
                    # Try accessing by attribute name (pyodbc Row objects support this)
                    column_value = getattr(row, column_name, None)
                    if column_value is None and hasattr(row, column_name.lower()):
                        column_value = getattr(row, column_name.lower())
                except AttributeError:
                    # Fallback: Access by index if we know the column order
                    # This requires matching column_name to cursor.description
                    raise RuntimeError(f"Could not access column '{column_name}' from result row")

                # Convert to target type
                converted_value = self._convert_to_type(column_value, pin.type)
                outputs[pin.node_id] = converted_value

                logger.info(f"[SQL LOOKUP] Output '{column_name}' = {converted_value} (type: {pin.type}, db_value: {column_value})")

        except Exception as e:
            logger.error(f"[SQL LOOKUP] Failed to map results to outputs: {e}")
            raise RuntimeError(f"Failed to map query results to outputs: {e}")

        logger.info(f"[SQL LOOKUP] Execution complete - returned {len(outputs)} outputs")
        return outputs
