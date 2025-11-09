/**
 * ModuleHeader Component
 * Displays module title, ID, and delete button
 */

import { ModuleTemplate } from "../../../modules/types";
import { ModuleInstance } from "../../types";
import { getTextColor } from "../../utils/moduleUtils";

export interface ModuleHeaderProps {
  moduleInstance: ModuleInstance;
  template: ModuleTemplate;
  onDeleteModule?: (moduleId: string) => void;
}

/**
 * Check if a color is reddish (to avoid conflict with red hover state)
 * Returns true if the color is in the red hue range
 */
function isReddishColor(hexColor: string): boolean {
  const hex = hexColor.replace("#", "");
  const r = parseInt(hex.substr(0, 2), 16);
  const g = parseInt(hex.substr(2, 2), 16);
  const b = parseInt(hex.substr(4, 2), 16);

  // Convert to HSL to check hue
  const rNorm = r / 255;
  const gNorm = g / 255;
  const bNorm = b / 255;

  const max = Math.max(rNorm, gNorm, bNorm);
  const min = Math.min(rNorm, gNorm, bNorm);
  const delta = max - min;

  if (delta === 0) return false; // grayscale

  let hue = 0;
  if (max === rNorm) {
    hue = ((gNorm - bNorm) / delta) % 6;
  }

  hue = hue * 60;
  if (hue < 0) hue += 360;

  // Red is around 0-30 degrees and 330-360 degrees
  return (hue >= 0 && hue <= 30) || (hue >= 330 && hue <= 360);
}

export function ModuleHeader({
  moduleInstance,
  template,
  onDeleteModule,
}: ModuleHeaderProps) {
  const headerColor = template.color || "#4B5563";
  const textColor = getTextColor(headerColor);

  // Use darker red if header is already reddish
  const isReddish = isReddishColor(headerColor);
  const hoverBgColor = isReddish ? "#7F1D1D" : "#EF4444"; // red-900 or red-500

  return (
    <>
      <style>{`
        .module-delete-btn-${moduleInstance.module_instance_id}:hover {
          background-color: ${hoverBgColor} !important;
        }
      `}</style>
      <div
        className="px-4 py-2 rounded-t-lg border-b border-gray-600"
        style={{ backgroundColor: headerColor }}
      >
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold" style={{ color: textColor }}>
            {template.title}
          </h3>
          <div className="flex items-center gap-2">
            <span
              className="text-xs font-mono opacity-75"
              style={{ color: textColor }}
            >
              {moduleInstance.module_instance_id}
            </span>
            {onDeleteModule && (
              <button
                onClick={() => onDeleteModule(moduleInstance.module_instance_id)}
                className={`module-delete-btn-${moduleInstance.module_instance_id} p-1 rounded transition-all`}
                style={{ color: textColor }}
                title="Delete module"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
