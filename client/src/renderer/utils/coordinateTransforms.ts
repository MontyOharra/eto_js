/**
 * Coordinate Transformation Utilities
 *
 * Handles coordinate transformations for different PDF object types.
 * Text objects need Y-coordinate flipping due to different coordinate systems,
 * while graphics and images use direct coordinates.
 */

export type BBox = [number, number, number, number]; // [x0, y0, x1, y1]

export interface CoordinateTransformConfig {
  needsCoordinateFlip: boolean;
  scale?: number;
}

/**
 * Transform coordinates from PDF space to screen space
 *
 * @param bbox - Bounding box coordinates [x0, y0, x1, y1]
 * @param pageHeight - Height of the PDF page (unscaled)
 * @param needsFlip - Whether to flip Y coordinates (true for text, false for graphics/images)
 * @param scale - Scale factor for rendering (default: 1)
 * @returns Transformed coordinates
 */
export const transformCoordinates = (
  bbox: BBox,
  pageHeight: number,
  needsFlip: boolean,
  scale: number = 1
): BBox => {
  if (needsFlip) {
    // Text objects: flip Y coordinates and apply scale
    return [
      bbox[0] * scale,                    // x0 stays the same
      (pageHeight - bbox[3]) * scale,     // y0 = pageHeight - original_y1 (flip Y)
      bbox[2] * scale,                    // x1 stays the same
      (pageHeight - bbox[1]) * scale      // y1 = pageHeight - original_y0 (flip Y)
    ];
  } else {
    // Graphics and images: use direct coordinates with scale
    return [
      bbox[0] * scale,
      bbox[1] * scale,
      bbox[2] * scale,
      bbox[3] * scale
    ];
  }
};

/**
 * Transform coordinates from screen space back to PDF space
 * Used when drawing extraction fields
 *
 * @param screenBbox - Screen coordinates [x0, y0, x1, y1]
 * @param pageHeight - Height of the PDF page (unscaled)
 * @param needsFlip - Whether to flip Y coordinates back (true for text, false for graphics/images)
 * @param scale - Scale factor for rendering (default: 1)
 * @returns PDF coordinates
 */
export const transformToPdfCoordinates = (
  screenBbox: BBox,
  pageHeight: number,
  needsFlip: boolean,
  scale: number = 1
): BBox => {
  // First unscale the coordinates
  const unscaled: BBox = [
    screenBbox[0] / scale,
    screenBbox[1] / scale,
    screenBbox[2] / scale,
    screenBbox[3] / scale
  ];

  if (needsFlip) {
    // Flip Y coordinates back to PDF space
    return [
      unscaled[0],                    // x0 stays the same
      pageHeight - unscaled[3],       // y0 = pageHeight - screen_y1 (flip Y back)
      unscaled[2],                    // x1 stays the same
      pageHeight - unscaled[1]        // y1 = pageHeight - screen_y0 (flip Y back)
    ];
  } else {
    // Direct coordinates
    return unscaled;
  }
};

/**
 * Normalize bounding box coordinates to ensure x0,y0 is top-left and x1,y1 is bottom-right
 *
 * @param bbox - Bounding box that may have negative width/height
 * @returns Normalized bounding box
 */
export const normalizeBoundingBox = (bbox: BBox): BBox => {
  const [x0, y0, x1, y1] = bbox;
  return [
    Math.min(x0, x1), // left
    Math.min(y0, y1), // top
    Math.max(x0, x1), // right
    Math.max(y0, y1)  // bottom
  ];
};

/**
 * Calculate the center point of a bounding box
 *
 * @param bbox - Bounding box coordinates
 * @returns Center point [x, y]
 */
export const getBoundingBoxCenter = (bbox: BBox): [number, number] => {
  const [x0, y0, x1, y1] = bbox;
  return [
    (x0 + x1) / 2,
    (y0 + y1) / 2
  ];
};

/**
 * Calculate the dimensions of a bounding box
 *
 * @param bbox - Bounding box coordinates
 * @returns Dimensions [width, height]
 */
export const getBoundingBoxDimensions = (bbox: BBox): [number, number] => {
  const [x0, y0, x1, y1] = bbox;
  return [
    Math.abs(x1 - x0), // width
    Math.abs(y1 - y0)  // height
  ];
};

/**
 * Check if a point is inside a bounding box
 *
 * @param point - Point coordinates [x, y]
 * @param bbox - Bounding box coordinates
 * @returns True if point is inside the bounding box
 */
export const isPointInBoundingBox = (point: [number, number], bbox: BBox): boolean => {
  const [px, py] = point;
  const [x0, y0, x1, y1] = normalizeBoundingBox(bbox);

  return px >= x0 && px <= x1 && py >= y0 && py <= y1;
};

/**
 * Check if two bounding boxes intersect
 *
 * @param bbox1 - First bounding box
 * @param bbox2 - Second bounding box
 * @returns True if the bounding boxes intersect
 */
export const doBoundingBoxesIntersect = (bbox1: BBox, bbox2: BBox): boolean => {
  const [x1_0, y1_0, x1_1, y1_1] = normalizeBoundingBox(bbox1);
  const [x2_0, y2_0, x2_1, y2_1] = normalizeBoundingBox(bbox2);

  return !(x1_1 < x2_0 || x2_1 < x1_0 || y1_1 < y2_0 || y2_1 < y1_0);
};

/**
 * Object type configurations for coordinate transformations
 */
export const OBJECT_COORDINATE_CONFIGS = {
  // Text objects need Y-coordinate flipping
  text_words: { needsCoordinateFlip: true },
  text_lines: { needsCoordinateFlip: true },

  // Graphics use direct coordinates
  graphic_rects: { needsCoordinateFlip: false },
  graphic_lines: { needsCoordinateFlip: false },
  graphic_curves: { needsCoordinateFlip: false },

  // Images use direct coordinates
  images: { needsCoordinateFlip: false },

  // Tables use direct coordinates
  tables: { needsCoordinateFlip: false }
} as const;

export type ObjectType = keyof typeof OBJECT_COORDINATE_CONFIGS;

/**
 * Get coordinate transformation config for an object type
 *
 * @param objectType - Type of PDF object
 * @returns Coordinate transformation configuration
 */
export const getCoordinateConfig = (objectType: ObjectType): CoordinateTransformConfig => {
  return OBJECT_COORDINATE_CONFIGS[objectType];
};