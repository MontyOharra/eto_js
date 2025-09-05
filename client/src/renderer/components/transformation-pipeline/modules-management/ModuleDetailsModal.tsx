import React from 'react';
import { BaseModuleTemplate } from '../../../types/modules';

interface ModuleDetailsModalProps {
  module: BaseModuleTemplate;
  onClose: () => void;
}

export const ModuleDetailsModal: React.FC<ModuleDetailsModalProps> = ({
  module,
  onClose
}) => {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col">
        {/* Header - Fixed */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700 flex-shrink-0">
          <div className="flex items-center">
            <div 
              className="w-6 h-6 rounded-full flex-shrink-0"
              style={{ backgroundColor: module.color }}
            />
            <div className="ml-3">
              <h2 className="text-xl font-semibold text-white">{module.name}</h2>
              <p className="text-sm text-gray-400">{module.category}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white p-2 rounded-lg hover:bg-gray-700 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content - Scrollable */}
        <div className="p-6 space-y-6 flex-1 overflow-y-auto min-h-0">
          {/* Description */}
          <div>
            <h3 className="text-lg font-medium text-white mb-2">Description</h3>
            <p className="text-gray-300 leading-relaxed">{module.description}</p>
          </div>

          {/* Inputs Section */}
          {module.inputs.length > 0 && (
            <div>
              <h3 className="text-lg font-medium text-white mb-3">
                Inputs ({module.inputs.length})
              </h3>
              <div className="space-y-3">
                {module.inputs.map((input, index) => (
                  <div key={index} className="bg-gray-900 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium text-white">{input.name}</h4>
                      <div className="flex items-center space-x-2">
                        <span className={`text-xs px-2 py-1 rounded ${
                          input.required ? 'bg-red-900 text-red-300' : 'bg-gray-700 text-gray-300'
                        }`}>
                          {input.required ? 'Required' : 'Optional'}
                        </span>
                        <span className="text-xs bg-blue-900 text-blue-300 px-2 py-1 rounded capitalize">
                          {input.type}
                        </span>
                      </div>
                    </div>
                    <p className="text-sm text-gray-400">{input.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Outputs Section */}
          {module.outputs.length > 0 && (
            <div>
              <h3 className="text-lg font-medium text-white mb-3">
                Outputs ({module.outputs.length})
              </h3>
              <div className="space-y-3">
                {module.outputs.map((output, index) => (
                  <div key={index} className="bg-gray-900 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium text-white">{output.name}</h4>
                      <span className="text-xs bg-green-900 text-green-300 px-2 py-1 rounded capitalize">
                        {output.type}
                      </span>
                    </div>
                    <p className="text-sm text-gray-400">{output.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Configuration Section */}
          {module.config && module.config.length > 0 && (
            <div>
              <h3 className="text-lg font-medium text-white mb-3">
                Configuration ({module.config.length})
              </h3>
              <div className="space-y-3">
                {module.config.map((config, index) => (
                  <div key={index} className="bg-gray-900 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium text-white">{config.name || config.description}</h4>
                      <div className="flex items-center space-x-2">
                        {config.required && (
                          <span className="text-xs bg-red-900 text-red-300 px-2 py-1 rounded">
                            Required
                          </span>
                        )}
                        <span className="text-xs bg-purple-900 text-purple-300 px-2 py-1 rounded capitalize">
                          {config.type}
                        </span>
                      </div>
                    </div>
                    <p className="text-sm text-gray-400 mb-2">{config.description}</p>
                    {config.defaultValue !== undefined && (
                      <p className="text-xs text-gray-500">
                        Default: <span className="text-gray-300">{String(config.defaultValue)}</span>
                      </p>
                    )}
                    {config.options && (
                      <p className="text-xs text-gray-500">
                        Options: <span className="text-gray-300">{config.options.join(', ')}</span>
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Dynamic Features */}
          {(module.dynamicInputs?.enabled || module.dynamicOutputs?.enabled) && (
            <div>
              <h3 className="text-lg font-medium text-white mb-3">Dynamic Features</h3>
              <div className="bg-gray-900 rounded-lg p-4">
                {module.dynamicInputs?.enabled && (
                  <div className="mb-3 last:mb-0">
                    <h4 className="font-medium text-green-400 mb-1">Dynamic Inputs</h4>
                    <p className="text-sm text-gray-400">
                      Min: {module.dynamicInputs.minNodes || 0}, 
                      Max: {module.dynamicInputs.maxNodes || 'Unlimited'}
                      {module.dynamicInputs.allowTypeConfiguration && ' • Configurable Types'}
                    </p>
                  </div>
                )}
                {module.dynamicOutputs?.enabled && (
                  <div>
                    <h4 className="font-medium text-green-400 mb-1">Dynamic Outputs</h4>
                    <p className="text-sm text-gray-400">
                      Min: {module.dynamicOutputs.minNodes || 0}, 
                      Max: {module.dynamicOutputs.maxNodes || 'Unlimited'}
                      {module.dynamicOutputs.allowTypeConfiguration && ' • Configurable Types'}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer - Fixed */}
        <div className="p-6 border-t border-gray-700 flex justify-end flex-shrink-0">
          <button
            onClick={onClose}
            className="bg-gray-600 hover:bg-gray-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};