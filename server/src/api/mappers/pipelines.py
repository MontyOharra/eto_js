"""
Pipeline API Mappers
Convert between domain types and API schemas
"""
from shared.types.pipelines import (
    NodeInstance as NodeInstanceDomain,
    EntryPoint as EntryPointDomain,
    ModuleInstance as ModuleInstanceDomain,
    NodeConnection as NodeConnectionDomain,
    PipelineState as PipelineStateDomain,
    VisualState as VisualStateDomain,
    Position as PositionDomain,
)
from shared.types.pipeline_definition import (
    PipelineDefinition,
    PipelineDefinitionSummary,
    PipelineDefinitionCreate,
)
from api.schemas.pipelines import (
    Node,
    EntryPoint,
    ModuleInstance,
    NodeConnection,
    PipelineState,
    VisualState,
    Position,
    PipelineSummary,
    PipelineDetail,
    CreatePipelineRequest,
    PipelinesListResponse,
)


# ========== Domain → API (Response) Conversions ==========

def convert_node(node: NodeInstanceDomain) -> Node:
    """Convert domain NodeInstance to API Node"""
    return Node(
        node_id=node.node_id,
        type=node.type,
        name=node.name,
        position_index=node.position_index,
        group_index=node.group_index
    )


def convert_entry_point(entry_point: EntryPointDomain) -> EntryPoint:
    """Convert domain EntryPoint to API EntryPoint"""
    return EntryPoint(
        entry_point_id=entry_point.entry_point_id,
        name=entry_point.name,
        outputs=[convert_node(node) for node in entry_point.outputs]
    )


def convert_module_instance(module: ModuleInstanceDomain) -> ModuleInstance:
    """Convert domain ModuleInstance to API ModuleInstance"""
    return ModuleInstance(
        module_instance_id=module.module_instance_id,
        module_ref=module.module_ref,
        config=module.config,
        inputs=[convert_node(node) for node in module.inputs],
        outputs=[convert_node(node) for node in module.outputs]
    )


def convert_connection(connection: NodeConnectionDomain) -> NodeConnection:
    """Convert domain NodeConnection to API NodeConnection"""
    return NodeConnection(
        from_node_id=connection.from_node_id,
        to_node_id=connection.to_node_id
    )


def convert_pipeline_state(pipeline_state: PipelineStateDomain) -> PipelineState:
    """Convert domain PipelineState to API PipelineState"""
    return PipelineState(
        entry_points=[convert_entry_point(ep) for ep in pipeline_state.entry_points],
        modules=[convert_module_instance(mod) for mod in pipeline_state.modules],
        connections=[convert_connection(conn) for conn in pipeline_state.connections]
    )


def convert_visual_state(visual_state: VisualStateDomain) -> VisualState:
    """Convert domain VisualState to API VisualState (flat structure)"""
    # visual_state is already a dict at domain level
    return {
        key: Position(x=pos.x, y=pos.y)
        for key, pos in visual_state.items()
    }


def convert_pipeline_summary(summary: PipelineDefinitionSummary) -> PipelineSummary:
    """Convert domain PipelineDefinitionSummary to API PipelineSummary"""
    return PipelineSummary(
        id=summary.id
    )


def convert_pipeline_summary_list(summaries: list[PipelineDefinitionSummary]) -> list[PipelineSummary]:
    """Convert list of domain summaries to API schemas"""
    return [convert_pipeline_summary(summary) for summary in summaries]


def convert_pipeline_detail(pipeline: PipelineDefinition) -> PipelineDetail:
    """Convert domain PipelineDefinition to API PipelineDetail"""
    return PipelineDetail(
        id=pipeline.id,
        pipeline_state=convert_pipeline_state(pipeline.pipeline_state),
        visual_state=convert_visual_state(pipeline.visual_state)
    )


# ========== API (Request) → Domain Conversions ==========

def convert_node_to_domain(node: Node | dict) -> NodeInstanceDomain:
    """
    Convert API Node to domain NodeInstance.
    Handles both Pydantic models and dictionaries.
    """
    if isinstance(node, dict):
        return NodeInstanceDomain(
            node_id=node['node_id'],
            type=node['type'],
            name=node['name'],
            position_index=node['position_index'],
            group_index=node['group_index']
        )

    return NodeInstanceDomain(
        node_id=node.node_id,
        type=node.type,
        name=node.name,
        position_index=node.position_index,
        group_index=node.group_index
    )


