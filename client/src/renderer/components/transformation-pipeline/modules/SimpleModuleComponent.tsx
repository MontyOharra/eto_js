import React from 'react';

interface SimpleModuleComponentProps {
  color: string;
  position: { x: number; y: number };
  name: string;
}

export const SimpleModuleComponent: React.FC<SimpleModuleComponentProps> = ({
  color,
  position,
  name
}) => {
  return (
    <div
      className="absolute w-12 h-12 rounded-full border-2 border-white shadow-lg cursor-pointer"
      style={{
        backgroundColor: color,
        left: `${position.x}px`,
        top: `${position.y}px`,
        transform: 'translate(-50%, -50%)', // Center the circle on the position
      }}
      title={name}
    />
  );
};