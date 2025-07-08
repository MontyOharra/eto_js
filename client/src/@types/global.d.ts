import { position } from "../../prisma/generated/client/index";
import { DatabaseConfig } from "./database";

declare global {
  type OutputPayloadMapping = {
    testDatabaseConnection: boolean;
    getPositions: position[];
    setDatabaseConfig: boolean;
    getDatabaseConfig: DatabaseConfig;
  };

  type InputPayloadMapping = {
    testDatabaseConnection: void;
    getPositions: void;
    setDatabaseConfig: DatabaseConfig;
    getDatabaseConfig: void;
  };

  interface Window {
    electron: {
      testDatabaseConnection: () => Promise<boolean>;
      getPositions: () => Promise<position[]>;
      setDatabaseConfig: (config: DatabaseConfig) => Promise<boolean>;
      getDatabaseConfig: () => Promise<DatabaseConfig>;
    };
  }
}
