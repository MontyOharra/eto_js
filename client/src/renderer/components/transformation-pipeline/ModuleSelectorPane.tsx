import { useState, useMemo } from "react";
import { ModuleTemplate } from "../../types/moduleTypes";

interface ModuleSelectorPaneProps {
  modules: ModuleTemplate[];
  selectedModuleId: string | null;
  onModuleSelect: (moduleId: string | null) => void;
}

type ModuleKind = "all" | "transform" | "action" | "control";

const MODULE_KINDS: ModuleKind[] = ["all", "transform", "action", "control"];

const KIND_LABELS: Record<ModuleKind, string> = {
  all: "All",
  transform: "Transform",
  action: "Action",
  control: "Control",
};

const KIND_COLORS: Record<string, string> = {
  transform: "#3B82F6", // blue-500
  action: "#10B981", // green-500
  control: "#8B5CF6", // purple-500
};

export function ModuleSelectorPane({
  modules,
  selectedModuleId,
  onModuleSelect,
}: ModuleSelectorPaneProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedType, setSelectedType] = useState<ModuleKind>("all");
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Filter and group modules
  const { displayModules, groupedByCategory } = useMemo(() => {
    // Apply filters
    let filtered = modules.filter((m) => {
      const matchesSearch = m.title
        .toLowerCase()
        .includes(searchTerm.toLowerCase());
      const matchesType =
        selectedType === "all" || m.kind === selectedType;
      return matchesSearch && matchesType;
    });

    // Group by category
    const grouped: Record<string, ModuleTemplate[]> = {};
    filtered.forEach((module) => {
      const category = module.category || "Uncategorized";
      if (!grouped[category]) {
        grouped[category] = [];
      }
      grouped[category].push(module);
    });

    // Sort categories and modules within categories
    const sortedCategories = Object.keys(grouped).sort();
    sortedCategories.forEach((category) => {
      grouped[category].sort((a, b) => a.title.localeCompare(b.title));
    });

    return {
      displayModules: filtered,
      groupedByCategory: grouped,
    };
  }, [modules, searchTerm, selectedType]);

  const handleTypeChange = (direction: "prev" | "next") => {
    const currentIndex = MODULE_KINDS.indexOf(selectedType);
    let newIndex: number;

    if (direction === "prev") {
      newIndex = currentIndex === 0 ? MODULE_KINDS.length - 1 : currentIndex - 1;
    } else {
      newIndex = currentIndex === MODULE_KINDS.length - 1 ? 0 : currentIndex + 1;
    }

    setSelectedType(MODULE_KINDS[newIndex]);
  };

  if (isCollapsed) {
    return (
      <div className="w-12 bg-gray-800 border-r border-gray-600 flex flex-col items-center py-4">
        <button
          onClick={() => setIsCollapsed(false)}
          className="text-gray-400 hover:text-white transition-colors"
          title="Expand"
        >
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 5l7 7-7 7M5 5l7 7-7 7"
            />
          </svg>
        </button>
      </div>
    );
  }

  return (
    <div className="w-80 bg-gray-800 border-r border-gray-600 flex flex-col h-full">
      {/* Header */}
      <div className="p-3 border-b border-gray-600 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white uppercase tracking-wide">
          Module Pane
        </h2>
        <button
          onClick={() => setIsCollapsed(true)}
          className="text-gray-400 hover:text-white transition-colors"
          title="Collapse"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
            />
          </svg>
        </button>
      </div>

      {/* Search Bar */}
      <div className="p-3 border-b border-gray-600">
        <div className="relative">
          <svg
            className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search modules..."
            className="w-full pl-10 pr-3 py-2 bg-gray-700 text-white text-sm rounded-md border border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Type Carousel Selector */}
      <div className="p-3 border-b border-gray-600">
        <div className="flex items-center justify-center space-x-2">
          <button
            onClick={() => handleTypeChange("prev")}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </button>
          <div className="text-center min-w-[100px]">
            <span className="text-white font-medium">
              {KIND_LABELS[selectedType]}
            </span>
          </div>
          <button
            onClick={() => handleTypeChange("next")}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5l7 7-7 7"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Module List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-6">
        {displayModules.length === 0 ? (
          <div className="text-center py-8 text-gray-400 text-sm">
            {searchTerm
              ? `No modules found for "${searchTerm}"`
              : `No ${selectedType === "all" ? "" : selectedType + " "}modules available`}
          </div>
        ) : (
          Object.keys(groupedByCategory)
            .sort()
            .map((category) => (
              <div key={category}>
                {/* Category Header */}
                <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
                  {category}
                </h3>

                {/* Module Cards */}
                <div className="space-y-2">
                  {groupedByCategory[category].map((module) => (
                    <ModuleCard
                      key={module.id}
                      module={module}
                      isSelected={selectedModuleId === module.id}
                      onSelect={() =>
                        onModuleSelect(
                          selectedModuleId === module.id ? null : module.id
                        )
                      }
                    />
                  ))}
                </div>
              </div>
            ))
        )}
      </div>
    </div>
  );
}

interface ModuleCardProps {
  module: ModuleTemplate;
  isSelected: boolean;
  onSelect: () => void;
}

function ModuleCard({ module, isSelected, onSelect }: ModuleCardProps) {
  const kindColor = KIND_COLORS[module.kind] || "#6B7280";

  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData("application/reactflow", JSON.stringify({ moduleId: module.id }));
    e.dataTransfer.effectAllowed = "move";

    // Create custom drag preview that looks like module header
    const dragPreview = document.createElement("div");
    dragPreview.style.position = "absolute";
    dragPreview.style.top = "-1000px";
    dragPreview.style.padding = "8px 12px";
    dragPreview.style.backgroundColor = module.color || "#4B5563";
    dragPreview.style.color = "white";
    dragPreview.style.borderRadius = "8px 8px 0 0";
    dragPreview.style.fontSize = "14px";
    dragPreview.style.fontWeight = "500";
    dragPreview.style.minWidth = "200px";
    dragPreview.textContent = module.title;
    document.body.appendChild(dragPreview);
    e.dataTransfer.setDragImage(dragPreview, 0, 0);
    setTimeout(() => document.body.removeChild(dragPreview), 0);
  };

  return (
    <button
      onClick={onSelect}
      draggable
      onDragStart={handleDragStart}
      className={`w-full text-left p-3 rounded-md transition-all cursor-grab active:cursor-grabbing ${
        isSelected
          ? "bg-blue-900 border-2 border-blue-500"
          : "bg-gray-700 border-2 border-transparent hover:bg-gray-600"
      }`}
      style={{
        borderLeftColor: isSelected ? undefined : kindColor,
        borderLeftWidth: isSelected ? undefined : "4px",
      }}
    >
      {/* Module Title */}
      <div className="font-medium text-white text-sm mb-1">{module.title}</div>

      {/* Type Badge */}
      <div className="flex items-center space-x-2 mb-2">
        <span
          className="inline-block px-2 py-0.5 rounded text-xs font-medium uppercase"
          style={{
            backgroundColor: kindColor + "33",
            color: kindColor,
          }}
        >
          {module.kind}
        </span>
      </div>

      {/* Description */}
      {module.description && (
        <p className="text-xs text-gray-400 line-clamp-2">
          {module.description}
        </p>
      )}
    </button>
  );
}
