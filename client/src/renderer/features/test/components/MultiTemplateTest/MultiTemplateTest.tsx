import { MultiTemplateTestResult, TemplateMatch } from '../../types';

interface MultiTemplateTestProps {
  isUploading: boolean;
  testResult: MultiTemplateTestResult | null;
  error: string | null;
  onFileUpload: (event: React.ChangeEvent<HTMLInputElement>) => void;
}

export function MultiTemplateTest({
  isUploading,
  testResult,
  error,
  onFileUpload,
}: MultiTemplateTestProps) {
  const triggerFileInput = () => {
    document.getElementById('pdf-upload-input')?.click();
  };

  return (
    <div className="px-6 pt-6 pb-4 border-b border-gray-700 flex-shrink-0">
      <div className="flex items-center gap-4">
        <div>
          <h2 className="text-lg font-semibold text-white">Test Multi-Template Matching</h2>
          <p className="text-gray-400 text-sm">Upload a PDF to test the new algorithm</p>
        </div>
        <input
          id="pdf-upload-input"
          type="file"
          accept=".pdf"
          onChange={onFileUpload}
          className="hidden"
        />
        <button
          onClick={triggerFileInput}
          disabled={isUploading}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded-lg transition-colors flex items-center gap-2"
        >
          {isUploading ? (
            <>
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span>Uploading...</span>
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <span>Upload PDF</span>
            </>
          )}
        </button>
      </div>

      {/* Result Display */}
      {testResult && (
        <div className="mt-4 bg-gray-800 rounded-lg p-4 border border-gray-700">
          <h3 className="text-white font-semibold mb-2">Result:</h3>
          <div className="space-y-2 text-sm">
            <div className="flex gap-2">
              <span className="text-gray-400">PDF:</span>
              <span className="text-white">{testResult.pdf_filename} (ID: {testResult.pdf_id})</span>
            </div>
            <div className="flex gap-2">
              <span className="text-gray-400">Total Pages:</span>
              <span className="text-white">{testResult.total_pages}</span>
            </div>
            <div className="flex gap-2">
              <span className="text-gray-400">Matches:</span>
              <span className="text-green-400">{testResult.matches.length}</span>
            </div>
            <div className="flex gap-2">
              <span className="text-gray-400">Unmatched Pages:</span>
              <span className="text-yellow-400">{testResult.unmatched_pages.length}</span>
            </div>
          </div>

          {testResult.matches.length > 0 && (
            <div className="mt-4">
              <h4 className="text-white font-semibold mb-2">Template Matches:</h4>
              <div className="space-y-2">
                {testResult.matches.map((match: TemplateMatch, idx: number) => (
                  <div key={idx} className="bg-gray-750 rounded p-3 border border-gray-600">
                    <div className="flex justify-between items-start mb-1">
                      <span className="text-white font-medium">{match.template_name}</span>
                      <span className="text-xs text-gray-400">v{match.version_number}</span>
                    </div>
                    <div className="text-sm text-gray-400">
                      Pages: {match.matched_pages.join(', ')}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {testResult.unmatched_pages.length > 0 && (
            <div className="mt-4">
              <h4 className="text-white font-semibold mb-2">Unmatched Pages:</h4>
              <div className="text-sm text-yellow-400">
                {testResult.unmatched_pages.join(', ')}
              </div>
            </div>
          )}

          {/* Raw JSON Output */}
          <details className="mt-4">
            <summary className="text-gray-400 cursor-pointer hover:text-white">View Raw JSON</summary>
            <pre className="mt-2 bg-gray-900 rounded p-3 text-xs text-green-400 overflow-auto max-h-60">
              {JSON.stringify(testResult, null, 2)}
            </pre>
          </details>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="mt-4 bg-red-900/20 border border-red-500/50 rounded-lg p-4">
          <h3 className="text-red-400 font-semibold mb-1">Error:</h3>
          <p className="text-red-300 text-sm">{error}</p>
        </div>
      )}
    </div>
  );
}
