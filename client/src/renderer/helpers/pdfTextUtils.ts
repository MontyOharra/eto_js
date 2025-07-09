import { TextContent, TextItem } from "pdfjs-dist/types/src/display/api";

/**
 * Extracts the textual value that appears on the same horizontal line as `label`
 * and to the right of it.
 *
 * Heuristics:
 * 1. Find the text item whose cleaned string matches `label` (case-insensitive).
 * 2. Use its baseline (y coordinate) to find other items on the same line
 *    (within `yTolerance` user-space units).
 * 3. From those items keep only ones whose left edge (x) is after the label's
 *    right edge.
 * 4. Sort the remaining items left-to-right and join their `str` values.
 *
 * @param textContent TextContent returned by `page.getTextContent()`.
 * @param label       The exact label text to look for (case-insensitive).
 * @param yTolerance  Allowed baseline deviation when matching the same line.
 */
export function extractValueForLabel(
  textContent: TextContent,
  label: string,
  yTolerance = 2
): string | null {
  // Normalise helper
  const norm = (s: string) => s.trim().toLowerCase();
  const labelNorm = norm(label);

  // Find the label item first
  let labelItem: TextItem | undefined;
  for (const item of textContent.items as TextItem[]) {
    if (norm(item.str) === labelNorm) {
      labelItem = item;
      break;
    }
  }
  if (!labelItem) return null;

  const [, , , , e, f] = labelItem.transform as number[];
  const labelX = e;
  const labelRight = labelX + labelItem.width;
  const labelY = f; // baseline

  // Collect candidate items on same line
  const sameLine: TextItem[] = [];
  for (const item of textContent.items as TextItem[]) {
    const [, , , , x, y] = item.transform as number[];
    if (Math.abs(y - labelY) <= yTolerance && x > labelRight) {
      sameLine.push(item);
    }
  }

  // Sort left-to-right
  sameLine.sort((i1, i2) => {
    const x1 = (i1.transform as number[])[4];
    const x2 = (i2.transform as number[])[4];
    return x1 - x2;
  });

  if (sameLine.length === 0) return null;
  return (
    sameLine
      .map((i) => i.str)
      .join("")
      .trim() || null
  );
}

/**
 * Dump a concise view of each TextItem to the console for debugging.
 * Shows: index, str, x, y, width, height, fontName.
 */
export function debugDumpTextContent(
  textContent: TextContent,
  limit = 100
): void {
  console.groupCollapsed(`pdfTextUtils: first ${limit} text items`);
  (textContent.items as TextItem[]).slice(0, limit).forEach((item, idx) => {
    const [, , , , x, y] = item.transform as number[];
    // eslint-disable-next-line no-console
    console.log(
      `#${idx.toString().padStart(3)}  (${x.toFixed(1)}, ${y.toFixed(1)})  w=${item.width.toFixed(
        1
      )}  h=${item.height.toFixed(1)}  "${item.str}"  font=${item.fontName}`
    );
  });
  console.groupEnd();
}

/**
 * Like extractValueForLabel but also returns the bounding rectangle of the
 * value (in PDF user-space units).
 */
export function extractValueBoxForLabel(
  textContent: TextContent,
  label: string,
  yTolerance = 2
): {
  value: string;
  rect: { left: number; top: number; right: number; bottom: number };
} | null {
  // Reuse extractValueForLabel logic but collect items
  const norm = (s: string) => s.trim().toLowerCase();
  const labelNorm = norm(label);

  let labelItem: TextItem | undefined;
  for (const item of textContent.items as TextItem[]) {
    if (norm(item.str) === labelNorm) {
      labelItem = item;
      break;
    }
  }
  if (!labelItem) return null;

  const [, , , , xLabel, yLabel] = labelItem.transform as number[];
  const labelRight = xLabel + labelItem.width;

  const candidateItems: TextItem[] = [];
  for (const item of textContent.items as TextItem[]) {
    const [, , , , x, y] = item.transform as number[];
    if (Math.abs(y - yLabel) <= yTolerance && x > labelRight) {
      candidateItems.push(item);
    }
  }

  if (candidateItems.length === 0) return null;

  // Sort and build value string
  candidateItems.sort(
    (i1, i2) => (i1.transform as number[])[4] - (i2.transform as number[])[4]
  );
  const value = candidateItems
    .map((i) => i.str)
    .join("")
    .trim();

  // Compute bounding rect
  let left = Infinity,
    top = Infinity,
    right = -Infinity,
    bottom = -Infinity;
  for (const item of candidateItems) {
    const [, , , , ix, iy] = item.transform as number[];
    left = Math.min(left, ix);
    right = Math.max(right, ix + item.width);
    // pdf.js baseline is iy, top for CSS is iy+item.height? Actually user-space baseline, top is iy? We'll treat top as iy.
    const t = iy;
    const b = iy - item.height;
    top = Math.max(top, t);
    bottom = Math.min(bottom, b);
  }

  return {
    value,
    rect: {
      left,
      top,
      right,
      bottom,
    },
  };
}

/**
 * Find the first TextItem whose `str` value exactly matches `text` (case-insensitive by default).
 * Returns the raw TextItem object so callers can inspect its transform, width, etc.
 */
export function findTextItem(
  textContent: TextContent,
  text: string,
  options: { caseInsensitive?: boolean } = { caseInsensitive: true }
): TextItem | null {
  const { caseInsensitive = true } = options;
  const cmp = caseInsensitive
    ? (a: string, b: string) =>
        a.trim().toLowerCase() === b.trim().toLowerCase()
    : (a: string, b: string) => a === b;

  for (const item of textContent.items as TextItem[]) {
    if (cmp(item.str, text)) {
      return item;
    }
  }
  return null;
}
