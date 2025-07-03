type OutputPayloadMapping = {
  testDatabaseConnection: boolean;
  getPositions: position[];
};

type InputPayloadMapping = {
  testDatabaseConnection: void;
  getPositions: void;
};

interface Window {
  electron: {
    testDatabaseConnection: () => Promise<boolean>;
    getPositions: () => Promise<position[]>;
  };
}

