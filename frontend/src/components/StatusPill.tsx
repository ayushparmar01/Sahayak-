import React from 'react';

interface StatusPillProps {
  status: 'VERIFIED' | 'REVISION_PENDING' | 'OUTDATED' | 'UNKNOWN' | 'ACTIVE' | 'DRAFT' | string;
  label?: string;
}

export const StatusPill: React.FC<StatusPillProps> = ({ status, label }) => {
  const getStyles = () => {
    switch (status) {
      case 'VERIFIED':
      case 'ACTIVE':
        return 'bg-emerald-100 text-emerald-800 border-emerald-300';
      case 'REVISION_PENDING':
      case 'DRAFT':
        return 'bg-amber-100 text-amber-800 border-amber-300';
      case 'OUTDATED':
        return 'bg-rose-100 text-rose-800 border-rose-300';
      default:
        return 'bg-stone-100 text-stone-700 border-stone-300';
    }
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getStyles()}`}
    >
      {label || status}
    </span>
  );
};
