import React, { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
}

export const Card: React.FC<CardProps> = ({ children, className = '', onClick }) => {
  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-xl border border-stone-200 shadow-sm hover:shadow transition-shadow overflow-hidden ${
        onClick ? 'cursor-pointer hover:border-emerald-500' : ''
      } ${className}`}
    >
      {children}
    </div>
  );
};
