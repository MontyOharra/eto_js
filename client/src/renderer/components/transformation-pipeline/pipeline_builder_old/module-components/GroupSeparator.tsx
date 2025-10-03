import React from 'react';

interface GroupSeparatorProps {
  groupLabel?: string;
  isFirst?: boolean;
}

export const GroupSeparator: React.FC<GroupSeparatorProps> = ({
  groupLabel,
  isFirst = false
}) => {
  if (isFirst) return null;

  return (
    <div className="flex items-center justify-center py-1">
      <div className="flex-1 h-px bg-gray-600"></div>
      {groupLabel && (
        <>
          <span className="px-2 text-xs text-gray-500 bg-gray-800">{groupLabel}</span>
          <div className="flex-1 h-px bg-gray-600"></div>
        </>
      )}
    </div>
  );
};