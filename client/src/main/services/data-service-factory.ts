import { DataService, LocalDatabaseService } from "./database-service.js";

export class DataServiceFactory {
  private static instance: DataService | null = null;

  static createDataService(): DataService {
    if (!this.instance) {
      // Prisma uses DATABASE_URL environment variable - no config needed
      this.instance = new LocalDatabaseService();
    }

    return this.instance;
  }

  static async cleanup(): Promise<void> {
    if (this.instance) {
      await this.instance.disconnect();
      this.instance = null;
    }
  }
}
