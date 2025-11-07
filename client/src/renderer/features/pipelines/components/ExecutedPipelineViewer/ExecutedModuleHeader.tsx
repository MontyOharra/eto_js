/**
 * ExecutedModuleHeader
 * Header section for executed module showing name and status
 */

import { getTextColor } from "../../utils/moduleUtils";

interface ExecutedModuleHeaderProps {
  moduleId: string;
  moduleName: string;
  moduleColor: string;
}

export function ExecutedModuleHeader({
  moduleId,
  moduleName,
  moduleColor,
}: ExecutedModuleHeaderProps) {
  const textColor = getTextColor(moduleColor);

  return (
    <div
      className="px-4 py-2 rounded-t-lg border-b border-gray-600"
      style={{ backgroundColor: moduleColor }}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold" style={{ color: textColor }}>
          {moduleName}
        </h3>
        <span className="text-xs font-mono opacity-75" style={{ color: textColor }}>
          {moduleId}
        </span>
      </div>
    </div>
  );
}
