import { PrismaClient } from "../../../prisma/generated/prisma/index.js";

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
        console.log("DATABASE_URL not set, building connection string");
        process.env.DATABASE_URL = buildDatabaseUrl();
        console.log("DATABASE_URL set to", process.env.DATABASE_URL);
      }

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
