import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { DatabaseConfig } from "../../@types/database";

export const Route = createFileRoute("/conn-definition")({
  component: ConnectionDefinition,
});

function ConnectionDefinition() {
  const [config, setConfig] = useState<DatabaseConfig>({
    authType: "windows",
    server: "localhost",
    port: "1433",
    database: "HTC",
    encrypt: "optional",
    trustServerCertificate: "true",
    username: "",
    password: "",
    azureUser: "",
    azurePassword: "",
    azureClientId: "",
  });

  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState("");

  // Load current configuration on component mount
  useEffect(() => {
    const loadCurrentConfig = async () => {
      try {
        const currentConfig = await window.electron.getDatabaseConfig();
        if (currentConfig) {
          setConfig(currentConfig);
        }
      } catch (error) {
        console.error("Failed to load current configuration:", error);
        setMessage("Failed to load current configuration");
      } finally {
        setIsLoading(false);
      }
    };

    loadCurrentConfig();
  }, []);

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setConfig((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setMessage("");

    try {
      const result = await window.electron.setDatabaseConfig(config);

      if (result) {
        setMessage("Configution Valid");
      } else {
        setMessage("Configuration Invalid");
      }
    } catch (error) {
      setMessage(
        `Error: ${error instanceof Error ? error.message : "Unknown error"}`
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="p-6 max-w-2xl mx-auto">
        <div className="text-center">Loading current configuration...</div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">
        Database Connection Configuration
      </h1>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">
            Authentication Type
          </label>
          <select
            name="authType"
            value={config.authType}
            onChange={handleInputChange}
            className="w-full p-2 border border-gray-300 rounded-md"
          >
            <option value="windows">Windows Authentication</option>
            <option value="sql">SQL Server Authentication</option>
            <option value="azure">Azure AD Authentication</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Server</label>
          <input
            type="text"
            name="server"
            value={config.server}
            onChange={handleInputChange}
            className="w-full p-2 border border-gray-300 rounded-md"
            placeholder="localhost"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Port</label>
          <input
            type="text"
            name="port"
            value={config.port}
            onChange={handleInputChange}
            className="w-full p-2 border border-gray-300 rounded-md"
            placeholder="1433"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">
            Database Name
          </label>
          <input
            type="text"
            name="database"
            value={config.database}
            onChange={handleInputChange}
            className="w-full p-2 border border-gray-300 rounded-md"
            placeholder="HTC"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Encrypt</label>
          <select
            name="encrypt"
            value={config.encrypt}
            onChange={handleInputChange}
            className="w-full p-2 border border-gray-300 rounded-md"
          >
            <option value="optional">Optional</option>
            <option value="true">True</option>
            <option value="false">False</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">
            Trust Server Certificate
          </label>
          <select
            name="trustServerCertificate"
            value={config.trustServerCertificate}
            onChange={handleInputChange}
            className="w-full p-2 border border-gray-300 rounded-md"
          >
            <option value="true">True</option>
            <option value="false">False</option>
          </select>
        </div>

        {config.authType === "sql" && (
          <>
            <div>
              <label className="block text-sm font-medium mb-1">Username</label>
              <input
                type="text"
                name="username"
                value={config.username || ""}
                onChange={handleInputChange}
                className="w-full p-2 border border-gray-300 rounded-md"
                placeholder="Enter username"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Password</label>
              <input
                type="password"
                name="password"
                value={config.password || ""}
                onChange={handleInputChange}
                className="w-full p-2 border border-gray-300 rounded-md"
                placeholder="Enter password"
                required
              />
            </div>
          </>
        )}

        {config.authType === "azure" && (
          <>
            <div>
              <label className="block text-sm font-medium mb-1">
                Azure User
              </label>
              <input
                type="text"
                name="azureUser"
                value={config.azureUser || ""}
                onChange={handleInputChange}
                className="w-full p-2 border border-gray-300 rounded-md"
                placeholder="Enter Azure username"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Azure Password
              </label>
              <input
                type="password"
                name="azurePassword"
                value={config.azurePassword || ""}
                onChange={handleInputChange}
                className="w-full p-2 border border-gray-300 rounded-md"
                placeholder="Enter Azure password"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Azure Client ID (Optional)
              </label>
              <input
                type="text"
                name="azureClientId"
                value={config.azureClientId || ""}
                onChange={handleInputChange}
                className="w-full p-2 border border-gray-300 rounded-md"
                placeholder="Enter Azure client ID"
              />
            </div>
          </>
        )}

        <div className="pt-4">
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-blue-500 text-white py-2 px-4 rounded-md hover:bg-blue-600 disabled:bg-gray-400"
          >
            {isSubmitting ? "Updating..." : "Update Configuration"}
          </button>
        </div>

        {message && (
          <div
            className={`p-3 rounded-md ${
              message.includes("successful") || message.includes("saved")
                ? "bg-green-100 text-green-800"
                : "bg-red-100 text-red-800"
            }`}
          >
            {message}
          </div>
        )}
      </form>
    </div>
  );
}
