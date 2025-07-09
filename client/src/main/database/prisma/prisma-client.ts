import { PrismaClient } from "../../../../prisma/generated/client/index.js";
import { getPrismaQueryEnginePath } from "../../helpers/utils.js";
import { buildDatabaseUrl } from "./helpers.js";
import type { DatabaseConfig } from "../../../@types/database.js";

// Singleton wrapper around PrismaClient so we only instantiate it once.
class PrismaService {
  private static instance: PrismaClient | null = null;

  static getInstance(): PrismaClient {
    if (!PrismaService.instance) {
      process.env.PRISMA_QUERY_ENGINE_LIBRARY = getPrismaQueryEnginePath();

      PrismaService.instance = new PrismaClient({
        log: ["warn", "error"],
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
      // Disconnect existing client, if any
      await this.disconnect();

      // Update DATABASE_URL for Prisma using the shared helper
      process.env.DATABASE_URL = buildDatabaseUrl(config);
      console.log("New DATABASE_URL:", process.env.DATABASE_URL);

      // Create a fresh instance – this will pick up the new env var
      const newClient = this.getInstance();

      // Smoke-test the connection
      await newClient.$queryRaw`SELECT 1 as test`;

      return true;
    } catch (error) {
      console.error("Failed to reconnect with new config:", error);
      this.instance = null;
      return false;
    }
  }
}

/** Returns the singleton Prisma client (same as PrismaService.getInstance). */
export function getPrisma() {
  return PrismaService.getInstance();
}

export { PrismaService };
// Re-export the type so callers can keep importing it from here.
export type { DatabaseConfig };
