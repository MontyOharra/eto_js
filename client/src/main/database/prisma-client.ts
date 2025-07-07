import { PrismaClient } from "../../../prisma/generated/client/index.js";
import { config } from "dotenv";
import { getPrismaQueryEnginePath } from "../helpers/utils.js";
import fs from "fs";
import { app } from "electron";
import path from "path";

// Load environment variables from appropriate location
function loadEnvironmentVariables() {
  if (app.isPackaged) {
    // In packaged app: Look for config in user data directory
    const userDataPath = app.getPath("userData");
    const configPath = path.join(userDataPath, ".env");

    if (fs.existsSync(configPath)) {
      console.log(`Loading config from: ${configPath}`);
      config({ path: configPath });
    } else {
      console.log(`Config file not found at: ${configPath}`);
      console.log(
        "Create a .env file in the app data directory with your database settings"
      );

      // Create a sample config file
      const sampleConfig = `# Database Configuration
# Copy this file to: ${configPath}
# And update with your database settings

DB_AUTH_TYPE=windows
DB_SERVER=localhost
DB_PORT=1433
DB_NAME=HTC
DB_ENCRYPT=optional
DB_TRUST_SERVER_CERTIFICATE=true

# For SQL Server authentication, uncomment and set:
# DB_USER=your_username
# DB_PASSWORD=your_password

# For Azure AD authentication, uncomment and set:
# DB_AZURE_USER=your_azure_user
# DB_AZURE_PASSWORD=your_azure_password
# DB_AZURE_CLIENT_ID=your_client_id
`;

      try {
        fs.writeFileSync(path.join(userDataPath, ".env.example"), sampleConfig);
        console.log(
          `Sample config created at: ${path.join(userDataPath, ".env.example")}`
        );
      } catch (error) {
        console.error("Failed to create sample config:", error);
      }
    }
  } else {
    // In development: Use local .env file
    config();
  }
}

loadEnvironmentVariables();

// Function to build connection string based on auth type
function buildDatabaseUrl(): string {
  const authType = process.env.DB_AUTH_TYPE || "windows";
  const server = process.env.DB_SERVER || "localhost";
  const port = process.env.DB_PORT || "1433";
  const database = process.env.DB_NAME || "HTC";
  const encrypt = process.env.DB_ENCRYPT || "optional";
  const trustCert = process.env.DB_TRUST_SERVER_CERTIFICATE || "true";

  let connectionString = `sqlserver://${server}:${port};database=${database};encrypt=${encrypt};trustServerCertificate=${trustCert}`;

  switch (authType.toLowerCase()) {
    case "windows":
    case "integrated": {
      connectionString += ";integratedSecurity=true";
      break;
    }

    case "sql":
    case "sqlserver": {
      const username = process.env.DB_USER;
      const password = process.env.DB_PASSWORD;
      if (username && password) {
        connectionString += `;username=${username};password=${password}`;
      }
      break;
    }

    case "azure":
    case "azuread": {
      const azureUser = process.env.DB_AZURE_USER;
      const azurePassword = process.env.DB_AZURE_PASSWORD;
      if (azureUser && azurePassword) {
        connectionString += `;username=${azureUser};password=${azurePassword}`;
      }
      // Azure might use different auth methods
      const clientId = process.env.DB_AZURE_CLIENT_ID;
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
}

export const prisma = PrismaService.getInstance();
export { PrismaService };
