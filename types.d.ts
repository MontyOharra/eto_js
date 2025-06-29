type PythonTestReturn = {
  output: string;
};

type OutputPayloadMapping = {
  pythonTest: PythonTestReturn;
};

type InputPayloadMapping = {
  pythonTest: string;
}

interface Window {
  electron: {
    pythonTest: (testType: string) => Promise<PythonTestReturn>;
  };
}