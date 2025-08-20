import { useState, useMemo } from "react";
import { Template } from "../data/mockTemplates";
import { TemplateCard } from "./TemplateCard";

interface TemplatesListProps {
  templates: Template[];
  onEdit: (template: Template) => void;
  onView: (template: Template) => void;
  onDelete: (template: Template) => void;
}

type SortField =
  | "name"
  | "customerName"
  | "updatedAt"
  | "usageCount"
  | "successRate"
  | "status";
type SortDirection = "asc" | "desc";

export function TemplatesList({
  templates,
  onEdit,
  onView,
  onDelete,
}: TemplatesListProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<Template["status"] | "all">(
    "all"
  );
  const [customerFilter, setCustomerFilter] = useState<string>("all");
  const [sortField, setSortField] = useState<SortField>("updatedAt");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  // Get unique customers for filter
  const customers = useMemo(() => {
    const customerSet = new Set(
      templates.map((t) => t.customerName).filter(Boolean)
    );
    return Array.from(customerSet).sort();
  }, [templates]);

  // Filter and sort templates
  const filteredAndSortedTemplates = useMemo(() => {
    let filtered = templates.filter((template) => {
      const matchesSearch =
        template.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        template.description
          ?.toLowerCase()
          .includes(searchTerm.toLowerCase()) ||
        template.customerName
          ?.toLowerCase()
          .includes(searchTerm.toLowerCase()) ||
        template.tags.some((tag) =>
          tag.toLowerCase().includes(searchTerm.toLowerCase())
        );

      const matchesStatus =
        statusFilter === "all" || template.status === statusFilter;
      const matchesCustomer =
        customerFilter === "all" || template.customerName === customerFilter;

      return matchesSearch && matchesStatus && matchesCustomer;
    });

    // Sort templates
    filtered.sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (sortField) {
        case "name":
          aValue = a.name.toLowerCase();
          bValue = b.name.toLowerCase();
          break;
        case "customerName":
          aValue = a.customerName?.toLowerCase() || "";
          bValue = b.customerName?.toLowerCase() || "";
          break;
        case "updatedAt":
          aValue = a.updatedAt.getTime();
          bValue = b.updatedAt.getTime();
          break;
        case "usageCount":
          aValue = a.usageCount;
          bValue = b.usageCount;
          break;
        case "successRate":
          aValue = a.successRate || 0;
          bValue = b.successRate || 0;
          break;
        case "status":
          aValue = a.status;
          bValue = b.status;
          break;
        default:
          return 0;
      }

      if (sortDirection === "asc") {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });

    return filtered;
  }, [
    templates,
    searchTerm,
    statusFilter,
    customerFilter,
    sortField,
    sortDirection,
  ]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
  };

  const SortButton = ({
    field,
    children,
  }: {
    field: SortField;
    children: React.ReactNode;
  }) => (
    <button
      onClick={() => handleSort(field)}
      className={`px-3 py-1 text-xs rounded transition-colors ${
        sortField === field
          ? "bg-blue-600 text-white"
          : "bg-gray-700 text-gray-300 hover:bg-gray-600"
      }`}
    >
      {children}
      {sortField === field && (
        <span className="ml-1">{sortDirection === "asc" ? "↑" : "↓"}</span>
      )}
    </button>
  );

  return (
    <div className="space-y-6">
      {/* Filters and Search */}
      <div className="bg-gray-800 p-4 rounded-lg space-y-4">
        <div className="flex flex-wrap gap-4">
          {/* Search */}
          <div className="flex-1 min-w-64">
            <input
              type="text"
              placeholder="Search templates..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value as Template["status"] | "all")
            }
            className="px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="draft">Draft</option>
            <option value="testing">Testing</option>
            <option value="archived">Archived</option>
          </select>

          {/* Customer Filter */}
          <select
            value={customerFilter}
            onChange={(e) => setCustomerFilter(e.target.value)}
            className="px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
          >
            <option value="all">All Customers</option>
            {customers.map((customer) => (
              <option key={customer} value={customer}>
                {customer}
              </option>
            ))}
          </select>
        </div>

        {/* Sort Options */}
        <div className="flex flex-wrap gap-2">
          <span className="text-gray-400 text-sm self-center">Sort by:</span>
          <SortButton field="name">Name</SortButton>
          <SortButton field="customerName">Customer</SortButton>
          <SortButton field="updatedAt">Last Modified</SortButton>
          <SortButton field="usageCount">Usage</SortButton>
          <SortButton field="successRate">Success Rate</SortButton>
          <SortButton field="status">Status</SortButton>
        </div>
      </div>

      {/* Results Count */}
      <div className="flex justify-between items-center">
        <p className="text-gray-400">
          Showing {filteredAndSortedTemplates.length} of {templates.length}{" "}
          templates
        </p>
        <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors">
          Create New Template
        </button>
      </div>

      {/* Templates Grid */}
      {filteredAndSortedTemplates.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredAndSortedTemplates.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              onEdit={onEdit}
              onView={onView}
              onDelete={onDelete}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <p className="text-gray-400 text-lg">
            No templates found matching your criteria
          </p>
          <p className="text-gray-500 text-sm mt-2">
            Try adjusting your search or filters
          </p>
        </div>
      )}
    </div>
  );
}
