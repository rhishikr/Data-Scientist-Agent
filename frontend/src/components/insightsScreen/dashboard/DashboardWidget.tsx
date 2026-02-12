// dashboard/DashboardWidget.tsx
import React from "react";
import { GripVertical, X, ChevronUp, ChevronDown } from "lucide-react";

export function DashboardWidget({
  children,
  isCustomizing,
  onRemove,
  onMoveUp,
  onMoveDown,
  canMoveUp,
  canMoveDown,
  className = "",
}: {
  children: React.ReactNode;
  isCustomizing: boolean;
  onRemove?: () => void;
  onMoveUp?: () => void;
  onMoveDown?: () => void;
  canMoveUp?: boolean;
  canMoveDown?: boolean;
  className?: string;
}) {
  return (
    <div className={`relative group ${className}`}>
      {isCustomizing && (
        <>
          <div className="absolute -left-3 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity z-10">
            <div className="bg-slate-200 rounded p-1 shadow-sm">
              <GripVertical className="size-4 text-slate-600" />
            </div>
          </div>

          <button
            onClick={onRemove}
            className="absolute -right-2 -top-2 opacity-0 group-hover:opacity-100 transition-opacity bg-red-500 hover:bg-red-600 text-white rounded-full p-1 shadow-md z-10"
            title="Remove widget"
          >
            <X className="size-3" />
          </button>

          <div className="absolute -right-2 top-8 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col gap-1 z-10">
            {canMoveUp && (
              <button
                onClick={onMoveUp}
                className="bg-teal-500 hover:bg-teal-600 text-white rounded-full p-1 shadow-md"
                title="Move up"
              >
                <ChevronUp className="size-3" />
              </button>
            )}
            {canMoveDown && (
              <button
                onClick={onMoveDown}
                className="bg-teal-500 hover:bg-teal-600 text-white rounded-full p-1 shadow-md"
                title="Move down"
              >
                <ChevronDown className="size-3" />
              </button>
            )}
          </div>

          <div className="absolute inset-0 border-2 border-dashed border-teal-300 rounded-lg pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity" />
        </>
      )}
      {children}
    </div>
  );
}
