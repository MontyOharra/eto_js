import { useState } from "react";
import { Handle, Position } from "@xyflow/react";

interface NodeIO {
  id: string;
  name: string;
  type: string;
}

interface ModuleNodeProps {
  data: {
    label: string;
    inputs?: NodeIO[];
    outputs?: NodeIO[];
  };
}

// Type to color mapping
const TYPE_COLORS: Record<string, string> = {
  str: "#3B82F6", // blue-500
  int: "#EF4444", // red-500
  float: "#F59E0B", // orange-500
  bool: "#10B981", // green-500
  datetime: "#8B5CF6", // purple-500
};

const AVAILABLE_TYPES = ["str", "int", "float", "bool", "datetime"];

export function ModuleNode({ data }: ModuleNodeProps) {
  const [inputs, setInputs] = useState<NodeIO[]>(
    data.inputs || [
      { id: "input-1", name: "Input 1", type: "str" },
      { id: "input-2", name: "Input 2", type: "str" },
    ]
  );

  const [outputs, setOutputs] = useState<NodeIO[]>(
    data.outputs || [
      { id: "output-1", name: "Output 1", type: "str" },
      { id: "output-2", name: "Output 2", type: "str" },
    ]
  );

  const [isConfigExpanded, setIsConfigExpanded] = useState(false);
  const [configOption1, setConfigOption1] = useState("option-a");
  const [configOption2, setConfigOption2] = useState("choice-1");
  const [configText, setConfigText] = useState("");

  const handleInputNameChange = (id: string, newName: string) => {
    setInputs((prev) =>
      prev.map((input) => (input.id === id ? { ...input, name: newName } : input))
    );
  };

  const handleInputTypeChange = (id: string, newType: string) => {
    setInputs((prev) =>
      prev.map((input) => (input.id === id ? { ...input, type: newType } : input))
    );
  };

  const handleOutputNameChange = (id: string, newName: string) => {
    setOutputs((prev) =>
      prev.map((output) => (output.id === id ? { ...output, name: newName } : output))
    );
  };

  const handleOutputTypeChange = (id: string, newType: string) => {
    setOutputs((prev) =>
      prev.map((output) => (output.id === id ? { ...output, type: newType } : output))
    );
  };

  return (
    <div className="bg-gray-800 rounded-lg border-2 border-gray-600 min-w-[320px]">
      {/* Header */}
      <div className="bg-gray-700 px-3 py-2 rounded-t-lg border-b border-gray-600">
        <div className="text-white font-medium text-sm">{data.label}</div>
      </div>

      {/* Body with inputs and outputs side by side */}
      <div className="flex">
        {/* Inputs Section */}
        <div className="flex-1 p-3 border-r border-gray-600">
          <div className="text-[10px] text-gray-400 uppercase font-semibold mb-2">
            Inputs
          </div>
          <div className="space-y-2">
            {inputs.map((input) => (
              <div key={input.id} className="relative space-y-1">
                {/* Input Handle - positioned outside */}
                <Handle
                  type="target"
                  position={Position.Left}
                  id={input.id}
                  className="!w-3 !h-3 !border-2 !border-gray-900"
                  style={{
                    left: -8,
                    backgroundColor: TYPE_COLORS[input.type] || "#6B7280",
                  }}
                />
                {/* Name Input */}
                <input
                  type="text"
                  value={input.name}
                  onChange={(e) => handleInputNameChange(input.id, e.target.value)}
                  className="w-full text-xs bg-gray-700 text-gray-200 px-1 py-0.5 rounded border border-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="Name"
                />
                {/* Type Selector */}
                <select
                  value={input.type}
                  onChange={(e) => handleInputTypeChange(input.id, e.target.value)}
                  className="w-full text-[10px] bg-gray-700 text-gray-300 px-1 py-0.5 rounded border border-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  style={{
                    borderLeftColor: TYPE_COLORS[input.type] || "#6B7280",
                    borderLeftWidth: "3px",
                  }}
                >
                  {AVAILABLE_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        </div>

        {/* Outputs Section */}
        <div className="flex-1 p-3">
          <div className="text-[10px] text-gray-400 uppercase font-semibold mb-2 text-right">
            Outputs
          </div>
          <div className="space-y-2">
            {outputs.map((output) => (
              <div key={output.id} className="relative space-y-1">
                {/* Output Handle - positioned outside */}
                <Handle
                  type="source"
                  position={Position.Right}
                  id={output.id}
                  className="!w-3 !h-3 !border-2 !border-gray-900"
                  style={{
                    right: -8,
                    backgroundColor: TYPE_COLORS[output.type] || "#6B7280",
                  }}
                />
                {/* Name Input */}
                <input
                  type="text"
                  value={output.name}
                  onChange={(e) => handleOutputNameChange(output.id, e.target.value)}
                  className="w-full text-xs bg-gray-700 text-gray-200 px-1 py-0.5 rounded border border-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500 text-right"
                  placeholder="Name"
                />
                {/* Type Selector */}
                <select
                  value={output.type}
                  onChange={(e) => handleOutputTypeChange(output.id, e.target.value)}
                  className="w-full text-[10px] bg-gray-700 text-gray-300 px-1 py-0.5 rounded border border-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500 text-right"
                  style={{
                    borderRightColor: TYPE_COLORS[output.type] || "#6B7280",
                    borderRightWidth: "3px",
                  }}
                >
                  {AVAILABLE_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Collapsible Configuration Section */}
      <div className="border-t border-gray-600">
        {/* Configuration Header */}
        <button
          onClick={() => setIsConfigExpanded(!isConfigExpanded)}
          className="w-full px-3 py-2 flex items-center justify-between hover:bg-gray-700 transition-colors"
        >
          <span className="text-[10px] text-gray-400 uppercase font-semibold">
            Configuration
          </span>
          <svg
            className={`w-4 h-4 text-gray-400 transition-transform ${
              isConfigExpanded ? "rotate-180" : ""
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>

        {/* Configuration Content */}
        {isConfigExpanded && (
          <div className="px-3 pb-3 space-y-2 bg-gray-750">
            {/* Dropdown 1 */}
            <div>
              <label className="text-[10px] text-gray-400 block mb-1">
                Option 1
              </label>
              <select
                value={configOption1}
                onChange={(e) => setConfigOption1(e.target.value)}
                className="w-full text-xs bg-gray-700 text-gray-200 px-2 py-1 rounded border border-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="option-a">Option A</option>
                <option value="option-b">Option B</option>
                <option value="option-c">Option C</option>
              </select>
            </div>

            {/* Dropdown 2 */}
            <div>
              <label className="text-[10px] text-gray-400 block mb-1">
                Option 2
              </label>
              <select
                value={configOption2}
                onChange={(e) => setConfigOption2(e.target.value)}
                className="w-full text-xs bg-gray-700 text-gray-200 px-2 py-1 rounded border border-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="choice-1">Choice 1</option>
                <option value="choice-2">Choice 2</option>
                <option value="choice-3">Choice 3</option>
              </select>
            </div>

            {/* Text Input */}
            <div>
              <label className="text-[10px] text-gray-400 block mb-1">
                Text Input
              </label>
              <input
                type="text"
                value={configText}
                onChange={(e) => setConfigText(e.target.value)}
                placeholder="Enter text..."
                className="w-full text-xs bg-gray-700 text-gray-200 px-2 py-1 rounded border border-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
