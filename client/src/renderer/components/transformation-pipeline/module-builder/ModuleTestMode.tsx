import React, { useState, useCallback } from 'react';

interface TestInput {
  fieldId: string;
  fieldName: string;
  fieldType: string;
  value: any;
  required: boolean;
}

interface TestOutput {
  fieldId: string;
  fieldName: string;
  fieldType: string;
  value: any;
}

interface InputField {
  id: string;
  name: string;
  type: 'string' | 'number' | 'boolean' | 'array' | 'object';
  description: string;
  required: boolean;
  defaultValue?: any;
}

interface OutputField {
  id: string;
  name: string;
  type: 'string' | 'number' | 'boolean' | 'array' | 'object';
  description: string;
}

interface ModuleTestModeProps {
  inputFields: InputField[];
  outputFields: OutputField[];
  moduleName: string;
}

export const ModuleTestMode: React.FC<ModuleTestModeProps> = ({
  inputFields,
  outputFields,
  moduleName
}) => {
  const [testInputs, setTestInputs] = useState<TestInput[]>(
    inputFields.map(field => ({
      fieldId: field.id,
      fieldName: field.name,
      fieldType: field.type,
      value: field.defaultValue || getDefaultValueForType(field.type),
      required: field.required
    }))
  );

  const [testOutputs, setTestOutputs] = useState<TestOutput[]>(
    outputFields.map(field => ({
      fieldId: field.id,
      fieldName: field.name,
      fieldType: field.type,
      value: null
    }))
  );

  const [isRunning, setIsRunning] = useState(false);
  const [executionLog, setExecutionLog] = useState<string[]>([]);

  function getDefaultValueForType(type: string): any {
    switch (type) {
      case 'string': return '';
      case 'number': return 0;
      case 'boolean': return false;
      case 'array': return [];
      case 'object': return {};
      default: return '';
    }
  }

  const handleInputChange = (fieldId: string, value: any) => {
    setTestInputs(prev => prev.map(input => 
      input.fieldId === fieldId ? { ...input, value } : input
    ));
  };

  const parseInputValue = (value: string, type: string): any => {
    try {
      switch (type) {
        case 'number':
          return parseFloat(value) || 0;
        case 'boolean':
          return value.toLowerCase() === 'true' || value === '1';
        case 'array':
        case 'object':
          return value ? JSON.parse(value) : (type === 'array' ? [] : {});
        default:
          return value;
      }
    } catch {
      return type === 'array' ? [] : type === 'object' ? {} : value;
    }
  };

  const formatOutputValue = (value: any, type: string): string => {
    if (value === null || value === undefined) {
      return 'null';
    }
    
    if (type === 'object' || type === 'array') {
      return JSON.stringify(value, null, 2);
    }
    
    return String(value);
  };

  const simulateModuleExecution = useCallback(async () => {
    setIsRunning(true);
    setExecutionLog(['🚀 Starting module execution...']);
    
    // Simulate execution delay
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Validate required inputs
    const missingInputs = testInputs.filter(input => 
      input.required && (input.value === '' || input.value === null || input.value === undefined)
    );
    
    if (missingInputs.length > 0) {
      setExecutionLog(prev => [...prev, 
        '❌ Missing required inputs:', 
        ...missingInputs.map(input => `  - ${input.fieldName}`)
      ]);
      setIsRunning(false);
      return;
    }
    
    setExecutionLog(prev => [...prev, '✓ All required inputs provided']);
    setExecutionLog(prev => [...prev, '🔄 Processing data through pipeline...']);
    
    // Simulate processing delay
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Generate mock output values
    const mockOutputs = testOutputs.map(output => {
      let mockValue;
      
      switch (output.fieldType) {
        case 'string':
          mockValue = `Processed result for ${output.fieldName}`;
          break;
        case 'number':
          mockValue = Math.round(Math.random() * 100);
          break;
        case 'boolean':
          mockValue = Math.random() > 0.5;
          break;
        case 'array':
          mockValue = [`item1_${output.fieldName}`, `item2_${output.fieldName}`];
          break;
        case 'object':
          mockValue = { 
            processed: true, 
            fieldName: output.fieldName,
            timestamp: new Date().toISOString()
          };
          break;
        default:
          mockValue = 'Mock result';
      }
      
      return { ...output, value: mockValue };
    });
    
    setTestOutputs(mockOutputs);
    setExecutionLog(prev => [...prev, '✅ Module execution completed successfully']);
    setIsRunning(false);
  }, [testInputs, testOutputs]);

  const clearResults = () => {
    setTestOutputs(prev => prev.map(output => ({ ...output, value: null })));
    setExecutionLog([]);
  };

  if (inputFields.length === 0 && outputFields.length === 0) {
    return (
      <div className="text-center py-16">
        <svg className="w-16 h-16 text-gray-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
        <h3 className="text-lg font-medium text-white mb-2">No Fields to Test</h3>
        <p className="text-gray-400 max-w-md mx-auto">
          Define input and output fields in the previous tabs to enable module testing.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium text-white mb-2">Test Custom Module</h3>
          <p className="text-gray-400 text-sm">
            Test your custom module "{moduleName || 'Untitled Module'}" with sample inputs to verify outputs
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={clearResults}
            disabled={isRunning}
            className="text-gray-400 hover:text-white px-3 py-2 rounded-lg transition-colors disabled:opacity-50"
          >
            Clear Results
          </button>
          <button
            onClick={simulateModuleExecution}
            disabled={isRunning}
            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {isRunning ? (
              <>
                <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                Running...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1.586a1 1 0 01.707.293L12 11l.707-.707A1 1 0 0113.414 10H15m-6 5a2 2 0 002 2h2a2 2 0 002-2m-6 0a2 2 0 01-2-2V6a2 2 0 012-2h6a2 2 0 012 2v7a2 2 0 01-2 2m-6 0h6" />
                </svg>
                Run Test
              </>
            )}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Panel */}
        {inputFields.length > 0 && (
          <div className="bg-gray-800 rounded-lg p-6">
            <h4 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
              </svg>
              Test Inputs ({inputFields.length})
            </h4>
            
            <div className="space-y-4">
              {testInputs.map((input, index) => (
                <div key={input.fieldId} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium text-white">
                      {input.fieldName}
                      {input.required && <span className="text-red-400 ml-1">*</span>}
                    </label>
                    <span className="text-xs text-gray-400 capitalize">{input.fieldType}</span>
                  </div>
                  
                  {input.fieldType === 'boolean' ? (
                    <select
                      value={input.value.toString()}
                      onChange={(e) => handleInputChange(input.fieldId, e.target.value === 'true')}
                      className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white"
                    >
                      <option value="false">False</option>
                      <option value="true">True</option>
                    </select>
                  ) : input.fieldType === 'array' || input.fieldType === 'object' ? (
                    <textarea
                      value={typeof input.value === 'string' ? input.value : JSON.stringify(input.value, null, 2)}
                      onChange={(e) => handleInputChange(input.fieldId, parseInputValue(e.target.value, input.fieldType))}
                      className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white font-mono text-sm"
                      rows={3}
                      placeholder={input.fieldType === 'array' ? '[]' : '{}'}
                    />
                  ) : (
                    <input
                      type={input.fieldType === 'number' ? 'number' : 'text'}
                      value={input.value}
                      onChange={(e) => handleInputChange(input.fieldId, parseInputValue(e.target.value, input.fieldType))}
                      className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white"
                      placeholder={`Enter ${input.fieldType} value`}
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Output Panel */}
        {outputFields.length > 0 && (
          <div className="bg-gray-800 rounded-lg p-6">
            <h4 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16l4-4m0 0l-4-4m4 4H3m5-4v1a3 3 0 003 3h7a3 3 0 003-3V7a3 3 0 00-3-3h-7a3 3 0 00-3 3v1" />
              </svg>
              Test Outputs ({outputFields.length})
            </h4>
            
            <div className="space-y-4">
              {testOutputs.map((output) => (
                <div key={output.fieldId} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium text-white">{output.fieldName}</label>
                    <span className="text-xs text-gray-400 capitalize">{output.fieldType}</span>
                  </div>
                  
                  <div className="bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 min-h-[42px] flex items-center">
                    {output.value !== null ? (
                      <pre className="text-white text-sm font-mono whitespace-pre-wrap">
                        {formatOutputValue(output.value, output.fieldType)}
                      </pre>
                    ) : (
                      <span className="text-gray-500 italic text-sm">No output generated</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Execution Log */}
      {executionLog.length > 0 && (
        <div className="bg-gray-800 rounded-lg p-6">
          <h4 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
            <svg className="w-5 h-5 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Execution Log
          </h4>
          
          <div className="bg-gray-900 rounded-lg p-4 max-h-48 overflow-y-auto">
            <div className="space-y-1 font-mono text-sm">
              {executionLog.map((log, index) => (
                <div key={index} className="text-gray-300">
                  <span className="text-gray-500">[{new Date().toLocaleTimeString()}]</span> {log}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};