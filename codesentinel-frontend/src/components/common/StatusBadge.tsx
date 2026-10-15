import React from 'react';
import { CheckCircle2, AlertTriangle, Clock, RefreshCw } from 'lucide-react';

interface StatusBadgeProps {
  status: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const norm = status?.toLowerCase() || 'unknown';

  if (norm === 'completed' || norm === 'success') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
        <span>Completed</span>
      </span>
    );
  }

  if (norm === 'running' || norm === 'scanning') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
        <RefreshCw className="w-3.5 h-3.5 text-indigo-400 animate-spin" />
        <span>Running</span>
      </span>
    );
  }

  if (norm === 'failed' || norm === 'failure') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/30">
        <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
        <span>Failed</span>
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700">
      <Clock className="w-3.5 h-3.5 text-slate-400" />
      <span className="capitalize">{status}</span>
    </span>
  );
};
