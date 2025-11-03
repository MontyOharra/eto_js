import { useState } from 'react';
import { EtoRunListItem, EtoRunStatus } from '../../types';
import { StatusIcon } from '../ui';
import {
  NotStartedRunRow,
  ProcessingRunRow,
  SuccessRunRow,
  FailureRunRow,
  NeedsTemplateRunRow,
  SkippedRunRow,
} from '../rows';

interface EtoRunsTableProps {
  title: string;
  status: EtoRunStatus;
  runs: EtoRunListItem[];
  // Status-specific callbacks
  onView?: (runId: number) => void;
  onReview?: (runId: number) => void;
  onSkip?: (runId: number) => void;
  onBuildTemplate?: (runId: number) => void;
  onReprocess?: (runId: number) => void;
  onDelete?: (runId: number) => void;
}

export function EtoRunsTable({
  title,
  status,
  runs,
  onView,
  onReview,
  onSkip,
  onBuildTemplate,
  onReprocess,
  onDelete,
}: EtoRunsTableProps) {
  const [isExpanded, setIsExpanded] = useState(runs.length > 0);

  const getStatusColor = (status: EtoRunStatus) => {
    switch (status) {
      case 'success':
        return 'text-green-400';
      case 'failure':
        return 'text-red-400';
      case 'needs_template':
        return 'text-yellow-400';
      case 'processing':
        return 'text-blue-400';
      case 'not_started':
        return 'text-gray-400';
      case 'skipped':
        return 'text-gray-500';
      default:
        return 'text-gray-400';
    }
  };

  const statusDisplayTest = 

  const renderRow = (run: EtoRunListItem) => {
    switch (status) {
      case 'not_started':
        return <NotStartedRunRow key={run.id} run={run} />;
      case 'processing':
        return <ProcessingRunRow key={run.id} run={run} />;
      case 'success':
        return onView ? (
          <SuccessRunRow key={run.id} run={run} onView={onView} />
        ) : (
          <NotStartedRunRow key={run.id} run={run} />
        );
      case 'failure':
        return onView && onReview && onSkip ? (
          <FailureRunRow
            key={run.id}
            run={run}
            onReview={onReview}
            onSkip={onSkip}
          />
        ) : (
          <NotStartedRunRow key={run.id} run={run} />
        );
      case 'needs_template':
        return onBuildTemplate && onSkip ? (
          <NeedsTemplateRunRow
            key={run.id}
            run={run}
            onBuildTemplate={onBuildTemplate}
            onSkip={onSkip}
          />
        ) : (
          <NotStartedRunRow key={run.id} run={run} />
        );
      case 'skipped':
        return onReprocess && onDelete ? (
          <SkippedRunRow
            key={run.id}
            run={run}
            onReprocess={onReprocess}
            onDelete={onDelete}
          />
        ) : (
          <NotStartedRunRow key={run.id} run={run} />
        );
      default:
        return <NotStartedRunRow key={run.id} run={run} />;
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
          <StatusIcon status={status} />
          <div>
            <h3 className={`text-lg font-semibold ${getStatusColor(status)}`}>
              {title}
            </h3>
            <p className="text-sm text-gray-400">
              {runs.length} {runs.length === 1 ? 'run' : 'runs'}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <span className="text-sm text-gray-400">{runs.length} items</span>
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform ${
              isExpanded ? 'rotate-180' : ''
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
      </div>

      {/* Table Content */}
      {isExpanded && (
        <div className="border-t border-gray-700">
          {runs.length > 0 ? (
            <div className="p-4 space-y-3">{runs.map(renderRow)}</div>
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
