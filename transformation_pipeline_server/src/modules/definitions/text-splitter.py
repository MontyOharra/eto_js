"""
Text Processing Modules for ETO Transformation Pipeline

This module contains various text processing transformation modules.
"""

import json
import re
from typing import Dict, Any, List
from ..module import BaseModuleExecutor, ModuleExecutionError

class TextSplitterModule(BaseModuleExecutor):
    """Split text into multiple chunks based on various criteria"""
    
    def get_module_id(self) -> str:
        return "text_splitter"
    
    def get_module_info(self) -> Dict[str, Any]:
        """Return the module template information for database storage"""
        return {
            'id': 'text_splitter',
            'name': 'Text Splitter',
            'description': 'Split text into multiple chunks based on various criteria',
            'version': '1.0.0',
            'input_schema': json.dumps([
                {
                    'name': 'input_text',
                    'type': 'string',
                    'description': 'Text to be split',
                    'required': True
                }
            ]),
            'output_schema': json.dumps([
                {
                    'name': 'chunk_1',
                    'type': 'string',
                    'description': 'Text chunk 1'
                }
            ]),
            # Indicate this module supports variable outputs (UI-driven)
            'max_inputs': 1,
            'max_outputs': None,  # None = unlimited, user can add/remove
            'dynamic_inputs': None,
            'dynamic_outputs': None,
            'color': '#8B5CF6',
            'category': 'Text Processing',
            'config_schema': json.dumps([
                {
                    'name': 'split_method',
                    'type': 'select',
                    'description': 'Method to use for splitting text',
                    'required': True,
                    'defaultValue': 'sentence',
                    'options': ['sentence', 'paragraph', 'word_count', 'character_count', 'delimiter']
                },
                {
                    'name': 'chunk_size',
                    'type': 'number',
                    'description': 'Target size for each chunk (words or characters)',
                    'required': False,
                    'defaultValue': 100
                },
                {
                    'name': 'custom_delimiter',
                    'type': 'string',
                    'description': 'Custom delimiter for splitting (if delimiter method selected)',
                    'required': False,
                    'placeholder': ','
                }
            ]),
            'service_endpoint': None,
            'handler_name': 'TextSplitterModule',
            'is_active': True
        }
    
    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], expected_outputs: List[str] | None = None) -> Dict[str, Any]:
        """Split the input text based on configuration"""
        try:
            # Validate inputs and config
            self.validate_inputs(inputs)
            self.validate_config(config)
            
            input_text = inputs.get('input_text', '')
            split_method = config.get('split_method', 'sentence')
            chunk_size = int(config.get('chunk_size', 100))
            custom_delimiter = config.get('custom_delimiter', ',')
            
            # Use expected_outputs to determine how many chunks to generate
            expected_output_names = expected_outputs or ['chunk_1', 'chunk_2', 'chunk_3']
            num_outputs = len(expected_output_names)
            
            chunks = []
            
            if split_method == 'sentence':
                # Split by sentences
                sentences = re.split(r'[.!?]+', input_text)
                chunks = [s.strip() for s in sentences if s.strip()]
            
            elif split_method == 'paragraph':
                # Split by paragraphs (double newlines)
                paragraphs = re.split(r'\n\s*\n', input_text)
                chunks = [p.strip() for p in paragraphs if p.strip()]
            
            elif split_method == 'word_count':
                # Split by word count
                words = input_text.split()
                chunks = []
                for i in range(0, len(words), chunk_size):
                    chunk = ' '.join(words[i:i + chunk_size])
                    chunks.append(chunk)
            
            elif split_method == 'character_count':
                # Split by character count
                for i in range(0, len(input_text), chunk_size):
                    chunk = input_text[i:i + chunk_size]
                    chunks.append(chunk)
            
            elif split_method == 'delimiter':
                # Split by custom delimiter
                chunks = input_text.split(custom_delimiter)
                chunks = [c.strip() for c in chunks]
            
            # Use expected_outputs to determine which outputs to generate
            expected_output_names = output_names or ['chunk_1', 'chunk_2', 'chunk_3']
            
            result = {}
            for i, output_name in enumerate(expected_output_names):
                if i < len(chunks):
                    result[output_name] = chunks[i]
                else:
                    result[output_name] = ''  # Empty string for unused chunks
            
            self.logger.info(f"Text split into {len(chunks)} chunks using {split_method} method")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Text splitting failed: {e}")
            raise ModuleExecutionError(f"Failed to split text: {str(e)}")