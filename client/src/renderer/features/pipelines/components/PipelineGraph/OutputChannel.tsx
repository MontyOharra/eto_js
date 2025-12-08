import { Module } from "./Module";
import { ModuleInstance, OutputChannelInstance } from "../../types";
import { createOutputChannelTemplate } from "../../utils/moduleFactory";
import { OutputChannelType } from "../../../modules/types";


export interface OutputChannelProps {
  data: {
    // Core data (always required)
    outputChannel: OutputChannelInstance;
    channelDefinition: OutputChannelType;

    onHandleClick?: (
      nodeId: string,
      handleId: string,
      handleType: "source" | "target"
    ) => void;

    // Edit callbacks
    onDeleteOutputChannel?: (outputChannelId: string) => void;

    // Connected output name for inputs
    getConnectedOutputName?: (inputNodeId: string) => string | undefined;

    // Interaction callbacks (optional)
    onModuleMouseEnter?: (moduleId: string) => void;
    onModuleMouseLeave?: () => void;
  };
}

// ============================================================================
// OutputChannel Component
// ============================================================================

export function OutputChannel({ data }: OutputChannelProps) {
  const {
    outputChannel,
    channelDefinition,
    onHandleClick,
    onDeleteOutputChannel,
    getConnectedOutputName,
    onModuleMouseEnter,
    onModuleMouseLeave,
  } = data;

  // Generate template for this specific channel type
  const template = createOutputChannelTemplate(
    channelDefinition.name,
    channelDefinition.label,
    channelDefinition.data_type
  );

  // Create synthetic ModuleInstance from OutputChannelInstance
  const moduleInstance: ModuleInstance = {
    module_instance_id: outputChannel.output_channel_instance_id,
    module_ref: `output_channel_${channelDefinition.name}:1.0.0`,
    config: {},
    inputs: outputChannel.inputs,
    outputs: [], // Output channels have no outputs
  };

  // Pass through to Module component with synthetic data
  return (
    <Module
      data={{
        moduleInstance,
        template,
        onHandleClick,
        // Pass through interaction callbacks
        onModuleMouseEnter,
        onModuleMouseLeave,
        // Delete callback - wrap to use output channel ID
        onDeleteModule: onDeleteOutputChannel
          ? () => onDeleteOutputChannel(outputChannel.output_channel_instance_id)
          : undefined,
        // Connected output name for inputs
        getConnectedOutputName,
        // No add/remove nodes or config for output channels
      }}
    />
  );
}
