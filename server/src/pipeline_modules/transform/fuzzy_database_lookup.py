"""
Fuzzy Database Lookup Transform Module
Finds the best matching value in a database column using fuzzy string matching
"""
import logging
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from rapidfuzz import fuzz, process

from shared.types import TransformModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register

logger = logging.getLogger(__name__)


class FuzzyDatabaseLookupConfig(BaseModel):
    """Configuration for Fuzzy Database Lookup"""

    # Database & Table
    database: str = Field(
        default="htc_db",
        description="Database name to query (business database only)"
    )
    table: str = Field(..., description="Table to search in")

    # Column Configuration
    search_column: str = Field(..., description="Column to match against")
    return_column: str = Field(..., description="Column to return as matched value")

    # Matching Configuration
    algorithm: Literal["ratio", "partial_ratio", "token_sort_ratio", "token_set_ratio"] = Field(
        default="token_sort_ratio",
        description="Fuzzy matching algorithm to use"
    )
    
    min_confidence: int = Field(
        default=80, 
        description="Minimum confidence score (0-100) to consider a match valid"
    )

    # Query Optimization (optional)
    where_clause: Optional[str] = Field(
        default=None,
        description="Optional SQL WHERE clause to filter candidates (e.g., 'active = 1')"
    )
    limit: Optional[int] = Field(
        default=None,
        description="Limit number of rows to compare (None = all rows)"
    )

    # Case sensitivity
    case_sensitive: bool = Field(
        default=False,
        description="Whether matching should be case-sensitive"
    )


@register
class FuzzyDatabaseLookup(TransformModule):
    """
    Fuzzy Database Lookup transform module
    Finds the best matching value in a database column using fuzzy string matching
    """

    # Class metadata
    id = "fuzzy_database_lookup"
    version = "1.0.0"
    title = "Fuzzy Database Lookup"
    description = "Find best matching value in database using fuzzy string matching"
    category = "Database"
    color = "#8B5CF6"  # Purple

    # Configuration model
    ConfigModel = FuzzyDatabaseLookupConfig

    @classmethod
    def config_schema(cls) -> Dict[str, Any]:
        """
        Generate config schema with dynamic database connection enum.

        Injects available business database connections from ServiceContainer
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
                else:
                    logger.warning("No business database connections available")
            else:
                logger.warning("ServiceContainer not initialized yet - cannot inject database connections")

        except Exception as e:
            logger.warning(f"Could not inject database connections into schema: {e}")
            # Schema will still work, just won't have enum (will be text input instead)

        return schema

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="search_text",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="matched_value",
                            typing=NodeTypeRule(allowed_types=["str", "None"]),
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            label="confidence",
                            typing=NodeTypeRule(allowed_types=["float"]),
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            label="match_found",
                            typing=NodeTypeRule(allowed_types=["bool"]),
                            min_count=1,
                            max_count=1
                        )
                    ]
                )
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: FuzzyDatabaseLookupConfig, context: Any, services: Any = None) -> Dict[str, Any]:
        """
        Execute fuzzy database lookup

        Args:
            inputs: Dictionary with search_text input
            cfg: Validated configuration
            context: Execution context with ordered inputs/outputs
            services: DatabaseManager for database access

        Returns:
            Dictionary with matched_value, confidence, and match_found outputs
        """
        # Validate services
        if services is None:
            raise ValueError("DatabaseManager services required for fuzzy_database_lookup")

        # Get input
        input_node_id = list(inputs.keys())[0]
        search_text = inputs[input_node_id]

        # Get output node IDs
        matched_value_id = context.outputs[0].node_id
        confidence_id = context.outputs[1].node_id
        match_found_id = context.outputs[2].node_id

        # Handle None/empty input
        if not search_text:
            return {
                matched_value_id: None,
                confidence_id: 0.0,
                match_found_id: False
            }

        # Get database connection
        connection = services.get_connection(cfg.database)

        # Build SQL query
        sql = f"SELECT [{cfg.search_column}], [{cfg.return_column}] FROM [{cfg.table}]"

        if cfg.where_clause:
            sql += f" WHERE {cfg.where_clause}"

        if cfg.limit:
            sql += f" LIMIT {cfg.limit}"

        # Execute query using pyodbc cursor (with context manager)
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

        # Handle empty result set
        if not rows or len(rows) == 0:
            return {
                matched_value_id: None,
                confidence_id: 0.0,
                match_found_id: False
            }

        # Prepare search text for matching
        search_query = search_text if cfg.case_sensitive else search_text.lower()

        # Build choices list for fuzzy matching
        # pyodbc rows are accessed by index - first column is search, second is return
        choices = []
        for row in rows:
            # Access by index (SELECT returns columns in order: search_column, return_column)
            search_value = row[0]  # cfg.search_column
            return_value = row[1]  # cfg.return_column

            # Skip None values
            if search_value is None:
                continue

            # Apply case sensitivity
            match_value = str(search_value) if cfg.case_sensitive else str(search_value).lower()

            choices.append((match_value, return_value))

        # Handle no valid choices
        if not choices:
            return {
                matched_value_id: None,
                confidence_id: 0.0,
                match_found_id: False
            }

        # Select fuzzy matching algorithm
        algorithm_map = {
            "ratio": fuzz.ratio,
            "partial_ratio": fuzz.partial_ratio,
            "token_sort_ratio": fuzz.token_sort_ratio,
            "token_set_ratio": fuzz.token_set_ratio
        }
        scorer = algorithm_map[cfg.algorithm]

        # Extract only search values for matching
        search_values = [choice[0] for choice in choices]

        # Find best match
        best_match = process.extractOne(
            search_query,
            search_values,
            scorer=scorer
        )

        # best_match is tuple: (matched_string, score, index)
        if best_match is None:
            return {
                matched_value_id: None,
                confidence_id: 0.0,
                match_found_id: False
            }

        matched_string, score, index = best_match

        # Check confidence threshold
        if score < cfg.min_confidence:
            return {
                matched_value_id: None,
                confidence_id: score,
                match_found_id: False
            }

        # Get return value from original choices
        return_value = choices[index][1]

        return {
            matched_value_id: return_value,
            confidence_id: score,
            match_found_id: True
        }
