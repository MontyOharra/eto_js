import { EtoRunMasterStatus } from '../../types';

interface EtoRunDetailOverviewProps {
  source: string;
  sourceDate: string;
  masterStatus: EtoRunMasterStatus;
  totalPages: number;
  templatesMatched: number;
  processingTime?: string;
}

function getStatusColor(status: EtoRunMasterStatus): string {
  switch (status) {
    case 'success':
      return 'text-green-400 bg-green-400/10';
    case 'processing':
      return 'text-blue-400 bg-blue-400/10';
    case 'failure':
      return 'text-red-400 bg-red-400/10';
    case 'not_started':
      return 'text-gray-400 bg-gray-400/10';
    default:
      return 'text-gray-400 bg-gray-400/10';
  }
}

export function EtoRunDetailOverview({
  source,
  sourceDate,
  masterStatus,
  totalPages,
  templatesMatched,
  processingTime = '-',
}: EtoRunDetailOverviewProps) {
  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <h2 className="text-xl font-semibold text-white mb-4">Overview</h2>
      <div className="grid grid-cols-5 gap-4">
        <div>
          <p className="text-gray-400 text-sm">Source</p>
          <p className="text-white font-medium mt-1">{source}</p>
          <p className="text-gray-400 text-xs mt-1">{sourceDate}</p>
        </div>
        <div>
          <p className="text-gray-400 text-sm">Status</p>
          <div className="flex items-center gap-2 mt-1">
            <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getStatusColor(masterStatus)}`}>
              {masterStatus}
            </span>
          </div>
        </div>
        <div>
          <p className="text-gray-400 text-sm">Total Pages</p>
          <p className="text-white text-lg font-semibold mt-1">{totalPages}</p>
        </div>
        <div>
          <p className="text-gray-400 text-sm">Templates Matched</p>
          <p className="text-white text-lg font-semibold mt-1">{templatesMatched}</p>
        </div>
        <div>
          <p className="text-gray-400 text-sm">Processing Time</p>
          <p className="text-white text-lg font-semibold mt-1">{processingTime}</p>
        </div>
      </div>
    </div>
  );
}
