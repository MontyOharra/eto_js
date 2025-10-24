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
)
from shared.types.pipeline_definition import (
    PipelineDefinitionFull,
    PipelineDefinitionSummary,
    PipelineDefinitionCreate,
)
from api.schemas.pipelines import (
    NodeDTO,
    EntryPointDTO,
    ModuleInstanceDTO,
    NodeConnectionDTO,
    PipelineStateDTO,
    VisualStateDTO,
    PositionDTO,
    PipelineSummaryDTO,
    PipelineDetailDTO,
    CreatePipelineRequest,
    PipelinesListResponse,
)


# ========== Domain → API (Response) Conversions ==========

def convert_node_to_dto(node: NodeInstanceDomain) -> NodeDTO:
    """Convert domain NodeInstance to API NodeDTO"""
    return NodeDTO(
        node_id=node.node_id,
        type=node.type,
        name=node.name,
        position_index=node.position_index,
        group_index=node.group_index
    )


def convert_entry_point_to_dto(entry_point: EntryPointDomain) -> EntryPointDTO:
    """Convert domain EntryPoint to API EntryPointDTO"""
    return EntryPointDTO(
        node_id=entry_point.node_id,
        name=entry_point.name
    )


def convert_module_instance_to_dto(module: ModuleInstanceDomain) -> ModuleInstanceDTO:
    """Convert domain ModuleInstance to API ModuleInstanceDTO"""
    return ModuleInstanceDTO(
        module_instance_id=module.module_instance_id,
        module_ref=module.module_ref,
        config=module.config,
        inputs=[convert_node_to_dto(node) for node in module.inputs],
        outputs=[convert_node_to_dto(node) for node in module.outputs]
    )


def convert_connection_to_dto(connection: NodeConnectionDomain) -> NodeConnectionDTO:
    """Convert domain NodeConnection to API NodeConnectionDTO"""
    return NodeConnectionDTO(
        from_node_id=connection.from_node_id,
        to_node_id=connection.to_node_id
    )


def convert_pipeline_state_to_dto(pipeline_state: PipelineStateDomain) -> PipelineStateDTO:
    """Convert domain PipelineState to API PipelineStateDTO"""
    return PipelineStateDTO(
        entry_points=[convert_entry_point_to_dto(ep) for ep in pipeline_state.entry_points],
        modules=[convert_module_instance_to_dto(mod) for mod in pipeline_state.modules],
        connections=[convert_connection_to_dto(conn) for conn in pipeline_state.connections]
    )


def convert_visual_state_to_dto(visual_state: VisualStateDomain) -> VisualStateDTO:
    """Convert domain VisualState to API VisualStateDTO"""
    return VisualStateDTO(
        modules={
            key: PositionDTO(x=pos[0], y=pos[1])
            for key, pos in visual_state.modules.items()
        },
        entry_points={
            key: PositionDTO(x=pos[0], y=pos[1])
            for key, pos in visual_state.entry_points.items()
        }
    )


def convert_pipeline_summary(summary: PipelineDefinitionSummary) -> PipelineSummaryDTO:
    """Convert domain PipelineDefinitionSummary to API PipelineSummaryDTO"""
    return PipelineSummaryDTO(
        id=summary.id,
        compiled_plan_id=summary.compiled_plan_id,
        created_at=summary.created_at.isoformat(),
        updated_at=summary.updated_at.isoformat()
    )


def convert_pipeline_summary_list(summaries: list[PipelineDefinitionSummary]) -> list[PipelineSummaryDTO]:
    """Convert list of domain summaries to API schemas"""
    return [convert_pipeline_summary(summary) for summary in summaries]


def convert_pipeline_detail(pipeline: PipelineDefinitionFull) -> PipelineDetailDTO:
    """Convert domain PipelineDefinitionFull to API PipelineDetailDTO"""
    return PipelineDetailDTO(
        id=pipeline.id,
        compiled_plan_id=pipeline.compiled_plan_id,
        pipeline_state=convert_pipeline_state_to_dto(pipeline.pipeline_state),
        visual_state=convert_visual_state_to_dto(pipeline.visual_state)
    )


# ========== API (Request) → Domain Conversions ==========

def convert_dto_to_node(node_dto: NodeDTO) -> NodeInstanceDomain:
    """Convert API NodeDTO to domain NodeInstance"""
    return NodeInstanceDomain(
        node_id=node_dto.node_id,
        type=node_dto.type,
        name=node_dto.name,
        position_index=node_dto.position_index,
        group_index=node_dto.group_index
    )


def convert_dto_to_entry_point(entry_point_dto: EntryPointDTO) -> EntryPointDomain:
    """Convert API EntryPointDTO to domain EntryPoint"""
    return EntryPointDomain(
        node_id=entry_point_dto.node_id,
        name=entry_point_dto.name
    )


def convert_dto_to_module_instance(module_dto: ModuleInstanceDTO) -> ModuleInstanceDomain:
    """Convert API ModuleInstanceDTO to domain ModuleInstance"""
    return ModuleInstanceDomain(
        module_instance_id=module_dto.module_instance_id,
        module_ref=module_dto.module_ref,
        config=module_dto.config,
        inputs=[convert_dto_to_node(node) for node in module_dto.inputs],
        outputs=[convert_dto_to_node(node) for node in module_dto.outputs]
    )


def convert_dto_to_connection(connection_dto: NodeConnectionDTO) -> NodeConnectionDomain:
    """Convert API NodeConnectionDTO to domain NodeConnection"""
    return NodeConnectionDomain(
        from_node_id=connection_dto.from_node_id,
        to_node_id=connection_dto.to_node_id
    )


def convert_dto_to_pipeline_state(pipeline_state_dto: PipelineStateDTO) -> PipelineStateDomain:
    """Convert API PipelineStateDTO to domain PipelineState"""
    return PipelineStateDomain(
        entry_points=[convert_dto_to_entry_point(ep) for ep in pipeline_state_dto.entry_points],
        modules=[convert_dto_to_module_instance(mod) for mod in pipeline_state_dto.modules],
        connections=[convert_dto_to_connection(conn) for conn in pipeline_state_dto.connections]
    )


def convert_dto_to_visual_state(visual_state_dto: VisualStateDTO) -> VisualStateDomain:
    """Convert API VisualStateDTO to domain VisualState"""
    return VisualStateDomain(
        modules={
            key: (pos.x, pos.y)
            for key, pos in visual_state_dto.modules.items()
        },
        entry_points={
            key: (pos.x, pos.y)
            for key, pos in visual_state_dto.entry_points.items()
        }
    )


def convert_create_request(request: CreatePipelineRequest) -> PipelineDefinitionCreate:
    """Convert API CreatePipelineRequest to domain PipelineDefinitionCreate"""
    return PipelineDefinitionCreate(
        pipeline_state=convert_dto_to_pipeline_state(request.pipeline_state),
        visual_state=convert_dto_to_visual_state(request.visual_state)
    )
