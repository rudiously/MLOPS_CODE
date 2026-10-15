import React from 'react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
  fullPage?: boolean;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  text,
  fullPage = false,
}) => {
  const sizeMap = {
    sm: 'h-4 w-4 border-2',
    md: 'h-8 w-8 border-3',
    lg: 'h-12 w-12 border-4',
  }[size];

  const content = (
    <div className="flex flex-col items-center justify-center gap-3">
      <div className="relative">
        <div
          className={`${sizeMap} rounded-full border-slate-700/60 border-t-purple-500 animate-spin`}
        />
        <div
          className={`absolute inset-0 ${sizeMap} rounded-full border-blue-500/30 blur-[2px] animate-pulse`}
        />
      </div>
      {text && (
        <p className="text-xs font-medium uppercase tracking-wider text-slate-400 animate-pulse">
          {text}
        </p>
      )}
    </div>
  );

  if (fullPage) {
    return (
      <div className="min-h-[50vh] w-full flex items-center justify-center">
        {content}
      </div>
    );
  }

  return content;
};
