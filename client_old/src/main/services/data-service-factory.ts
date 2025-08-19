import { LocalPrismaDataService } from "./local-prisma-db-service.js";
// If you add new services, import them here:
// import { RemoteApiDataService } from "./remote-api-data-service.js";

import { DataService } from "../../@types/database.js";

export enum DataServiceType {
  /** Default – talks directly to a local/embedded Prisma-managed DB. */
  LocalPrisma = "localPrisma",
  /** Example stub – would proxy requests to a backend REST/GraphQL API. */
  RemoteApi = "remoteApi",
  /** Example stub – useful for unit tests. */
  Mock = "mock",
}

export class DataServiceFactory {
  private static instance: DataService | null = null;

  static createDataService(
    type: DataServiceType = DataServiceType.LocalPrisma
  ): DataService {
    if (!this.instance) {
      switch (type) {
        case DataServiceType.LocalPrisma:
          this.instance = new LocalPrismaDataService();
          break;

        default:
          throw new Error(`Unsupported DataServiceType: ${type}`);
      }
    }

    return this.instance;
  }

  static resetInstance(): void {
    this.instance = null;
  }

  static async cleanup(): Promise<void> {
    if (this.instance) {
      await this.instance.disconnect();
      this.instance = null;
    }
  }
}
