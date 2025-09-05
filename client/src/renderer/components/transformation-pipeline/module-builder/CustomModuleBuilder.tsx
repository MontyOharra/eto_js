import React, { useState } from 'react';
import { BaseModuleTemplate } from '../../../types/modules';
import { useTransformationModules } from '../../../hooks/useTransformationModules';
import { InputOutputDesigner } from './InputOutputDesigner';
import { ModuleTestMode } from './ModuleTestMode';
import { TransformationGraph } from '../TransformationGraph';
import { InputDefiner, OutputDefiner, IODefinerTemplate } from '../../../types/inputOutputDefiners';

interface CustomModuleBuilderProps {
  moduleId: string | null; // null for new module, string for editing
  onClose: () => void;
  onSave: () => void;
}

interface ModuleBuilderTab {
  id: 'design' | 'inputs' | 'outputs' | 'test';
  label: string;
  icon: JSX.Element;
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

export const CustomModuleBuilder: React.FC<CustomModuleBuilderProps> = ({
  moduleId,
  onClose,
  onSave
}) => {
  const isEditing = moduleId !== null;
  const [activeTab, setActiveTab] = useState<'design' | 'inputs' | 'outputs' | 'test'>('design');
  const [moduleName, setModuleName] = useState('');
  const [moduleDescription, setModuleDescription] = useState('');
  const [inputFields, setInputFields] = useState<InputField[]>([]);
  const [outputFields, setOutputFields] = useState<OutputField[]>([]);
  const [inputDefiners, setInputDefiners] = useState<InputDefiner[]>([]);
  const [outputDefiners, setOutputDefiners] = useState<OutputDefiner[]>([]);
  
  const { modules, isLoading } = useTransformationModules();

  const tabs: ModuleBuilderTab[] = [
    {
      id: 'design',
      label: 'Design',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      )
    },
    {
      id: 'inputs',
      label: 'Inputs',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
        </svg>
      )
    },
    {
      id: 'outputs',
      label: 'Outputs',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16l4-4m0 0l-4-4m4 4H3m5-4v1a3 3 0 003 3h7a3 3 0 003-3V7a3 3 0 00-3-3h-7a3 3 0 00-3 3v1" />
        </svg>
      )
    },
    {
      id: 'test',
      label: 'Test',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1.586a1 1 0 01.707.293L12 11l.707-.707A1 1 0 0113.414 10H15m-6 5a2 2 0 002 2h2a2 2 0 002-2m-6 0a2 2 0 01-2-2V6a2 2 0 012-2h6a2 2 0 012 2v7a2 2 0 01-2 2m-6 0h6" />
        </svg>
      )
    }
  ];

  const ioDefinerTemplates: IODefinerTemplate[] = [
    { id: 'input_definer', name: 'Input Definer', type: 'input', color: '#3B82F6', icon: 'input' },
    { id: 'output_definer', name: 'Output Definer', type: 'output', color: '#10B981', icon: 'output' }
  ];


  const renderDesignTab = () => (
    <div className="flex h-full">
      {/* Module Palette */}
      <div className="w-80 bg-gray-800 border-r border-gray-700 flex flex-col">
        <div className="p-4 border-b border-gray-700">
          <h3 className="text-lg font-medium text-white mb-2">Components</h3>
          <input
            type="text"
            placeholder="Search..."
            className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-400 text-sm"
          />
        </div>
        
        <div className="flex-1 overflow-y-auto">
          {/* IO Definers Section */}
          <div className="p-4 border-b border-gray-700">
            <h4 className="text-sm font-medium text-gray-400 mb-3 uppercase tracking-wide">Input/Output Definers</h4>
            <div className="space-y-2">
              {ioDefinerTemplates.map(template => (
                <div
                  key={template.id}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData('text/plain', JSON.stringify({ type: template.type + '_definer', ...template }));
                  }}
                  className="bg-gray-900 rounded-lg p-3 cursor-move hover:bg-gray-700 transition-colors border border-gray-600"
                >
                  <div className="flex items-center space-x-2">
                    <div 
                      className="w-3 h-3 rounded-full flex-shrink-0"
                      style={{ backgroundColor: template.color }}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-white text-sm font-medium truncate">{template.name}</p>
                      <p className="text-gray-400 text-xs">Define custom {template.type}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Modules Section */}
          <div className="p-4">
            <h4 className="text-sm font-medium text-gray-400 mb-3 uppercase tracking-wide">Processing Modules</h4>
            {isLoading ? (
              <div className="text-center py-8">
                <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-2"></div>
                <p className="text-gray-400 text-sm">Loading modules...</p>
              </div>
            ) : (
              <div className="space-y-2">
                {modules.map(module => (
                  <div
                    key={module.id}
                    draggable
                    onDragStart={(e) => {
                      e.dataTransfer.setData('application/json', JSON.stringify(module));
                    }}
                    className="bg-gray-900 rounded-lg p-3 cursor-move hover:bg-gray-700 transition-colors border border-gray-600"
                  >
                    <div className="flex items-center space-x-2">
                      <div 
                        className="w-3 h-3 rounded-full flex-shrink-0"
                        style={{ backgroundColor: module.color }}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-white text-sm font-medium truncate">{module.name}</p>
                        <p className="text-gray-400 text-xs truncate">{module.category}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* Transformation Graph */}
      <TransformationGraph
        modules={modules}
        selectedModuleTemplate={null}
        onModuleSelect={() => {}}
        enableInputOutputDefiners={true}
        inputDefiners={inputDefiners}
        outputDefiners={outputDefiners}
        onInputDefinersChange={setInputDefiners}
        onOutputDefinersChange={setOutputDefiners}
      />
    </div>
  );

  const renderInputsTab = () => (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">
        <InputOutputDesigner
          type="input"
          fields={inputFields}
          onChange={(fields) => setInputFields(fields as InputField[])}
        />
      </div>
    </div>
  );

  const renderOutputsTab = () => (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">
        <InputOutputDesigner
          type="output"
          fields={outputFields}
          onChange={(fields) => setOutputFields(fields as OutputField[])}
        />
      </div>
    </div>
  );

  const renderTestTab = () => (
    <div className="p-6">
      <div className="max-w-6xl mx-auto">
        <ModuleTestMode
          inputFields={inputFields}
          outputFields={outputFields}
          moduleName={moduleName}
        />
      </div>
    </div>
  );

  const renderTabContent = () => {
    switch (activeTab) {
      case 'design':
        return renderDesignTab();
      case 'inputs':
        return renderInputsTab();
      case 'outputs':
        return renderOutputsTab();
      case 'test':
        return renderTestTab();
      default:
        return renderDesignTab();
    }
  };

  return (
    <div className="h-full bg-gray-900 text-white flex flex-col">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-3 flex-shrink-0">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-4">
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white p-1 rounded transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>
            <div>
              <h1 className="text-lg font-semibold text-white">
                {isEditing ? 'Edit Custom Module' : 'Create Custom Module'}
              </h1>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={onClose}
              className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg transition-colors text-sm"
            >
              Cancel
            </button>
            <button
              onClick={onSave}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors text-sm"
            >
              {isEditing ? 'Update Module' : 'Save Module'}
            </button>
          </div>
        </div>
        
        {/* Module Info */}
        <div className="grid grid-cols-2 gap-4 mb-3">
          <input
            type="text"
            placeholder="Module Name"
            value={moduleName}
            onChange={(e) => setModuleName(e.target.value)}
            className="bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-400 text-sm"
          />
          <input
            type="text"
            placeholder="Module Description"
            value={moduleDescription}
            onChange={(e) => setModuleDescription(e.target.value)}
            className="bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-400 text-sm"
          />
        </div>
        
        {/* Tabs */}
        <div className="flex space-x-1">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg transition-colors text-sm ${
                activeTab === tab.id
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700'
              }`}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden">
        {renderTabContent()}
      </div>
    </div>
  );
};