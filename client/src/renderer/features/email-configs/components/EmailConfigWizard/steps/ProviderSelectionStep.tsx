/**
 * Provider Selection Step
 * First step in email config wizard - select email provider type
 */

interface ProviderSelectionStepProps {
  selectedProvider: string | null;
  onSelectProvider: (provider: string) => void;
}

interface Provider {
  id: string;
  name: string;
  description: string;
  icon: string;
  tag?: string;
}

const AVAILABLE_PROVIDERS: Provider[] = [
  {
    id: 'imap',
    name: 'IMAP',
    description: 'Connect to any email server using IMAP protocol. Works with Gmail, Outlook, custom domains, and more.',
    icon: '📧',
    tag: 'Universal',
  },
  // Future providers:
  // {
  //   id: 'graph_api',
  //   name: 'Microsoft Graph API',
  //   description: 'Connect to Microsoft 365 / Outlook.com using modern OAuth authentication',
  //   icon: '🔷',
  //   tag: 'Microsoft',
  // },
];

export function ProviderSelectionStep({
  selectedProvider,
  onSelectProvider,
}: ProviderSelectionStepProps) {
  return (
    <div className="space-y-4">
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-white mb-2">Choose Email Provider</h3>
        <p className="text-sm text-gray-400">
          Select how you want to connect to your email account
        </p>
      </div>

      <div className="space-y-3">
        {AVAILABLE_PROVIDERS.map((provider) => (
          <button
            key={provider.id}
            onClick={() => onSelectProvider(provider.id)}
            className={`w-full p-4 rounded-lg border-2 transition-all text-left ${
              selectedProvider === provider.id
                ? 'border-blue-600 bg-blue-600/10'
                : 'border-gray-700 bg-gray-800 hover:border-gray-600 hover:bg-gray-750'
            }`}
          >
            <div className="flex items-start space-x-4">
              {/* Icon */}
              <div className="text-4xl flex-shrink-0">{provider.icon}</div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2 mb-1">
                  <h4 className="text-base font-semibold text-white">{provider.name}</h4>

                  {provider.tag && (
                    <span className="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-300">
                      {provider.tag}
                    </span>
                  )}
                </div>

                <p className="text-sm text-gray-400 leading-relaxed">
                  {provider.description}
                </p>
              </div>

              {/* Selection Indicator */}
              <div className="flex-shrink-0">
                <div
                  className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                    selectedProvider === provider.id
                      ? 'border-blue-600 bg-blue-600'
                      : 'border-gray-600'
                  }`}
                >
                  {selectedProvider === provider.id && (
                    <svg
                      className="w-3 h-3 text-white"
                      fill="currentColor"
                      viewBox="0 0 12 12"
                    >
                      <path d="M10 3L4.5 8.5L2 6" stroke="currentColor" strokeWidth="2" fill="none" />
                    </svg>
                  )}
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Info Box */}
      <div className="mt-6 p-4 rounded-lg bg-blue-600/10 border border-blue-600/30">
        <div className="flex items-start space-x-3">
          <div className="text-blue-400 flex-shrink-0 mt-0.5">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="flex-1">
            <h5 className="text-sm font-medium text-blue-400 mb-1">About IMAP</h5>
            <p className="text-sm text-gray-300 leading-relaxed">
              IMAP is a universal email protocol supported by virtually all email providers.
              You'll need your email server settings (host, port) and login credentials.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
