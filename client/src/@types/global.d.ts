import { position } from "../../prisma/generated/client/index";
import { DatabaseConfig } from "./database";

declare global {
  type OutputPayloadMapping = {};

  type InputPayloadMapping = {};

  interface Window {
    electron: {};
  }
}
