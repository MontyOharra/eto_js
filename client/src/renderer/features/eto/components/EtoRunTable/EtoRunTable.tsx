import { useState } from "react";
import { EtoRunListItem, EtoRunStatus } from "../../types";
import { StatusIcon } from "./StatusIcon";
import {
  NotStartedRunRow,
  ProcessingRunRow,
  SuccessRunRow,
  FailureRunRow,
  NeedsTemplateRunRow,
  SkippedRunRow,
} from "../EtoRunRow";

interface EtoRunTableProps {
  title: string;
  status: EtoRunStatus;
  runs: EtoRunListItem[];
  // Status-specific callbacks (single run)
  onView?: (runId: number) => void;
  onSkip?: (runId: number) => void;
  onBuildTemplate?: (runId: number) => void;
  onReprocess?: (runId: number) => void;
  onDelete?: (runId: number) => void;
  // Bulk action callbacks
  onBulkSkip?: (runIds: number[]) => void;
  onBulkReprocess?: (runIds: number[]) => void;
  onBulkDelete?: (runIds: number[]) => void;
}

export function EtoRunTable({
  title,
  status,
  runs,
  onView,
  onSkip,
  onBuildTemplate,
  onReprocess,
  onDelete,
  onBulkSkip,
  onBulkReprocess,
  onBulkDelete,
}: EtoRunTableProps) {
  const [isExpanded, setIsExpanded] = useState(runs.length > 0);
  const [selectedRunIds, setSelectedRunIds] = useState<Set<number>>(new Set());

  // Check if all runs are selected
  const allSelected = runs.length > 0 && selectedRunIds.size === runs.length;
  const someSelected =
    selectedRunIds.size > 0 && selectedRunIds.size < runs.length;

  // Toggle all runs selection
  const handleSelectAll = () => {
    if (allSelected) {
      setSelectedRunIds(new Set());
    } else {
      setSelectedRunIds(new Set(runs.map((run) => run.id)));
    }
  };

  // Toggle individual run selection
  const handleToggleRun = (runId: number) => {
    const newSelected = new Set(selectedRunIds);
    if (newSelected.has(runId)) {
      newSelected.delete(runId);
    } else {
      newSelected.add(runId);
    }
    setSelectedRunIds(newSelected);
  };

  // Bulk action handlers
  const handleBulkSkip = () => {
    if (onBulkSkip && selectedRunIds.size > 0) {
      onBulkSkip(Array.from(selectedRunIds));
      setSelectedRunIds(new Set()); // Clear selection after action
    }
  };

  const handleBulkReprocess = () => {
    if (onBulkReprocess && selectedRunIds.size > 0) {
      onBulkReprocess(Array.from(selectedRunIds));
      setSelectedRunIds(new Set()); // Clear selection after action
    }
  };

  const handleBulkDelete = () => {
    if (onBulkDelete && selectedRunIds.size > 0) {
      onBulkDelete(Array.from(selectedRunIds));
      setSelectedRunIds(new Set()); // Clear selection after action
    }
  };

  const getStatusColor = (status: EtoRunStatus) => {
    switch (status) {
      case "success":
        return "text-green-400";
      case "failure":
        return "text-red-400";
      case "needs_template":
        return "text-yellow-400";
      case "processing":
        return "text-blue-400";
      case "not_started":
        return "text-gray-400";
      case "skipped":
        return "text-gray-500";
      default:
        return "text-gray-400";
    }
  };

  let statusDisplayTest: string;
  if (status === "needs_template") {
    statusDisplayTest = "needs template";
  } else if (status === "not_started") {
    statusDisplayTest = "not started";
  } else {
    statusDisplayTest = status;
  }

  const renderRow = (run: EtoRunListItem) => {
    const isSelected = selectedRunIds.has(run.id);

    switch (status) {
      case "not_started":
        return (
          <NotStartedRunRow
            key={run.id}
            run={run}
            isSelected={isSelected}
            onToggleSelect={handleToggleRun}
          />
        );
      case "processing":
        return (
          <ProcessingRunRow
            key={run.id}
            run={run}
            isSelected={isSelected}
            onToggleSelect={handleToggleRun}
          />
        );
      case "success":
        return onView && (
          <SuccessRunRow
            key={run.id}
            run={run}
            onView={onView}
            isSelected={isSelected}
            onToggleSelect={handleToggleRun}
          />
        );
      case "failure":
        return onView && onReprocess && onSkip && (
          <FailureRunRow
            key={run.id}
            run={run}
            onView={onView}
            onReprocess={onReprocess}
            onSkip={onSkip}
            isSelected={isSelected}
            onToggleSelect={handleToggleRun}
          />
        );
      case "needs_template":
        return onBuildTemplate && onReprocess && onSkip && (
          <NeedsTemplateRunRow
            key={run.id}
            run={run}
            onBuildTemplate={onBuildTemplate}
            onReprocess={onReprocess}
            onSkip={onSkip}
            isSelected={isSelected}
            onToggleSelect={handleToggleRun}
          />
        );
      case "skipped":
        return onReprocess && onDelete && (
          <SkippedRunRow
            key={run.id}
            run={run}
            onReprocess={onReprocess}
            onDelete={onDelete}
            isSelected={isSelected}
            onToggleSelect={handleToggleRun}
          />
        );
      default:
        return (
          <NotStartedRunRow
            key={run.id}
            run={run}
            isSelected={isSelected}
            onToggleSelect={handleToggleRun}
          />
        );
    }
  };

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
      {/* Table Header */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-750 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {/* Left side - Icon with dropdown arrow underneath (vertically centered) */}
        <div className="flex items-center space-x-3">
          <div className="flex flex-col items-center justify-center">
            <StatusIcon status={status} />
            <svg
              className={`w-4 h-4 text-gray-400 transition-transform mt-1 ${
                isExpanded ? "rotate-180" : ""
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </div>

          <div>
            <h3 className={`text-lg font-semibold ${getStatusColor(status)}`}>
              {title}
            </h3>
            <p className="text-sm text-gray-400">
              {runs.length} {runs.length === 1 ? "run" : "runs"}
            </p>
          </div>
        </div>

        {/* Right side - Bulk action buttons and Select all checkbox */}
        <div
          className="flex items-center space-x-3"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Bulk action buttons - only show when items are selected */}
          {selectedRunIds.size > 0 && (
            <div className="flex items-center space-x-2">
              {/* Reprocess button - for needs_template, failure, and skipped statuses */}
              {onBulkReprocess &&
                (status === "needs_template" ||
                  status === "failure" ||
                  status === "skipped") && (
                  <button
                    onClick={handleBulkReprocess}
                    className="px-3 py-1 text-xs bg-green-600 hover:bg-green-700 text-white rounded transition-colors"
                  >
                    Reprocess ({selectedRunIds.size})
                  </button>
                )}
                
              {/* Skip button - for needs_template and failure statuses */}
              {onBulkSkip &&
                (status === "needs_template" || status === "failure") && (
                  <button
                    onClick={handleBulkSkip}
                    className="px-3 py-1 text-xs bg-yellow-600 hover:bg-yellow-700 text-white rounded transition-colors"
                  >
                    Skip ({selectedRunIds.size})
                  </button>
                )}

              {/* Delete button - for skipped status */}
              {onBulkDelete && status === "skipped" && (
                <button
                  onClick={handleBulkDelete}
                  className="px-3 py-1 text-xs bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
                >
                  Delete ({selectedRunIds.size})
                </button>
              )}
            </div>
          )}

          {/* Select all checkbox */}
          <label className="flex items-center cursor-pointer group">
            <span className="mr-2 text-sm text-gray-400 group-hover:text-gray-300">
              Select All
            </span>
            <input
              type="checkbox"
              checked={allSelected}
              ref={(input) => {
                if (input) {
                  input.indeterminate = someSelected;
                }
              }}
              onChange={handleSelectAll}
              className="w-4 h-4 rounded border-2 border-gray-600 bg-gray-900 appearance-none checked:bg-blue-600 checked:border-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-800 cursor-pointer transition-colors relative checked:after:content-['✓'] checked:after:absolute checked:after:text-white checked:after:text-xs checked:after:left-[2px] checked:after:top-[-2px]"
            />
          </label>
        </div>
      </div>

      {/* Table Content */}
      {isExpanded && (
        <div className="border-t border-gray-700">
          {runs.length > 0 ? (
            <div className="p-4 space-y-3">{runs.map(renderRow)}</div>
          ) : (
            <div className="p-8 text-center">
              <p className="text-gray-400">No {statusDisplayTest} runs found</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
