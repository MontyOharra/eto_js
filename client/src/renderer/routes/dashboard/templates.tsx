import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { TemplatesList } from "../../components/template/TemplatesList";
import { TemplateBuilderModal } from "../../components/template/TemplateBuilderModal";
import { TemplateViewerModal } from "../../components/template/TemplateViewerModal";
import { useTemplates, useServerHealth } from "../../hooks/useApi";
import { TemplateSummary } from "../../types/eto";
import { apiClient } from "../../services/api";

export const Route = createFileRoute("/dashboard/templates")({
  component: TemplatesPage,
});

function TemplatesPage() {
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [buildingTemplateForRun, setBuildingTemplateForRun] = useState<string | null>(null);
  const [viewingTemplateId, setViewingTemplateId] = useState<number | null>(null);
  const [reprocessing, setReprocessing] = useState(false);
  
  // Fetch templates data from API
  const { data: templates, loading, error, refetch } = useTemplates({ 
    status: statusFilter === "all" ? undefined : statusFilter,
    limit: 50,
    autoRefresh: true,
    refreshInterval: 60000
  });
  const { isServerOnline } = useServerHealth();

  const handleEdit = (template: TemplateSummary) => {
    console.log("Edit template:", template);
    // TODO: Navigate to template editor
  };

  const handleView = (template: TemplateSummary) => {
    console.log("View template:", template);
    setViewingTemplateId(template.id);
  };

  const handleDelete = (template: TemplateSummary) => {
    console.log("Delete template:", template);
    // TODO: Show confirmation dialog
  };

  const handleCreateTemplate = () => {
    console.log("Create new template - need to select ETO run first");
    // TODO: Show ETO run selection dialog or navigate to ETO runs page
  };

  const handleTemplateBuilderSave = (templateData: any) => {
    console.log("Template saved successfully:", templateData);
    setBuildingTemplateForRun(null);
    // Refresh the templates list to show the new template
    refetch();
  };

  const handleTemplateBuilderClose = () => {
    setBuildingTemplateForRun(null);
  };

  const handleTemplateViewerClose = () => {
    setViewingTemplateId(null);
  };

  const handleReprocessUnrecognized = async () => {
    setReprocessing(true);
    try {
      const result = await apiClient.triggerReprocessing();
      console.log('Reprocessing result:', result);
      
      if (result.success && result.result.reprocessed > 0) {
        alert(`Successfully triggered reprocessing of ${result.result.reprocessed} unrecognized PDFs.`);
      } else if (result.success) {
        alert('No unrecognized PDFs found to reprocess.');
      } else {
        alert(`Reprocessing failed: ${result.result.error || 'Unknown error'}`);
      }
    } catch (err: any) {
      console.error('Error triggering reprocessing:', err);
      alert(`Failed to trigger reprocessing: ${err.message || 'Unknown error'}`);
    } finally {
      setReprocessing(false);
    }
  };

  // Show loading state
  if (loading && !templates) {
    return (
      <div className="flex-1 p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-blue-300 mb-2">Templates</h1>
          <p className="text-gray-400">Manage your PDF extraction templates</p>
        </div>
        
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400 mx-auto mb-4"></div>
            <p className="text-gray-400">Loading templates...</p>
          </div>
        </div>
      </div>
    );
  }

  // Show error state
  if (error && !templates) {
    return (
      <div className="flex-1 p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-blue-300 mb-2">Templates</h1>
          <p className="text-gray-400">Manage your PDF extraction templates</p>
        </div>
        
        <div className="bg-red-900/20 border border-red-700 rounded-lg p-6">
          <div className="flex items-center">
            <svg className="w-6 h-6 text-red-400 mr-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <div>
              <h3 className="text-red-400 font-medium">Failed to load templates</h3>
              <p className="text-gray-400 text-sm mt-1">{error}</p>
            </div>
          </div>
          <button 
            onClick={refetch}
            className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded text-sm font-medium transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 p-6">
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-blue-300 mb-2">Templates</h1>
            <p className="text-gray-400">Manage your PDF extraction templates</p>
          </div>
          
          <div className="flex items-center space-x-4">
            {/* Server status indicator */}
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${isServerOnline ? 'bg-green-400' : 'bg-red-400'}`}></div>
              <span className={`text-sm ${isServerOnline ? 'text-green-400' : 'text-red-400'}`}>
                {isServerOnline ? 'Server Online' : 'Server Offline'}
              </span>
            </div>
            
            {/* Reprocess button */}
            <button 
              onClick={handleReprocessUnrecognized}
              disabled={reprocessing || !isServerOnline}
              className="px-3 py-1 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 text-white text-sm rounded transition-colors"
              title="Reprocess all unrecognized PDFs with current templates"
            >
              {reprocessing ? 'Reprocessing...' : 'Reprocess Unrecognized'}
            </button>
            
            {/* Refresh button */}
            <button 
              onClick={refetch}
              disabled={loading}
              className="px-3 py-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white text-sm rounded transition-colors"
            >
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
        </div>
        
        {/* Data freshness indicator */}
        {templates && (
          <p className="text-xs text-gray-500 mt-2">
            Showing {templates.length} templates • Auto-refreshing every minute
          </p>
        )}
      </div>

      <TemplatesList
        templates={templates || []}
        onEdit={handleEdit}
        onView={handleView}
        onDelete={handleDelete}
        onCreateTemplate={handleCreateTemplate}
      />
      
      {/* Template Builder Modal */}
      <TemplateBuilderModal
        runId={buildingTemplateForRun}
        onClose={handleTemplateBuilderClose}
        onSave={handleTemplateBuilderSave}
      />
      
      {/* Template Viewer Modal */}
      <TemplateViewerModal
        templateId={viewingTemplateId}
        onClose={handleTemplateViewerClose}
      />
    </div>
  );
}
