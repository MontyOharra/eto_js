"""
Create Order Action Module
Inserts order data into an external database
"""
from typing import Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy import text

from shared.types import ActionModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.service import register


class CreateOrderConfig(BaseModel):
    """Configuration for Create Order action"""
    database_connection: str = Field(..., description="Name of the database connection to use (e.g., 'orders_db')")
    table_name: str = Field("orders", description="Name of the table to insert into")


@register
class CreateOrder(ActionModule):
    """
    Create Order action module
    Inserts order data into a configured database table

    Expects inputs:
    - customer_id (str or int)
    - mawb (float)
    - pu_date (datetime)

    Returns:
    - order_id (int): The ID of the created order
    """

    # Class metadata
    id = "create_order"
    version = "1.0.0"
    title = "Create Order"
    description = "Insert order data into external database"
    category = "Database"
    color = "#EF4444"  # Red

    # Configuration model
    ConfigModel = CreateOrderConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="hawb",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["str", "int"])
                        ),
                        NodeGroup(
                            label="mawb",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["float"])
                        ),
                        NodeGroup(
                            label="pu_date",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["datetime"])
                        )
                    ]
                )
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: CreateOrderConfig, context: Any) -> None:
        """
        Execute order creation

        Args:
            inputs: Dictionary with customer_id, mawb, pu_date
            cfg: Validated configuration with database connection info
            context: Execution context with services access

        Returns:
            Dictionary with created order_id
        """
        # Map input node_ids using context metadata
        hawb = context.inputs[0]  # customer_id
        mawb = context.inputs[1]  # mawb
        pu_date = context.inputs[2]   # pu_date

        # Extract values from inputs dict
        hawb = inputs[hawb.node_id]
        mawb = inputs[mawb.node_id]
        pu_date = inputs[pu_date.node_id]

        # Validate inputs
        if not isinstance(mawb, (int, float)):
            raise TypeError(f"mawb must be numeric, got {type(mawb).__name__}")

        if isinstance(pu_date, str):
            pu_date = datetime.fromisoformat(pu_date)
        elif not isinstance(pu_date, datetime):
            raise TypeError(f"pu_date must be datetime or str, got {type(pu_date).__name__}")

        # Get database connection from service container
        if not context.services:
            raise RuntimeError("ServiceContainer not available in execution context")

        db_pool = context.services.get('database_pool')

        # Insert order into database
        try:
            with db_pool.get_connection(cfg.database_connection) as conn:
                # Parameterized insert query
                query = text(f"""
                    INSERT INTO {cfg.table_name} (mawb, hawb, pu_date)
                    OUTPUT INSERTED.id
                    VALUES (:mawb, :hawb, :pu_date)
                """)

                result = conn.execute(
                    query,
                    {
                        "hawb": hawb,
                        "mawb": mawb,
                        "pu_date": pu_date,
                        "created_at": datetime.utcnow()
                    }
                )
                
                conn.commit()

        except KeyError as e:
            raise RuntimeError(f"Database connection '{cfg.database_connection}' not configured: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Failed to create order: {str(e)}")
