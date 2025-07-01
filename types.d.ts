type PythonTestReturn = {
  output: string;
};

type OutputPayloadMapping = {
  pythonTest: PythonTestReturn;
};

type InputPayloadMapping = {
  pythonTest: string;
}

type Email = {
  senderAddress: string;
  subject: string;
  pdfAttachments: string[];
}

interface Window {
  electron: {
    pythonTest: (testType: string) => Promise<PythonTestReturn>;
  };
}