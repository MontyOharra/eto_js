"""
SQL Parser Module for ETO Transformation Pipeline

Parses SQL queries and extracts columns, tables, or other elements based on configuration.
"""

import json
import re
import sqlparse
from typing import Dict, Any, List, Optional
from ....types import (
    ModuleID, ModuleInfo, ExecutionInputs, ExecutionConfig, 
    ExecutionOutputs, ExecutionNodeInfo, NodeSchema, NodeConfiguration, ConfigSchema
)
from ...module import BaseModuleExecutor, ModuleExecutionError, ModuleValidationError


class SQLParserModule(BaseModuleExecutor):
    """SQL parser that extracts different elements based on configuration"""
    
    def get_module_id(self) -> ModuleID:
        return "sql_parser"
    
    def get_module_info(self) -> ModuleInfo:
        """Return the module template information for database storage"""
        
        # Input configuration - single SQL query input
        input_config: NodeConfiguration = {
            "nodes": [
                {
                    "defaultName": "sql_query",
                    "type": "string"
                }
            ],
            "dynamic": None,  # Static node count
            "allowedTypes": ["string"]  # Only string inputs allowed
        }
        
        # Output configuration - single parsed result output
        output_config: NodeConfiguration = {
            "nodes": [
                {
                    "defaultName": "parsed_result",
                    "type": "string"
                }
            ],
            "dynamic": None,  # Static node count
            "allowedTypes": ["string"]  # Only string outputs
        }
        
        # Configuration schema with template references
        config_schema: List[ConfigSchema] = [
            {
                "name": "parse_mode",
                "type": "select",
                "description": "What to extract from the SQL query",
                "required": True,
                "defaultValue": "columns",
                "options": ["columns", "tables", "conditions", "full_parse"]
            },
            {
                "name": "output_format",
                "type": "select",
                "description": "Format for the output data",
                "required": False,
                "defaultValue": "json",
                "options": ["json", "csv", "list"]
            },
            {
                "name": "table_filter",
                "type": "string",
                "description": "Filter results to tables matching pattern (regex). Use {input_0} to reference input data",
                "required": False
            },
            {
                "name": "column_filter",
                "type": "string",
                "description": "Filter results to columns matching pattern (regex). Use {output_0} to reference output node",
                "required": False
            }
        ]
        
        return {
            'id': 'sql_parser',
            'name': 'SQL Parser',
            'description': 'Parses SQL queries and extracts columns, tables, or other elements',
            'version': '1.0.0',
            'input_config': json.dumps(input_config),
            'output_config': json.dumps(output_config),
            'config_schema': json.dumps(config_schema),
            'service_endpoint': None,
            'handler_name': 'SQLParserModule',
            'color': '#10B981',
            'category': 'Data Processing',
            'is_active': True
        }
    
    def validate_config_template_references(self, config: ExecutionConfig, node_info: ExecutionNodeInfo) -> bool:
        """Validate that config templates reference valid nodes"""
        table_filter = config.get('table_filter', '')
        column_filter = config.get('column_filter', '')
        
        # Check for template references
        input_refs = re.findall(r'\{input_(\d+)\}', table_filter + column_filter)
        output_refs = re.findall(r'\{output_(\d+)\}', table_filter + column_filter)
        
        # Validate input references
        for ref in input_refs:
            index = int(ref)
            if index >= len(node_info['inputs']):
                raise ModuleValidationError(f"Config template references invalid input index {index}")
        
        # Validate output references  
        for ref in output_refs:
            index = int(ref)
            if index >= len(node_info['outputs']):
                raise ModuleValidationError(f"Config template references invalid output index {index}")
        
        return True
    
    def execute(
        self, 
        inputs: ExecutionInputs, 
        config: ExecutionConfig,
        node_info: ExecutionNodeInfo,
        output_names: Optional[List[str]] = None
    ) -> ExecutionOutputs:
        """Parse the SQL query based on configuration"""
        try:
            # Validate inputs and config
            self.validate_inputs(inputs)
            self.validate_config(config)
            self.validate_config_template_references(config, node_info)
            
            # Get the first (and only) input value
            input_values = list(inputs.values())
            if not input_values:
                raise ModuleExecutionError("No SQL query provided")
            
            sql_query = str(input_values[0])
            parse_mode = config.get('parse_mode', 'columns')
            output_format = config.get('output_format', 'json')
            
            # Resolve template references in filters
            table_filter = self.resolve_config_template(config.get('table_filter', ''), node_info)
            column_filter = self.resolve_config_template(config.get('column_filter', ''), node_info)
            
            # Parse SQL query
            try:
                parsed = sqlparse.parse(sql_query)[0]
            except Exception as e:
                raise ModuleExecutionError(f"Failed to parse SQL query: {e}")
            
            # Extract based on parse mode
            if parse_mode == 'columns':
                result = self._extract_columns(parsed, column_filter)
            elif parse_mode == 'tables':
                result = self._extract_tables(parsed, table_filter)
            elif parse_mode == 'conditions':
                result = self._extract_conditions(parsed)
            elif parse_mode == 'full_parse':
                result = self._full_parse(parsed)
            else:
                raise ModuleExecutionError(f"Unknown parse mode: {parse_mode}")
            
            # Format output
            formatted_result = self._format_output(result, output_format)
            
            self.logger.info(f"SQL parsed in {parse_mode} mode, {len(result)} items extracted")
            
            # Get the first (and only) output node ID
            output_node_ids = [node['nodeId'] for node in node_info['outputs']]
            if not output_node_ids:
                raise ModuleExecutionError("No output node configured")
            
            return ExecutionOutputs({
                output_node_ids[0]: formatted_result
            })
            
        except Exception as e:
            self.logger.error(f"SQL parsing failed: {e}")
            raise ModuleExecutionError(f"Failed to parse SQL: {str(e)}")
    
    def _extract_columns(self, parsed, column_filter: str) -> List[str]:
        """Extract column names from parsed SQL"""
        columns = []
        
        def extract_from_token(token):
            if hasattr(token, 'tokens'):
                for sub_token in token.tokens:
                    extract_from_token(sub_token)
            elif token.ttype is sqlparse.tokens.Name:
                col_name = str(token).strip()
                if column_filter:
                    if re.search(column_filter, col_name):
                        columns.append(col_name)
                else:
                    columns.append(col_name)
        
        extract_from_token(parsed)
        return list(set(columns))  # Remove duplicates
    
    def _extract_tables(self, parsed, table_filter: str) -> List[str]:
        """Extract table names from parsed SQL"""
        tables = []
        
        def extract_from_token(token):
            if hasattr(token, 'tokens'):
                for i, sub_token in enumerate(token.tokens):
                    if sub_token.ttype is sqlparse.tokens.Keyword and sub_token.value.upper() in ('FROM', 'JOIN', 'UPDATE', 'INTO'):
                        # Look for table name in next non-whitespace token
                        for next_token in token.tokens[i+1:]:
                            if next_token.ttype is not sqlparse.tokens.Whitespace:
                                table_name = str(next_token).strip()
                                if table_filter:
                                    if re.search(table_filter, table_name):
                                        tables.append(table_name)
                                else:
                                    tables.append(table_name)
                                break
                    extract_from_token(sub_token)
        
        extract_from_token(parsed)
        return list(set(tables))  # Remove duplicates
    
    def _extract_conditions(self, parsed) -> List[str]:
        """Extract WHERE conditions from parsed SQL"""
        conditions = []
        
        def extract_from_token(token):
            if hasattr(token, 'tokens'):
                for i, sub_token in enumerate(token.tokens):
                    if sub_token.ttype is sqlparse.tokens.Keyword and sub_token.value.upper() == 'WHERE':
                        # Collect tokens until next major keyword
                        condition_tokens = []
                        for next_token in token.tokens[i+1:]:
                            if (next_token.ttype is sqlparse.tokens.Keyword and 
                                next_token.value.upper() in ('GROUP', 'ORDER', 'HAVING', 'LIMIT')):
                                break
                            condition_tokens.append(str(next_token))
                        
                        if condition_tokens:
                            conditions.append(''.join(condition_tokens).strip())
                    extract_from_token(sub_token)
        
        extract_from_token(parsed)
        return conditions
    
    def _full_parse(self, parsed) -> Dict[str, Any]:
        """Return full parsed structure"""
        return {
            'statement_type': parsed.get_type(),
            'tokens': [{'type': str(token.ttype), 'value': str(token)} for token in parsed.tokens],
            'formatted': str(parsed)
        }
    
    def _format_output(self, result, output_format: str) -> str:
        """Format the result based on output format"""
        if output_format == 'json':
            return json.dumps(result, indent=2)
        elif output_format == 'csv':
            if isinstance(result, list):
                return ','.join(result)
            else:
                return str(result)
        elif output_format == 'list':
            if isinstance(result, list):
                return '\n'.join(result)
            else:
                return str(result)
        else:
            return str(result)