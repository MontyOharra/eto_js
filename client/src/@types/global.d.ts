import { position } from "../../prisma/generated/client/index";
import { DatabaseConfig } from "./database";

declare global {
  type OutputPayloadMapping = {
    testDatabaseConnection: boolean;
    getPositions: position[];
    setDatabaseConfig: boolean;
    getDatabaseConfig: DatabaseConfig;
    openPdfWindow: boolean;
    getFilePath: string;
    readPdfFile: Uint8Array;
  };

  type InputPayloadMapping = {
    testDatabaseConnection: void;
    getPositions: void;
    setDatabaseConfig: DatabaseConfig;
    getDatabaseConfig: void;
    openPdfWindow: string;
    getFilePath: File;
    readPdfFile: string; // file path
  };

  interface Window {
    electron: {
      testDatabaseConnection: () => Promise<boolean>;
      getPositions: () => Promise<position[]>;
      setDatabaseConfig: (config: DatabaseConfig) => Promise<boolean>;
      getDatabaseConfig: () => Promise<DatabaseConfig>;
      openPdfWindow: (filePath: string) => Promise<boolean>;
      getFilePath: (file: File) => string;
      readPdfFile: (filePath: string) => Promise<Uint8Array>;
    };
  }
}
