import { prisma, PrismaService } from "../database/prisma-client.js";
import { position } from "../../../prisma/generated/client/index.js";

export interface DataService {
  testConnection(): Promise<boolean>;
  getPositions(): Promise<position[]>;
  disconnect(): Promise<void>;
}

export class LocalDatabaseService implements DataService {
  constructor() {
    // Prisma uses DATABASE_URL environment variable - no config needed
  }

  async testConnection(): Promise<boolean> {
    try {
      // Simple test query
      await prisma.$queryRaw`SELECT 1 as test`;
      return true;
    } catch (error) {
      console.error("Database connection test failed:", error);
      return false;
    }
  }

  async getPositions(): Promise<position[]> {
    try {
      const positions = await prisma.position.findMany();
      return positions;
    } catch (error) {
      console.error("Failed to fetch customers:", error);
      throw error;
    }
  }

  async disconnect(): Promise<void> {
    await PrismaService.disconnect();
  }
}
