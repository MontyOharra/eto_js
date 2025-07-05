import { position } from "../prisma/generated/prisma/index.js";

declare global {
  type OutputPayloadMapping = {
    testDatabaseConnection: boolean;
    getPositions: position[];
    getFarts: fart[];
  };

  type InputPayloadMapping = {
    testDatabaseConnection: void;
    getPositions: void;
    getFarts: void;
  };

  interface Window {
    electron: {
      testDatabaseConnection: () => Promise<boolean>;
      getPositions: () => Promise<position[]>;
    };
  };
}

export {};