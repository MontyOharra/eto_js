import { useState } from "react";
import { EtoRunSummary } from "../data/mockEtoRuns";
import { EtoRunRow } from "./EtoRunRow";

interface EtoRunsTableProps {
  title: string;
  runs: EtoRunSummary[];
  status: "success" | "failure" | "unrecognized";
  onView: (runId: string) => void;
  onReview: (runId: string) => void;
}

export function EtoRunsTable({
  title,
  runs,
  status,
  onView,
  onReview,
}: EtoRunsTableProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const getStatusColor = (status: EtoRunsTableProps["status"]) => {
    switch (status) {
      case "success":
        return "text-green-400";
      case "failure":
        return "text-red-400";
      case "unrecognized":
        return "text-yellow-400";
      default:
        return "text-gray-400";
    }
  };

  const getStatusIcon = (status: EtoRunsTableProps["status"]) => {
    switch (status) {
      case "success":
        return (
          <svg
            className="w-5 h-5 text-green-400"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
        );
      case "failure":
        return (
          <svg
            className="w-5 h-5 text-red-400"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
        );
      case "unrecognized":
        return (
          <svg
            className="w-5 h-5 text-yellow-400"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
        );
      default:
        return null;
    }
  };

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
      {/* Table Header */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-750 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center space-x-3">
          {getStatusIcon(status)}
          <div>
            <h3 className={`text-lg font-semibold ${getStatusColor(status)}`}>
              {title}
            </h3>
            <p className="text-sm text-gray-400">
              {runs.length} {runs.length === 1 ? "run" : "runs"}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <span className="text-sm text-gray-400">{runs.length} items</span>
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
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
      </div>

      {/* Table Content */}
      {isExpanded && (
        <div className="border-t border-gray-700">
          {runs.length > 0 ? (
            <div className="p-4 space-y-3">
              {runs.map((run) => (
                <EtoRunRow
                  key={run.id}
                  run={run}
                  onView={onView}
                  onReview={onReview}
                />
              ))}
            </div>
          ) : (
            <div className="p-8 text-center">
              <p className="text-gray-400">No {status} runs found</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
