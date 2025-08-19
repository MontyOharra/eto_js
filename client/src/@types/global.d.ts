import { position } from "../../prisma/generated/client/index";
import { DatabaseConfig } from "./database";

// Define PDF object types based on the Python extraction
export interface PdfObject {
  type:
    | "word"
    | "text_line"
    | "table"
    | "rect"
    | "curve"
    | "graphic_line"
    | "image";
  page: number;
  bbox: [number, number, number, number]; // [x0, y0, x1, y1]
  width: number;
  height: number;
  text?: string;
  fontname?: string;
  size?: string | number;
  linewidth?: string | number;
  stroke?: string;
  fill?: string;
  start?: [number, number];
  end?: [number, number];
  points?: [number, number][];
  rows?: number;
  cols?: number;
  preview?: any[][];
  name?: string;
  stream?: string;
  format?: string;
  colorspace?: string;
  bits?: string | number;
  width_pixels?: string | number;
  height_pixels?: string | number;
}

declare global {
  type OutputPayloadMapping = {
    testDatabaseConnection: boolean;
    getPositions: position[];
    setDatabaseConfig: boolean;
    getDatabaseConfig: DatabaseConfig;
    openPdfWindow: boolean;
    getFilePath: string;
    readPdfFile: Uint8Array;
    extractPdfObjects: PdfObject[];
  };

  type InputPayloadMapping = {
    testDatabaseConnection: void;
    getPositions: void;
    setDatabaseConfig: DatabaseConfig;
    getDatabaseConfig: void;
    openPdfWindow: string;
    getFilePath: File;
    readPdfFile: string; // file path
    extractPdfObjects: string; // PDF file path
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
      extractPdfObjects: (pdfFilePath: string) => Promise<PdfObject[]>;
    };
  }
}
