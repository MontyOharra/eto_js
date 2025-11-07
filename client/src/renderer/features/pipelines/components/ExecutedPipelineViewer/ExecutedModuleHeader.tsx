/**
 * ExecutedModuleHeader
 * Header section for executed module showing name and status
 */

import { getTextColor } from "../../utils/moduleUtils";

interface ExecutedModuleHeaderProps {
  moduleName: string;
  moduleColor: string;
  status: "executed" | "failed" | "not_executed";
}

export function ExecutedModuleHeader({
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
      </div>
    </div>
  );
}
