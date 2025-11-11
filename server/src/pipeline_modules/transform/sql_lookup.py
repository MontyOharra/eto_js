"""
SQL Lookup Transform Module
Executes a SQL SELECT query against configured database and returns results
"""
from typing import Dict, Any, List, Literal
from pydantic import BaseModel, Field

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

    def run(self, inputs: Dict[str, Any], cfg: SqlLookupConfig, context: Any) -> Dict[str, Any]:
        """
        Execute SQL lookup query
        TODO: Implement execution logic
        """
        raise NotImplementedError("SQL Lookup execution not yet implemented")
