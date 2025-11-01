import { createFileRoute } from '@tanstack/react-router';
import { useState, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  useTemplates,
  useCreateTemplate,
  useUpdateTemplate,
  useActivateTemplate,
  useDeactivateTemplate,
} from '../../../features/templates';
import { usePipelinesApi } from '../../../features/pipelines/hooks/usePipelinesApi';
import { TemplateCard, TemplateBuilderModal, TemplateDetailModal, TemplateData } from '../../../features/templates/components';
import { TemplateListItem, TemplateStatus } from '../../../features/templates/types';

export const Route = createFileRoute('/dashboard/pdf-templates/')({
  component: TemplatesPage,
});

type SortBy = 'name' | 'status' | 'usage_count';
type SortOrder = 'asc' | 'desc';

function TemplatesPage() {
  // TanStack Query hooks
  const { data: allTemplates = [], isLoading, error } = useTemplates();
  const createTemplate = useCreateTemplate();
  const updateTemplate = useUpdateTemplate();
  const activateTemplate = useActivateTemplate();
  const deactivateTemplate = useDeactivateTemplate();

  const { getPipeline } = usePipelinesApi();
  const queryClient = useQueryClient();

  const [statusFilter, setStatusFilter] = useState<TemplateStatus | 'all'>('all');
  const [sortBy, setSortBy] = useState<SortBy>('name');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');

  // Template Builder Modal State
  const [isBuilderOpen, setIsBuilderOpen] = useState(false);
  const [builderMode, setBuilderMode] = useState<'create' | 'edit'>('create');
  const [builderTemplateId, setBuilderTemplateId] = useState<number | undefined>(undefined);
  const [builderInitialData, setBuilderInitialData] = useState<TemplateData | undefined>(undefined);
  const [builderPdfFileId, setBuilderPdfFileId] = useState<number | null>(null);
  const [builderPdfFile, setBuilderPdfFile] = useState<File | null>(null);

  // Template Detail Modal State
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [detailTemplateId, setDetailTemplateId] = useState<number | null>(null);

  // Filter and sort templates using useMemo
  const filteredTemplates = useMemo((): TemplateListItem[] => {
    // Filter by status
    let filtered =
      statusFilter === 'all'
        ? allTemplates
        : allTemplates.filter((t) => t.status === statusFilter);

    // Sort
    const sorted = [...filtered].sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (sortBy) {
        case 'name':
          aValue = a.name.toLowerCase();
          bValue = b.name.toLowerCase();
          break;
        case 'status':
          aValue = a.status;
          bValue = b.status;
          break;
        case 'usage_count':
          aValue = a.current_version.usage_count;
          bValue = b.current_version.usage_count;
          break;
        default:
          aValue = a.id;
          bValue = b.id;
      }

      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });

    return sorted;
  }, [allTemplates, statusFilter, sortBy, sortOrder]);

  // ==========================================================================
  // Button Handlers
  // ==========================================================================

  const handleView = (templateId: number) => {
    setDetailTemplateId(templateId);
    setIsDetailOpen(true);
  };

  const handleCloseDetail = () => {
    setIsDetailOpen(false);
    setDetailTemplateId(null);
  };

  const handleEditFromDetail = async (templateId: number) => {
    try {
      // Close detail modal
      setIsDetailOpen(false);
      setDetailTemplateId(null);

      // Fetch template detail and version detail using queryClient
      const templateDetail = await queryClient.fetchQuery({
        queryKey: ['template', templateId],
        staleTime: 0, // Force fresh fetch
      });

      if (!templateDetail.current_version_id) {
        alert('Cannot edit template: No current version found');
        return;
      }

      const [versionDetail, pipelineData] = await Promise.all([
        queryClient.fetchQuery({
          queryKey: ['template-version', templateDetail.current_version_id],
          staleTime: 0,
        }),
        // We need to get the pipeline to access pipeline_state and visual_state
        (async () => {
          const versionData = await queryClient.fetchQuery({
            queryKey: ['template-version', templateDetail.current_version_id],
            staleTime: 0,
          });
          return getPipeline(versionData.pipeline_definition_id);
        })()
      ]);

      // Build initialData for the builder modal
      const initialData: TemplateData = {
        name: templateDetail.name,
        description: templateDetail.description || '',
        source_pdf_id: versionDetail.source_pdf_id,
        signature_objects: versionDetail.signature_objects,
        extraction_fields: versionDetail.extraction_fields,
        pipeline_state: pipelineData.pipeline_state,
        visual_state: pipelineData.visual_state,
      };

      // Open builder in edit mode
      setBuilderMode('edit');
      setBuilderTemplateId(templateId);
      setBuilderInitialData(initialData);
      setBuilderPdfFileId(versionDetail.source_pdf_id);
      setBuilderPdfFile(null); // No uploaded file for edit mode
      setIsBuilderOpen(true);
    } catch (err) {
      console.error('Failed to load template for editing:', err);
      alert(`Failed to load template: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  const handleActivate = async (templateId: number) => {
    try {
      await activateTemplate.mutateAsync(templateId);
      // TanStack Query auto-invalidates and refetches on success
    } catch (err) {
      console.error('Failed to activate template:', err);
    }
  };

  const handleDeactivate = async (templateId: number) => {
    try {
      await deactivateTemplate.mutateAsync(templateId);
      // TanStack Query auto-invalidates and refetches on success
    } catch (err) {
      console.error('Failed to deactivate template:', err);
    }
  };

  const handleCreateTemplate = () => {
    // Create a hidden file input element
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'application/pdf';

    input.onchange = (e: Event) => {
      const target = e.target as HTMLInputElement;
      const file = target.files?.[0];

      if (file) {
        // Validate file type
        if (file.type !== 'application/pdf') {
          alert('Please select a PDF file');
          return;
        }

        // Store the PDF file and open the builder
        setBuilderPdfFile(file);
        setBuilderPdfFileId(null); // No stored PDF ID for new uploads
        setIsBuilderOpen(true);
      }
    };

    // Trigger the file picker
    input.click();
  };

  const handleCloseBuilder = () => {
    setIsBuilderOpen(false);
    setBuilderMode('create');
    setBuilderTemplateId(undefined);
    setBuilderInitialData(undefined);
    setBuilderPdfFileId(null);
    setBuilderPdfFile(null);
  };

  const handleSaveTemplate = async (templateData: TemplateData) => {
    try {
      if (builderMode === 'create') {
        await createTemplate.mutateAsync({
          name: templateData.name,
          description: templateData.description,
          source_pdf_id: templateData.source_pdf_id!,
          signature_objects: templateData.signature_objects,
          extraction_fields: templateData.extraction_fields,
          pipeline_state: templateData.pipeline_state,
          visual_state: templateData.visual_state,
        } as any); // TODO: Fix type mismatch with SignatureObject[] vs PdfObjects
        console.log('Template created successfully');
      } else if (builderMode === 'edit' && builderTemplateId) {
        await updateTemplate.mutateAsync({
          templateId: builderTemplateId,
          request: {
            name: templateData.name,
            description: templateData.description,
            signature_objects: templateData.signature_objects,
            extraction_fields: templateData.extraction_fields,
            pipeline_state: templateData.pipeline_state,
            visual_state: templateData.visual_state,
          } as any, // TODO: Fix type mismatch
        });
        console.log('Template updated successfully');
      }
      // TanStack Query auto-invalidates and refetches on success
    } catch (err) {
      console.error(`Failed to ${builderMode} template:`, err);
      throw err; // Re-throw to let modal handle error
    }
  };

  // ==========================================================================
  // Render
  // ==========================================================================

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-900 border border-red-700 rounded-lg p-4">
          <h2 className="text-xl font-bold text-red-300 mb-2">Error</h2>
          <p className="text-red-200">
            {error instanceof Error ? error.message : 'Failed to load templates'}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-red-700 hover:bg-red-600 text-white rounded transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">PDF Templates</h1>
          <p className="text-gray-400 mt-2">
            Manage templates for automated document processing
          </p>
        </div>
        <button
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={handleCreateTemplate}
          disabled={isLoading || createTemplate.isPending}
        >
          {createTemplate.isPending ? 'Creating...' : '+ Create Template'}
        </button>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="mb-6 bg-blue-900 border border-blue-700 rounded-lg p-4">
          <p className="text-blue-200">Loading templates...</p>
        </div>
      )}

      {/* Filter and Sort Controls */}
      <div className="mb-6 bg-gray-800 border border-gray-700 rounded-lg p-4">
        <div className="flex flex-wrap items-center gap-4">
          {/* Status Filter */}
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-300">
              Status:
            </label>
            <select
              value={statusFilter}
              onChange={(e) =>
                setStatusFilter(e.target.value as TemplateStatus | 'all')
              }
              className="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">All</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>

          {/* Sort By */}
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-300">
              Sort by:
            </label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortBy)}
              className="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="name">Name</option>
              <option value="status">Status</option>
              <option value="usage_count">Usage Count</option>
            </select>
          </div>

          {/* Sort Order */}
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-300">Order:</label>
            <button
              onClick={() =>
                setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
              }
              className="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg px-3 py-2 hover:bg-gray-600 transition-colors flex items-center space-x-1"
            >
              <span>{sortOrder === 'asc' ? 'Ascending' : 'Descending'}</span>
              <svg
                className={`w-4 h-4 transition-transform ${sortOrder === 'desc' ? 'rotate-180' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 15l7-7 7 7"
                />
              </svg>
            </button>
          </div>

          {/* Results Count */}
          <div className="ml-auto text-sm text-gray-400">
            {filteredTemplates.length} template
            {filteredTemplates.length !== 1 ? 's' : ''}
          </div>
        </div>
      </div>

      {/* Templates Display */}
      <div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTemplates.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              onView={handleView}
              onActivate={
                template.status !== 'active' ? handleActivate : undefined
              }
              onDeactivate={
                template.status === 'active' ? handleDeactivate : undefined
              }
            />
          ))}
        </div>

      {/* Empty State */}
      {filteredTemplates.length === 0 && !isLoading && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-12 text-center">
          <div className="text-gray-400 mb-4">
            <svg
              className="mx-auto h-12 w-12 text-gray-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-white mb-2">
            {statusFilter === 'all'
              ? 'No templates yet'
              : `No ${statusFilter} templates`}
          </h3>
          <p className="text-gray-400 mb-4">
            {statusFilter === 'all'
              ? 'Get started by creating your first template'
              : `Try adjusting your filters or create a new template`}
          </p>
          <button
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
            onClick={handleCreateTemplate}
          >
            Create Template
          </button>
        </div>
      )}
    </div>

      {/* Template Builder Modal */}
      <TemplateBuilderModal
        isOpen={isBuilderOpen}
        mode={builderMode}
        templateId={builderTemplateId}
        initialData={builderInitialData}
        pdfFileId={builderPdfFileId}
        pdfFile={builderPdfFile}
        onClose={handleCloseBuilder}
        onSave={handleSaveTemplate}
      />

      {/* Template Detail Modal */}
      <TemplateDetailModal
        isOpen={isDetailOpen}
        templateId={detailTemplateId}
        onClose={handleCloseDetail}
        onEdit={handleEditFromDetail}
      />
    </div>
  );
}
