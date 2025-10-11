"""
Index Builder
Builds lookup indices for efficient validation (§2.2 from spec)
"""
from typing import Dict, List, Optional
from pydantic import BaseModel
from shared.types import PipelineState, ModuleInstance, PinInfo, ModuleInstance, PipelineIndices



class IndexBuilder:
    """
    Builds PipelineIndices for efficient validation
    """
    
    @staticmethod
    def build_indices(pipeline_state: PipelineState) -> PipelineIndices:
        pin_by_id: Dict[str, PinInfo] = {}
        module_by_id: Dict[str, ModuleInstance] = {}
        input_to_upstream: Dict[str, str] = {}
        
        for entry in pipeline_state.entry_points:
            pin_by_id[entry.node_id] = PinInfo(
                node_id=entry.node_id,
                type="str",  # Entry points always output str
                module_instance_id=None,
                direction="entry",
                name=entry.name
            )
            
        for module in pipeline_state.modules:
            
            module_by_id[module.module_instance_id] = module
            
            for input_pin in module.inputs:
                pin_by_id[input_pin.node_id] = PinInfo(
                    node_id=input_pin.node_id,
                    type=input_pin.type,
                    module_instance_id=module.module_instance_id,
                    direction="in",
                    name=input_pin.name
                )
            for output_pin in module.outputs:
                pin_by_id[output_pin.node_id] = PinInfo(
                    node_id=output_pin.node_id,
                    type=output_pin.type,
                    module_instance_id=module.module_instance_id,
                    direction="out",
                    name=output_pin.name
                )
                
        for connection in pipeline_state.connections:
            input_to_upstream[connection.to_node_id] = connection.from_node_id
                
        return PipelineIndices(
            pin_by_id=pin_by_id, 
            module_by_id=module_by_id, 
            input_to_upstream=input_to_upstream
        )