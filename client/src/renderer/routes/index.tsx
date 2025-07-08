import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { DatabaseConfig } from "../../@types/database";

export const Route = createFileRoute("/")({
  component: Index,
});

function Index() {
  const [config, setConfig] = useState<DatabaseConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleGetConfig = async () => {
    setIsLoading(true);
    try {
      const currentConfig = await window.electron.getDatabaseConfig();
      setConfig(currentConfig);
      console.log("Current Database Configuration:", currentConfig);
    } catch (error) {
      console.error("Failed to get database configuration:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-6">
      <h3 className="text-xl font-bold mb-4">Welcome Home!</h3>

      <div className="space-y-4">
        <button
          onClick={handleGetConfig}
          disabled={isLoading}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-blue-300"
        >
          {isLoading ? "Loading..." : "Get Current Database Config"}
        </button>

        {config && (
          <div className="mt-4 p-4 bg-gray-100 rounded-md">
            <h4 className="font-semibold mb-2">
              Current Database Configuration:
            </h4>
            <pre className="text-sm bg-white p-2 rounded border overflow-auto">
              {JSON.stringify(config, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
