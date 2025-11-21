import { ReactNode } from 'react';

interface TableProps {
  children: ReactNode;
}

interface TableHeaderProps {
  children: ReactNode;
}

interface TableBodyProps {
  children: ReactNode;
}

export function Table({ children }: TableProps) {
  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden flex flex-col h-full">
      {children}
    </div>
  );
}

function TableHeader({ children }: TableHeaderProps) {
  return (
    <div className="py-5 bg-gray-750 border-b-2 border-gray-600 flex-shrink-0">
      {children}
    </div>
  );
}

function TableBody({ children }: TableBodyProps) {
  return (
    <div className="overflow-y-auto flex-1 custom-scrollbar">
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 12px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
          margin-top: 8px;
          margin-bottom: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgb(75 85 99);
          border-radius: 6px;
          border: 3px solid rgb(31 41 55);
          background-clip: padding-box;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgb(107 114 128);
          background-clip: padding-box;
        }
      `}</style>
      {children}
    </div>
  );
}

Table.Header = TableHeader;
Table.Body = TableBody;
