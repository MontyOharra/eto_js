import { createFileRoute } from "@tanstack/react-router";
import { TemplatesList } from "../../components/TemplatesList";
import { mockTemplates } from "../../data/mockTemplates";
import { Template } from "../../data/mockTemplates";

export const Route = createFileRoute("/dashboard/templates")({
  component: TemplatesPage,
});

function TemplatesPage() {
  const handleEdit = (template: Template) => {
    console.log("Edit template:", template);
    // TODO: Navigate to template editor
  };

  const handleView = (template: Template) => {
    console.log("View template:", template);
    // TODO: Show template details modal
  };

  const handleDelete = (template: Template) => {
    console.log("Delete template:", template);
    // TODO: Show confirmation dialog
  };

  return (
    <div className="flex-1 p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-blue-300 mb-2">Templates</h1>
        <p className="text-gray-400">Manage your PDF extraction templates</p>
      </div>

      <TemplatesList
        templates={mockTemplates}
        onEdit={handleEdit}
        onView={handleView}
        onDelete={handleDelete}
      />
    </div>
  );
}
