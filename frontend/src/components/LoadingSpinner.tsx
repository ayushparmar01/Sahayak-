import React from 'react';

interface LoadingSpinnerProps {
  label?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ label = 'लोड हो रहा है...' }) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-stone-600">
      <div className="w-8 h-8 border-3 border-stone-300 border-t-emerald-700 rounded-full animate-spin" />
      <span className="mt-3 text-xs font-medium text-stone-500">{label}</span>
    </div>
  );
};
