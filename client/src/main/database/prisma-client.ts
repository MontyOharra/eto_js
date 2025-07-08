import { PrismaClient } from "../../../prisma/generated/client/index.js";
import { config } from "dotenv";
import { getPrismaQueryEnginePath } from "../helpers/utils.js";
import fs from "fs";
import { app } from "electron";
import { DatabaseConfig } from "../../@types/database.js";

// Load environment variables - simplified to only use process.env
// Configuration is managed by SecureConfigManager
function loadEnvironmentVariables() {
  if (!app.isPackaged) {
    // In development: Load from .env file if it exists
    config();
  }
  // In production: Environment variables are set by SecureConfigManager
  // No file-based configuration needed
}

loadEnvironmentVariables();

// Function to build connection string based on auth type
function buildDatabaseUrl(config?: DatabaseConfig): string {
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
      // Azure might use different auth methods
      const clientId = config?.azureClientId || process.env.DB_AZURE_CLIENT_ID;
      if (clientId) {
        connectionString += `;clientId=${clientId}`;
      }
      break;
    }
  }

  return connectionString;
}

// Singleton pattern for Prisma Client
class PrismaService {
  private static instance: PrismaClient | null = null;

  static getInstance(): PrismaClient {
    if (!PrismaService.instance) {
      // Set DATABASE_URL if not already set
      if (!process.env.DATABASE_URL) {
        process.env.DATABASE_URL = buildDatabaseUrl();
      }

      // Set the query engine path dynamically
      const queryEnginePath = getPrismaQueryEnginePath();
      console.log(`Prisma query engine path: ${queryEnginePath}`);

      // Verify the query engine exists
      if (!fs.existsSync(queryEnginePath)) {
        console.error(`Prisma query engine not found at: ${queryEnginePath}`);
        console.error(`Current working directory: ${process.cwd()}`);
        console.error(`Process executable path: ${process.execPath}`);
        console.error(`Resources path: ${process.resourcesPath}`);
        console.error(`App path: ${app.getAppPath()}`);
        console.error(`Is packaged: ${app.isPackaged}`);
      }

      process.env.PRISMA_QUERY_ENGINE_LIBRARY = queryEnginePath;

      PrismaService.instance = new PrismaClient({
        log: ["query", "info", "warn", "error"],
      });
    }
    return PrismaService.instance;
  }

  static async disconnect(): Promise<void> {
    if (PrismaService.instance) {
      await PrismaService.instance.$disconnect();
      PrismaService.instance = null;
    }
  }

  static async reconnectWithConfig(config: DatabaseConfig): Promise<boolean> {
    try {
      // Disconnect existing client
      await this.disconnect();

      // Update DATABASE_URL with new config
      process.env.DATABASE_URL = buildDatabaseUrl(config);

      console.log("New DATABASE_URL:", process.env.DATABASE_URL);

      // Create new instance (will use updated DATABASE_URL)
      const newClient = this.getInstance();

      // Test the connection
      await newClient.$queryRaw`SELECT 1 as test`;

      return true;
    } catch (error) {
      console.error("Failed to reconnect with new config:", error);
      // Reset instance on failure
      this.instance = null;
      return false;
    }
  }
}

export const prisma = PrismaService.getInstance();
export { PrismaService, type DatabaseConfig };
