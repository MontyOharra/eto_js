import React from 'react';
import { BaseModuleTemplate } from '../../../types/modules';

interface GraphModuleHeaderProps {
  template: BaseModuleTemplate;
  onDeleteClick: (e: React.MouseEvent) => void;
}

export const GraphModuleHeader: React.FC<GraphModuleHeaderProps> = ({
  template,
  onDeleteClick
}) => {
  // Helper function to determine if a color is light or dark
  const isLightColor = (hexColor: string): boolean => {
    // Remove # if present
    const color = hexColor.replace('#', '');
    
    // Parse RGB values
    const r = parseInt(color.substring(0, 2), 16);
    const g = parseInt(color.substring(2, 4), 16);
    const b = parseInt(color.substring(4, 6), 16);
    
    // Calculate luminance using relative luminance formula
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    
    // Return true if light (luminance > 0.5)
    return luminance > 0.5;
  };
  
  const textColor = isLightColor(template.color) ? '#000000' : '#ffffff';
  const deleteButtonHoverBg = isLightColor(template.color) ? 'rgba(220, 38, 38, 0.8)' : '#dc2626';
  return (
    <div>
      {/* Header */}
      <div 
        className="px-4 py-3 rounded-t-lg flex items-center justify-between gap-4"
        style={{ backgroundColor: template.color }}
      >
        <div className="font-medium text-sm flex-1" style={{ color: textColor }}>{template.name}</div>
        <button
          onClick={onDeleteClick}
          className="w-7 h-7 flex items-center justify-center rounded transition-colors"
          style={{ 
            color: textColor,
            ':hover': {
              backgroundColor: deleteButtonHoverBg,
              color: '#ffffff'
            }
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = deleteButtonHoverBg;
            e.currentTarget.style.color = '#ffffff';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'transparent';
            e.currentTarget.style.color = textColor;
          }}
          title="Delete module"
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        </button>
      </div>

      {/* Description */}
      <div className="px-4 py-2 bg-gray-750">
        <div className="text-gray-300 text-xs leading-relaxed">
          {template.description}
        </div>
      </div>
    </div>
  );
};