import React from 'react';
import { AlertTriangleIcon } from './Icons';

interface ErrorAlertProps {
  message: string;
  onRetry?: () => void;
}

export const ErrorAlert: React.FC<ErrorAlertProps> = ({ message, onRetry }) => {
  return (
    <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 my-4 flex items-start space-x-3 text-rose-900">
      <AlertTriangleIcon size={20} className="text-rose-600 shrink-0 mt-0.5" />
      <div className="flex-1 text-xs sm:text-sm">
        <span className="font-semibold block">त्रुटि (Error)</span>
        <p className="mt-0.5">{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-2 inline-flex items-center text-xs font-semibold text-rose-800 underline hover:text-rose-950"
          >
            पुनः प्रयास करें (Retry)
          </button>
        )}
      </div>
    </div>
  );
};
