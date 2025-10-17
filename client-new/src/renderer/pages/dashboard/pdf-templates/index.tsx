import { createFileRoute } from '@tanstack/react-router';
import { useEffect, useState } from 'react';
import { useMockTemplatesApi } from '../../../features/templates/hooks';
import { TemplateCard, TemplateBuilderModal, TemplateData } from '../../../features/templates/components';
import { TemplateListItem, TemplateStatus } from '../../../features/templates/types';

export const Route = createFileRoute('/dashboard/pdf-templates/')({
  component: TemplatesPage,
});

type SortBy = 'name' | 'status' | 'usage_count';
type SortOrder = 'asc' | 'desc';

function TemplatesPage() {
  const {
    getTemplates,
    createTemplate,
    activateTemplate,
    deactivateTemplate,
    deleteTemplate,
    isLoading,
    error,
  } = useMockTemplatesApi();

  const [allTemplates, setAllTemplates] = useState<TemplateListItem[]>([]);
  const [statusFilter, setStatusFilter] = useState<TemplateStatus | 'all'>('all');
  const [sortBy, setSortBy] = useState<SortBy>('name');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');

  // Template Builder Modal State
  const [isBuilderOpen, setIsBuilderOpen] = useState(false);
  const [builderPdfFileId, setBuilderPdfFileId] = useState<number | null>(null);

  // Fetch templates on mount
  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      const response = await getTemplates();
      setAllTemplates(response.items);
    } catch (err) {
      console.error('Failed to load templates:', err);
    }
  };

  // Filter and sort templates
  const getFilteredAndSortedTemplates = (): TemplateListItem[] => {
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
  };

  const filteredTemplates = getFilteredAndSortedTemplates();

  // ==========================================================================
  // Button Handlers
  // ==========================================================================

  const handleView = (templateId: number) => {
    console.log('View template:', templateId);
    // TODO: Navigate to template detail page or open modal
    // navigate({ to: `/dashboard/pdf-templates/${templateId}` });
  };

  const handleEdit = (templateId: number) => {
    console.log('Edit template:', templateId);
    // TODO: Navigate to template editor/wizard
    // navigate({ to: `/dashboard/pdf-templates/${templateId}/edit` });
  };

  const handleActivate = async (templateId: number) => {
    try {
      await activateTemplate(templateId);
      // Reload templates after successful activation
      await loadTemplates();
    } catch (err) {
      console.error('Failed to activate template:', err);
    }
  };

  const handleDeactivate = async (templateId: number) => {
    try {
      await deactivateTemplate(templateId);
      // Reload templates after successful deactivation
      await loadTemplates();
    } catch (err) {
      console.error('Failed to deactivate template:', err);
    }
  };

  const handleDelete = async (templateId: number) => {
    // Confirm deletion
    if (
      !window.confirm(
        'Are you sure you want to delete this template? This action cannot be undone.'
      )
    ) {
      return;
    }

    try {
      await deleteTemplate(templateId);
      // Reload templates after successful deletion
      await loadTemplates();
    } catch (err) {
      console.error('Failed to delete template:', err);
    }
  };

  const handleCreateTemplate = () => {
    // For now, use a mock PDF file ID (101)
    // In real implementation, user would select a PDF first
    setBuilderPdfFileId(101);
    setIsBuilderOpen(true);
  };

  const handleCloseBuilder = () => {
    setIsBuilderOpen(false);
    setBuilderPdfFileId(null);
  };

  const handleSaveTemplate = async (templateData: TemplateData) => {
    try {
      await createTemplate(templateData);
      await loadTemplates();
      console.log('Template created successfully');
    } catch (err) {
      console.error('Failed to create template:', err);
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
          <p className="text-red-200">{error}</p>
          <button
            onClick={loadTemplates}
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
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
          onClick={handleCreateTemplate}
        >
          + Create Template
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
              <option value="draft">Draft</option>
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
              onEdit={handleEdit}
              onActivate={
                template.status !== 'active' ? handleActivate : undefined
              }
              onDeactivate={
                template.status === 'active' ? handleDeactivate : undefined
              }
              onDelete={
                template.status === 'draft' ||
                template.current_version.usage_count === 0
                  ? handleDelete
                  : undefined
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
        pdfFileId={builderPdfFileId}
        onClose={handleCloseBuilder}
        onSave={handleSaveTemplate}
      />
    </div>
  );
}
