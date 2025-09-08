import React, { useState } from 'react';

interface InputDefinition {
  id: string;
  name: string;
  nodes: {
    outputs: Array<{
      id: string;
      name: string;
      type: string;
      description: string;
      required: boolean;
    }>;
  };
}

interface InputCollectionModalProps {
  isOpen: boolean;
  inputDefinitions: InputDefinition[];
  onSubmit: (inputData: Record<string, any>) => void;
  onCancel: () => void;
}

export const InputCollectionModal: React.FC<InputCollectionModalProps> = ({
  isOpen,
  inputDefinitions,
  onSubmit,
  onCancel
}) => {
  const [inputValues, setInputValues] = useState<Record<string, string>>({});

  if (!isOpen) return null;

  const handleInputChange = (nodeId: string, value: string) => {
    setInputValues(prev => ({
      ...prev,
      [nodeId]: value
    }));
  };

  const handleSubmit = () => {
    // Convert input values to the expected format (node IDs)
    const inputData: Record<string, any> = {};
    
    inputDefinitions.forEach(inputDef => {
      // For each input definition, create node ID based on output index
      inputDef.nodes.outputs.forEach((output, outputIndex) => {
        const nodeId = `${inputDef.id}_output_${outputIndex}`;
        const value = inputValues[nodeId] || '';
        
        // Convert based on type
        switch (output.type) {
          case 'number':
            inputData[nodeId] = value ? parseFloat(value) : 0;
            break;
          case 'boolean':
            inputData[nodeId] = value === 'true';
            break;
          default:
            inputData[nodeId] = value;
        }
      });
    });
    
    onSubmit(inputData);
  };

  const handleCancel = () => {
    setInputValues({});
    onCancel();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black bg-opacity-50"
        onClick={handleCancel}
      />
      
      {/* Modal */}
      <div className="relative bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-2xl max-h-[80vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-semibold text-white">
            Pipeline Input Data
          </h2>
          <button
            onClick={handleCancel}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <div className="space-y-6">
          <p className="text-gray-300 text-sm">
            Please provide input values for your pipeline execution:
          </p>
          
          {inputDefinitions.map(inputDef => (
            <div key={inputDef.id} className="border border-gray-600 rounded-lg p-4">
              <h3 className="text-lg font-medium text-white mb-3">
                {inputDef.name}
              </h3>
              
              {inputDef.nodes.outputs.map((output, outputIndex) => {
                const nodeId = `${inputDef.id}_output_${outputIndex}`;
                
                return (
                  <div key={nodeId} className="mb-4">
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      {output.name}
                      {output.required && <span className="text-red-400 ml-1">*</span>}
                    </label>
                    
                    <div className="text-xs text-gray-400 mb-2">
                      {output.description}
                    </div>
                    
                    {output.type === 'boolean' ? (
                      <select
                        value={inputValues[nodeId] || 'false'}
                        onChange={(e) => handleInputChange(nodeId, e.target.value)}
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:border-blue-500"
                      >
                        <option value="false">False</option>
                        <option value="true">True</option>
                      </select>
                    ) : (
                      <input
                        type={output.type === 'number' ? 'number' : 'text'}
                        value={inputValues[nodeId] || ''}
                        onChange={(e) => handleInputChange(nodeId, e.target.value)}
                        placeholder={`Enter ${output.name.toLowerCase()}...`}
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
                        required={output.required}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
        
        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={handleCancel}
            className="px-4 py-2 border border-gray-600 text-gray-300 rounded-lg hover:bg-gray-700 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            Execute Pipeline
          </button>
        </div>
      </div>
    </div>
  );
};