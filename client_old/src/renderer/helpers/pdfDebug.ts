// @ts-expect-error – OPS constant import (runtime only)
import { OPS } from "pdfjs-dist/build/pdf";

interface OperatorList {
  fnArray: number[];
  argsArray: unknown[][];
}

/**
 * Maps pdf.js operator list to readable array of { op, args }
 */
export function decodeOperatorList(opList: OperatorList) {
  const codeToName: Record<number, string> = {};
  Object.entries(OPS).forEach(([k, v]) => {
    codeToName[v as number] = k;
  });

  return opList.fnArray.map((fn: number, idx: number) => ({
    op: codeToName[fn] || `OP_${fn}`,
    args: opList.argsArray[idx],
  }));
}

export interface TextRun {
  value: string | null;
  coords: { x: number; y: number };
  width: number;
  height: number;
}

/**
 * Extract show-text runs grouped by beginText/endText pairs.
 * It walks through the decoded operator list and returns an array containing
 * the extracted string value together with the (x, y) coordinates taken from
 * the most recent `moveText` (or `setTextMatrix`) operation inside each
 * begin/end block.
 */
interface Glyph {
  accent: unknown;
  fontChar: string;
  isInFont: boolean;
  isSpace: boolean;
  operatorListId: unknown;
  originalCharCode: number;
  unicode: string;
  vmetric: unknown;
  width: number;
}

const getGlyphString = (
  showArgs: Glyph[][]
): { text: string; width: number } => {
  /*
   * showArgs[0] can be:
   *  • string
   *  • { str, ... }
   *  • array mixing strings, numbers, and glyph objects
   */
  const container = showArgs[0];
  const glyphs: Glyph[] = Array.isArray(container) ? container : [container];

  let text = "";
  let width = 0;
  for (const g of glyphs) {
    text += g.unicode;
    width += g.width;
  }
  width /= 72;
  return { text, width };
};

export function extractShowTextRuns(
  decodedOps: { op: string; args: unknown[] }[]
): TextRun[] {
  const runs: TextRun[] = [];

  for (let i = 0; i < decodedOps.length; i++) {
    const { op: opName } = decodedOps[i];

    if (opName === "beginText") {
      const currentRun: TextRun = {
        value: "",
        coords: { x: 0, y: 0 },
        width: 0,
        height: 0,
      };

      let foundEnd = false;

      for (i = i + 1; i < decodedOps.length; i++) {
        const { op: innerOp, args: innerArgs } = decodedOps[i];

        if (innerOp === "beginText") {
          throw new Error(
            "Nested beginText encountered before endText – malformed operator list."
          );
        }

        if (innerOp === "setFont") {
          const fontSize = innerArgs[1] as number;
          currentRun.height = fontSize;
          continue;
        }

        if (innerOp === "endText") {
          foundEnd = true;
          runs.push(currentRun);
          break; // exit inner loop, outer loop will continue with next op
        }

        if (
          innerOp === "moveText" ||
          innerOp === "setTextMatrix" /* handles Td/Tm equivalently */
        ) {
          if (innerArgs && innerArgs.length >= 2) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const [x, y] = innerArgs as any[];
            currentRun.coords.x = Number(x);
            currentRun.coords.y = Number(y);
          }
          continue;
        }

        if (innerOp === "showText" || innerOp === "showSpacedText") {
          const { text, width } = getGlyphString(
            innerArgs as unknown as Glyph[][]
          );
          currentRun.value += text;
          currentRun.width += width * currentRun.height / 14.04;
          // Estimate height roughly at 0.7 * font size (assume 12pt default)
          if (currentRun.height === 0) {
            currentRun.height = 10; // fallback
          }
          continue;
        }
        // other operators inside text object are ignored
      }

      if (!foundEnd) {
        throw new Error(
          "Operator list exhausted without encountering endText after beginText."
        );
      }
    }
  }

  return runs;
}
