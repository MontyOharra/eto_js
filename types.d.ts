type PythonTestReturn = {
  output: string;
};

type EventPayloadMapping = {
  pythonTest: PythonTestReturn;
};

interface Window {
  electron: {
    pythonTest: () => Promise<PythonTestReturn>;
  };
}