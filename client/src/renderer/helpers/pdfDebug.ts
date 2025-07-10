/* eslint-disable @typescript-eslint/no-explicit-any */
import { TextContent, TextItem } from "pdfjs-dist/types/src/display/api";
// @ts-expect-error – OPS constant import (runtime only)
import { OPS } from "pdfjs-dist/build/pdf";

interface ViewportLike {
  convertToViewportRectangle: (rect: number[]) => number[];
}

export interface PageObjectSummary {
  type: "text" | "annotation";
  value?: string;
  subtype?: string;
  rect: { left: number; top: number; right: number; bottom: number };
}

/**
 * Maps pdf.js operator list to readable array of { op, args }
 */
export function decodeOperatorList(opList: any) {
  const codeToName: Record<number, string> = {};
  Object.entries(OPS).forEach(([k, v]) => {
    codeToName[v as number] = k;
  });

  return opList.fnArray.map((fn: number, idx: number) => ({
    op: codeToName[fn] || `OP_${fn}`,
    args: opList.argsArray[idx],
  }));
}

/**
 * Builds a simplified list of page objects (text items + annotations) with viewport-based rectangles.
 */
export function buildPageObjects(
  textContent: TextContent,
  annotations: any[],
  viewport: ViewportLike,
  borderOffset = 0
): PageObjectSummary[] {
  const objects: PageObjectSummary[] = [];

  // Text items
  for (const item of textContent.items as TextItem[]) {
    const [, , , , x, y] = item.transform as number[];
    const [vx1, vy1, vx2, vy2] = viewport.convertToViewportRectangle([
      x,
      y,
      x + item.width,
      y + item.height,
    ]);
    objects.push({
      type: "text",
      value: item.str,
      rect: {
        left: Math.min(vx1, vx2) + borderOffset,
        top: Math.min(vy1, vy2) + borderOffset,
        right: Math.max(vx1, vx2) + borderOffset,
        bottom: Math.max(vy1, vy2) + borderOffset,
      },
    });
  }

  // Annotations
  for (const ann of annotations) {
    const [x1, y1, x2, y2] = viewport.convertToViewportRectangle(ann.rect);
    objects.push({
      type: "annotation",
      subtype: ann.subtype,
      rect: {
        left: Math.min(x1, x2) + borderOffset,
        top: Math.min(y1, y2) + borderOffset,
        right: Math.max(x1, x2) + borderOffset,
        bottom: Math.max(y1, y2) + borderOffset,
      },
    });
  }

  return objects;
}

/**
 * Extract low-level showText operations with their preceding moveText coordinates.
 * Very simplified – assumes each showText is preceded by a moveText that sets
 * the position (tx, ty). The resulting objects give you the raw glyph run and
 * its origin before any scaling.
 */
export function extractShowTextRuns(
  decodedOps: { op: string; args: any[] }[],
  viewport: ViewportLike,
  borderOffset = 0
) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const runs: PageObjectSummary[] = [];
  let currX = 0;
  let currY = 0;

  decodedOps.forEach(({ op, args }) => {
    if (op === "moveText" || op === "setTextMatrix") {
      currX = args[0];
      currY = args[1];
    } else if (op === "showText" || op === "showSpacedText") {
      const arg0 = args[0];
      let glyphs: any[] = [];
      if (typeof arg0 === "string") {
        glyphs = [{ str: arg0, width: arg0.length * 5 }];
      } else if (Array.isArray(arg0)) {
        glyphs = arg0;
      } else if (arg0 && typeof arg0 === "object") {
        glyphs = [arg0];
      }

      let str = "";
      let advance = 0;
      glyphs.forEach((g) => {
        if (typeof g === "string") {
          str += g;
        } else if (typeof g === "object" && g.str) {
          str += g.str;
          advance += g.width || 0;
        } else if (typeof g === "number") {
          // spacing adjustment
          advance += g;
        }
      });

      const estWidth = advance || str.length * 5;

      const [vx1, vy1, vx2, vy2] = viewport.convertToViewportRectangle([
        currX,
        currY,
        currX + estWidth,
        currY + 10,
      ]);

      runs.push({
        type: "text",
        value: str.trim(),
        rect: {
          left: Math.min(vx1, vx2) + borderOffset,
          top: Math.min(vy1, vy2) + borderOffset,
          right: Math.max(vx1, vx2) + borderOffset,
          bottom: Math.max(vy1, vy2) + borderOffset,
        },
      });
    }
  });

  return runs;
}