def convert_entry_point_to_domain(entry_point: EntryPoint | dict) -> EntryPointDomain:
    """
    Convert API EntryPoint to domain EntryPoint.
    Handles both Pydantic models and dictionaries.
    """
    if isinstance(entry_point, dict):
        return EntryPointDomain(
            entry_point_id=entry_point['entry_point_id'],
            name=entry_point['name'],
            outputs=[convert_node_to_domain(node) for node in entry_point.get('outputs', [])]
        )

    return EntryPointDomain(
        entry_point_id=entry_point.entry_point_id,
        name=entry_point.name,
        outputs=[convert_node_to_domain(node) for node in entry_point.outputs]
    )


def convert_module_instance_to_domain(module: ModuleInstance | dict) -> ModuleInstanceDomain:
    """
    Convert API ModuleInstance to domain ModuleInstance.
    Recursively converts nested inputs/outputs.
    Handles both Pydantic models and dictionaries.
    """
    if isinstance(module, dict):
        return ModuleInstanceDomain(
            module_instance_id=module['module_instance_id'],
            module_ref=module['module_ref'],
            config=module['config'],
            inputs=[convert_node_to_domain(node) for node in module.get('inputs', [])],
            outputs=[convert_node_to_domain(node) for node in module.get('outputs', [])]
        )

    return ModuleInstanceDomain(
        module_instance_id=module.module_instance_id,
        module_ref=module.module_ref,
        config=module.config,
        inputs=[convert_node_to_domain(node) for node in module.inputs],
        outputs=[convert_node_to_domain(node) for node in module.outputs]
    )


def convert_connection_to_domain(connection: NodeConnection | dict) -> NodeConnectionDomain:
    """
    Convert API NodeConnection to domain NodeConnection.
    Handles both Pydantic models and dictionaries.
    """
    if isinstance(connection, dict):
        return NodeConnectionDomain(
            from_node_id=connection['from_node_id'],
            to_node_id=connection['to_node_id']
        )

    return NodeConnectionDomain(
        from_node_id=connection.from_node_id,
        to_node_id=connection.to_node_id
    )


def convert_pipeline_state_to_domain(pipeline_state: PipelineState | dict) -> PipelineStateDomain:
    """
    Convert API PipelineState to domain PipelineState.
    Recursively converts all nested structures.
    Handles both Pydantic models and dictionaries.
    """
    if isinstance(pipeline_state, dict):
        return PipelineStateDomain(
            entry_points=[
                convert_entry_point_to_domain(ep)
                for ep in pipeline_state.get('entry_points', [])
            ],
            modules=[
                convert_module_instance_to_domain(mod)
                for mod in pipeline_state.get('modules', [])
            ],
            connections=[
                convert_connection_to_domain(conn)
                for conn in pipeline_state.get('connections', [])
            ]
        )

    return PipelineStateDomain(
        entry_points=[convert_entry_point_to_domain(ep) for ep in pipeline_state.entry_points],
        modules=[convert_module_instance_to_domain(mod) for mod in pipeline_state.modules],
        connections=[convert_connection_to_domain(conn) for conn in pipeline_state.connections]
    )


def convert_visual_state_to_domain(visual_state: VisualState | dict) -> VisualStateDomain:
    """
    Convert API VisualState to domain VisualState (flat structure).
    Handles both dictionaries with Position objects and plain dicts.
    """
    positions_dict = {}

    # Handle flat dict structure
    if isinstance(visual_state, dict):
        for key, pos in visual_state.items():
            if isinstance(pos, dict):
                # Plain dict with x, y keys
                positions_dict[key] = PositionDomain(x=pos['x'], y=pos['y'])
            else:
                # Position object
                positions_dict[key] = PositionDomain(x=pos.x, y=pos.y)

    return positions_dict


def convert_create_request(request: CreatePipelineRequest) -> PipelineDefinitionCreate:
    """Convert API CreatePipelineRequest to domain PipelineDefinitionCreate"""
    return PipelineDefinitionCreate(
        pipeline_state=convert_pipeline_state_to_domain(request.pipeline_state),
        visual_state=convert_visual_state_to_domain(request.visual_state)
    )


def convert_execution_result(result):
    """
    Convert domain execution result to API ExecutePipelineResponse.

    Args:
        result: Domain execution result object

    Returns:
        ExecutePipelineResponse for API
    """
    from api.schemas.pipelines import ExecutePipelineResponse, ExecutionStepResult

    steps = [
        ExecutionStepResult(
            module_instance_id=step.module_instance_id,
            step_number=step.step_number,
            inputs=step.inputs,
            outputs=step.outputs,
            error=step.error
        )
        for step in result.steps
    ]

    return ExecutePipelineResponse(
        status=result.status,
        steps=steps,
        executed_actions=result.executed_actions,
        error=result.error
    )
