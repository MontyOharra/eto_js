import { position } from "../../prisma/generated/client/index";
import { DatabaseConfig } from "./types";

declare global {
  type OutputPayloadMapping = {
    testDatabaseConnection: boolean;
    getPositions: position[];
    updateDatabaseConfig: boolean;
    loadDatabaseConfig: DatabaseConfig;
  };

  type InputPayloadMapping = {
    testDatabaseConnection: void;
    getPositions: void;
    updateDatabaseConfig: DatabaseConfig;
    loadDatabaseConfig: void;
  };

  interface Window {
    electron: {
      testDatabaseConnection: () => Promise<boolean>;
      getPositions: () => Promise<position[]>;
      updateDatabaseConfig: (config: DatabaseConfig) => Promise<boolean>;
      loadDatabaseConfig: () => Promise<DatabaseConfig>;
    };
  }
}
