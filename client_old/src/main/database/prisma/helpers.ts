import { DatabaseConfig } from "../../../@types/database.js";
import { app } from "electron";
import { config as dotenvConfig } from "dotenv";

/**
 * Build a SQL-Server connection string for Prisma.
 * Reads from the provided `config` object first and falls back to the
 * corresponding environment variables (which may have been populated by
 * SecureConfigManager or a .env file).
 */
export function buildDatabaseUrl(config?: DatabaseConfig): string {
  // In development we still want to honour the developer's .env file.
  if (!app.isPackaged) {
    dotenvConfig();
  }

  const authType = config?.authType || process.env.DB_AUTH_TYPE || "windows";
  const server = config?.server || process.env.DB_SERVER || "localhost";
  const port = config?.port || process.env.DB_PORT || "1433";
  const database = config?.database || process.env.DB_NAME || "HTC";
  const encrypt = config?.encrypt || process.env.DB_ENCRYPT || "optional";
  const trustCert =
    config?.trustServerCertificate ||
    process.env.DB_TRUST_SERVER_CERTIFICATE ||
    "true";

  let connectionString = `sqlserver://${server}:${port};database=${database};encrypt=${encrypt};trustServerCertificate=${trustCert}`;

  switch (authType.toLowerCase()) {
    case "windows":
    case "integrated": {
      connectionString += ";integratedSecurity=true";
      break;
    }

    case "sql":
    case "sqlserver": {
      const username = config?.username || process.env.DB_USER;
      const password = config?.password || process.env.DB_PASSWORD;
      if (username && password) {
        connectionString += `;username=${username};password=${password}`;
      }
      break;
    }

    case "azure":
    case "azuread": {
      const azureUser = config?.azureUser || process.env.DB_AZURE_USER;
      const azurePassword =
        config?.azurePassword || process.env.DB_AZURE_PASSWORD;
      if (azureUser && azurePassword) {
        connectionString += `;username=${azureUser};password=${azurePassword}`;
      }
      const clientId = config?.azureClientId || process.env.DB_AZURE_CLIENT_ID;
      if (clientId) {
        connectionString += `;clientId=${clientId}`;
      }
      break;
    }
  }

  return connectionString;
}


// Load environment variables – in dev we use dotenv, in prod they're set via SecureConfigManager
export function loadEnvironmentVariables() {
  if (!app.isPackaged) {
    dotenvConfig();
  }
}
