import React from 'react';
import { getSeverityBadgeColors } from '../../utils/formatters';

interface SeverityBadgeProps {
  severity: string | null | undefined;
  size?: 'sm' | 'md' | 'lg';
  showDot?: boolean;
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({
  severity,
  size = 'md',
  showDot = true,
}) => {
  const displaySev = severity ? severity.toUpperCase() : 'UNKNOWN';
  const colors = getSeverityBadgeColors(severity);

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 font-medium',
    md: 'text-xs px-2.5 py-1 font-semibold tracking-wide',
    lg: 'text-sm px-3.5 py-1.5 font-bold tracking-wider',
  }[size];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border transition-all duration-200 ${colors.bg} ${colors.text} ${colors.border} ${sizeClasses}`}
    >
      {showDot && (
        <span
          className={`h-1.5 w-1.5 rounded-full ${colors.dot} animate-pulse`}
        />
      )}
      <span>{displaySev}</span>
    </span>
  );
};
