"""
SQL Lookup Transform Module
Executes a SQL SELECT query against configured database and returns results
"""
import re
import os
from typing import Dict, Any, List, Tuple, Optional
from pydantic import BaseModel, Field
import psycopg2
import psycopg2.extras

from shared.types import TransformModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register


class SqlLookupConfig(BaseModel):
    """Configuration for SQL lookup"""
    sql_template: str = Field(
        description="SQL SELECT query with {input_name} placeholders for inputs and column names/aliases for outputs",
        example="SELECT order_id, customer_name FROM orders WHERE hawb = {hawb_input}"
    )
    database: str = Field(
        default="DATABASE_ETO",
        description="Database connection to use (must match env var name like DATABASE_ETO)"
    )
    on_multiple_rows: str = Field(
        default="error",
        description="How to handle multiple rows: 'first', 'last', or 'error'"
    )
    on_no_rows: str = Field(
        default="error",
        description="How to handle no rows: 'null' or 'error'"
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
                            min_count=0,
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
    def validate_wiring(
        cls,
        module_instance_id: str,
        cfg: Dict[str, Any],
        instance_inputs: List[Dict[str, Any]],
        instance_outputs: List[Dict[str, Any]],
        upstream_of_input: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Validate that pin names match SQL template placeholders and columns

        Returns list of validation errors (empty if valid)
        """
        errors = []

        try:
            sql_template = cfg.get("sql_template", "")
            if not sql_template:
                errors.append({
                    "field": "sql_template",
                    "message": "SQL template is required"
                })
                return errors

            # Extract input placeholders: {input_name}
            input_placeholders = re.findall(r'\{(\w+)\}', sql_template)

            # Extract output columns from SELECT clause
            output_columns = cls._parse_select_columns(sql_template)

            # Get actual pin names
            input_pin_names = [pin["name"] for pin in instance_inputs]
            output_pin_names = [pin["name"] for pin in instance_outputs]

            # Check all placeholders have corresponding input pins
            for placeholder in input_placeholders:
                if placeholder not in input_pin_names:
                    errors.append({
                        "field": "inputs",
                        "message": f"SQL template references {{'{placeholder}'}}, but no input pin named '{placeholder}' exists"
                    })

            # Check all input pins are used in template
            for pin_name in input_pin_names:
                if pin_name not in input_placeholders:
                    errors.append({
                        "field": "inputs",
                        "message": f"Input pin '{pin_name}' is not used in SQL template"
                    })

            # Check all output columns have corresponding output pins
            if output_columns:  # Only if we successfully parsed columns
                for column in output_columns:
                    if column not in output_pin_names:
                        errors.append({
                            "field": "outputs",
                            "message": f"SQL SELECT returns column '{column}', but no output pin named '{column}' exists"
                        })

                # Check all output pins match columns
                for pin_name in output_pin_names:
                    if pin_name not in output_columns:
                        errors.append({
                            "field": "outputs",
                            "message": f"Output pin '{pin_name}' does not match any column in SELECT clause"
                        })

        except Exception as e:
            errors.append({
                "field": "sql_template",
                "message": f"Error parsing SQL template: {str(e)}"
            })

        return errors

    @staticmethod
    def _parse_select_columns(sql_template: str) -> List[str]:
        """
        Parse SELECT clause to extract column names/aliases

        Returns list of output column names (using aliases where present)

        Examples:
            "SELECT order_id, customer_name FROM..." → ['order_id', 'customer_name']
            "SELECT order_id, name AS customer FROM..." → ['order_id', 'customer']
            "SELECT COUNT(*) AS total FROM..." → ['total']
        """
        try:
            # Extract SELECT clause (between SELECT and FROM)
            select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql_template, re.IGNORECASE | re.DOTALL)
            if not select_match:
                return []

            select_clause = select_match.group(1)

            # Split by comma (simple parsing, won't handle nested functions perfectly)
            columns = []
            for part in select_clause.split(','):
                part = part.strip()

                # Check for AS keyword
                as_match = re.search(r'\s+AS\s+(\w+)', part, re.IGNORECASE)
                if as_match:
                    # Use alias
                    columns.append(as_match.group(1))
                else:
                    # Try to extract simple column name (word characters only)
                    col_match = re.search(r'(\w+)$', part)
                    if col_match:
                        columns.append(col_match.group(1))

            return columns
        except Exception:
            return []

    def run(self, inputs: Dict[str, Any], cfg: SqlLookupConfig, context: Any) -> Dict[str, Any]:
        """
        Execute SQL lookup query

        Args:
            inputs: Dictionary with input values keyed by node_id
            cfg: Validated configuration
            context: Execution context with input/output metadata

        Returns:
            Dictionary with output values keyed by node_id

        Raises:
            ValueError: If query returns != 1 row (depending on config)
            RuntimeError: If database connection fails or query fails
        """
        # Get database connection string from environment
        conn_string = os.environ.get(cfg.database)
        if not conn_string:
            raise RuntimeError(
                f"Database connection '{cfg.database}' not found in environment. "
                f"Set {cfg.database} environment variable."
            )

        # Map input pins to their values by name
        input_values_by_name = {}
        for input_pin in context.inputs:
            value = inputs.get(input_pin.node_id)
            input_values_by_name[input_pin.name] = value

        # Parse SQL template to build parameterized query
        # Replace {placeholder} with $1, $2, etc. for PostgreSQL parameterized queries
        parameterized_sql, param_names = self._parameterize_sql(cfg.sql_template)

        # Build params list in order
        params = [input_values_by_name[name] for name in param_names]

        # Execute query
        try:
            conn = psycopg2.connect(conn_string)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute(parameterized_sql, params)
            rows = cursor.fetchall()

            cursor.close()
            conn.close()

        except psycopg2.Error as e:
            raise RuntimeError(f"Database query failed: {e}")

        # Handle row count based on config
        if len(rows) == 0:
            if cfg.on_no_rows == "error":
                raise ValueError(f"SQL query returned 0 rows (expected exactly 1)")
            else:  # "null"
                # Return None for all outputs
                return {pin.node_id: None for pin in context.outputs}

        if len(rows) > 1:
            if cfg.on_multiple_rows == "error":
                raise ValueError(f"SQL query returned {len(rows)} rows (expected exactly 1)")
            elif cfg.on_multiple_rows == "first":
                row = rows[0]
            elif cfg.on_multiple_rows == "last":
                row = rows[-1]
            else:
                raise ValueError(f"Invalid on_multiple_rows value: {cfg.on_multiple_rows}")
        else:
            row = rows[0]

        # Map result columns to output pins by name
        outputs = {}
        for output_pin in context.outputs:
            column_name = output_pin.name
            if column_name in row:
                outputs[output_pin.node_id] = row[column_name]
            else:
                raise RuntimeError(
                    f"Query result missing expected column '{column_name}'. "
                    f"Available columns: {list(row.keys())}"
                )

        return outputs

    @staticmethod
    def _parameterize_sql(sql_template: str) -> Tuple[str, List[str]]:
        """
        Convert SQL template with {placeholders} to parameterized query with $1, $2, etc.

        Args:
            sql_template: SQL with {input_name} placeholders

        Returns:
            Tuple of (parameterized_sql, param_names_in_order)

        Example:
            Input: "SELECT * FROM orders WHERE hawb = {hawb} AND status = {status}"
            Output: ("SELECT * FROM orders WHERE hawb = $1 AND status = $2", ['hawb', 'status'])
        """
        # Find all {placeholder} occurrences in order
        placeholders = re.findall(r'\{(\w+)\}', sql_template)

        # Build mapping of {placeholder} -> $N
        parameterized_sql = sql_template
        for i, placeholder in enumerate(placeholders, start=1):
            parameterized_sql = parameterized_sql.replace(
                f'{{{placeholder}}}',
                f'${i}',
                1  # Only replace first occurrence to maintain order
            )

        return parameterized_sql, placeholders
