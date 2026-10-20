import React from 'react';
import { AlertTriangleIcon } from './Icons';

interface EmptyStateProps {
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  actionText,
  onAction,
}) => {
  return (
    <div className="text-center py-12 px-4 bg-white rounded-xl border border-stone-200">
      <div className="w-12 h-12 rounded-full bg-stone-100 flex items-center justify-center mx-auto text-stone-400">
        <AlertTriangleIcon size={24} />
      </div>
      <h3 className="mt-3 text-sm font-semibold text-stone-900">{title}</h3>
      <p className="mt-1 text-xs text-stone-500 max-w-sm mx-auto">{description}</p>
      {actionText && onAction && (
        <button
          onClick={onAction}
          className="mt-4 inline-flex items-center px-3 py-1.5 rounded-md text-xs font-medium bg-emerald-700 text-white hover:bg-emerald-800 transition"
        >
          {actionText}
        </button>
      )}
    </div>
  );
};
