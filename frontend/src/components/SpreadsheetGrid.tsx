import type { ReactNode } from 'react';

interface SpreadsheetGridProps {
  title?: string;
  children: ReactNode;
  className?: string;
}

export default function SpreadsheetGrid({ title, children, className = '' }: SpreadsheetGridProps) {
  return (
    <div className={`mb-6 ${className}`}>
      {title && <h3 className="text-sm font-bold text-gray-700 mb-1 px-1">{title}</h3>}
      <div className="overflow-x-auto">
        <table className="border-collapse text-xs min-w-full">
          {children}
        </table>
      </div>
    </div>
  );
}
