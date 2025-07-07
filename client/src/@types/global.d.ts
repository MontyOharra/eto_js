
  type OutputPayloadMapping = {
    testDatabaseConnection: boolean;
    getPositions: Prisma.positionModel[];
  };

  type InputPayloadMapping = {
    testDatabaseConnection: void;
    getPositions: void;
  };

  interface Window {
    electron: {
      testDatabaseConnection: () => Promise<boolean>;
      getPositions: () => Promise<Prisma.positionModel[]>;
    };
  }
