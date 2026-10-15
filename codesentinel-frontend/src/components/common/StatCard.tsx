import React, { ReactNode } from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: ReactNode;
  color?: 'purple' | 'blue' | 'red' | 'amber' | 'emerald' | 'cyan';
  badge?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  color = 'purple',
  badge,
}) => {
  const colorMap = {
    purple: {
      border: 'border-purple-500/20 hover:border-purple-500/40',
      bgGlow: 'from-purple-500/10 to-transparent',
      iconBg: 'bg-purple-500/10 text-purple-400 border border-purple-500/20',
      badge: 'bg-purple-500/10 text-purple-300 border-purple-500/30',
    },
    blue: {
      border: 'border-blue-500/20 hover:border-blue-500/40',
      bgGlow: 'from-blue-500/10 to-transparent',
      iconBg: 'bg-blue-500/10 text-blue-400 border border-blue-500/20',
      badge: 'bg-blue-500/10 text-blue-300 border-blue-500/30',
    },
    red: {
      border: 'border-rose-500/20 hover:border-rose-500/40',
      bgGlow: 'from-rose-500/10 to-transparent',
      iconBg: 'bg-rose-500/10 text-rose-400 border border-rose-500/20',
      badge: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
    },
    amber: {
      border: 'border-amber-500/20 hover:border-amber-500/40',
      bgGlow: 'from-amber-500/10 to-transparent',
      iconBg: 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
      badge: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    },
    emerald: {
      border: 'border-emerald-500/20 hover:border-emerald-500/40',
      bgGlow: 'from-emerald-500/10 to-transparent',
      iconBg: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
      badge: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    },
    cyan: {
      border: 'border-cyan-500/20 hover:border-cyan-500/40',
      bgGlow: 'from-cyan-500/10 to-transparent',
      iconBg: 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20',
      badge: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
    },
  }[color];

  return (
    <div
      className={`relative overflow-hidden rounded-xl border bg-slate-900/70 p-5 backdrop-blur-md transition-all duration-300 hover:shadow-lg ${colorMap.border}`}
    >
      <div
        className={`absolute -top-12 -right-12 h-32 w-32 rounded-full bg-gradient-to-br ${colorMap.bgGlow} blur-2xl pointer-events-none`}
      />

      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-400">
            {title}
          </p>
          <p className="text-2xl font-bold tracking-tight text-white sm:text-3xl font-mono">
            {value}
          </p>
        </div>
        <div className={`rounded-lg p-2.5 ${colorMap.iconBg}`}>
          {icon}
        </div>
      </div>

      {(subtitle || badge) && (
        <div className="mt-3 flex items-center justify-between text-xs">
          {subtitle && <span className="text-slate-400">{subtitle}</span>}
          {badge && (
            <span
              className={`rounded-full px-2 py-0.5 font-medium border ${colorMap.badge}`}
            >
              {badge}
            </span>
          )}
        </div>
      )}
    </div>
  );
};
