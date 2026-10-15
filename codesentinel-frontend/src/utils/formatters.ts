export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).format(d);
  } catch {
    return dateStr;
  }
}

export function formatRelativeTime(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  try {
    const d = new Date(dateStr);
    const now = new Date();
    const diffSec = Math.floor((now.getTime() - d.getTime()) / 1000);
    if (diffSec < 60) return `${diffSec}s ago`;
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
    return `${Math.floor(diffSec / 86400)}d ago`;
  } catch {
    return dateStr;
  }
}

export function formatPercent(val: number | null | undefined): string {
  if (val == null || isNaN(val)) return '0.0%';
  return `${(val * 100).toFixed(1)}%`;
}

export function getSeverityWeight(severity: string | null | undefined): number {
  switch (severity?.toLowerCase()) {
    case 'critical': return 4;
    case 'high': return 3;
    case 'medium': return 2;
    case 'low': return 1;
    default: return 0;
  }
}

export function getSeverityBadgeColors(severity: string | null | undefined): {
  bg: string;
  text: string;
  border: string;
  dot: string;
  glow: string;
} {
  switch (severity?.toLowerCase()) {
    case 'critical':
      return {
        bg: 'bg-rose-500/10',
        text: 'text-rose-400',
        border: 'border-rose-500/30',
        dot: 'bg-rose-500',
        glow: 'shadow-[0_0_12px_rgba(244,63,94,0.35)]',
      };
    case 'high':
      return {
        bg: 'bg-amber-500/10',
        text: 'text-amber-400',
        border: 'border-amber-500/30',
        dot: 'bg-amber-500',
        glow: 'shadow-[0_0_12px_rgba(245,158,11,0.35)]',
      };
    case 'medium':
      return {
        bg: 'bg-yellow-500/10',
        text: 'text-yellow-300',
        border: 'border-yellow-500/30',
        dot: 'bg-yellow-400',
        glow: 'shadow-[0_0_12px_rgba(234,179,8,0.35)]',
      };
    case 'low':
      return {
        bg: 'bg-emerald-500/10',
        text: 'text-emerald-400',
        border: 'border-emerald-500/30',
        dot: 'bg-emerald-400',
        glow: 'shadow-[0_0_12px_rgba(16,185,129,0.35)]',
      };
    case 'clean':
    case 'safe':
      return {
        bg: 'bg-cyan-500/10',
        text: 'text-cyan-400',
        border: 'border-cyan-500/30',
        dot: 'bg-cyan-400',
        glow: 'shadow-[0_0_12px_rgba(6,182,212,0.35)]',
      };
    default:
      return {
        bg: 'bg-slate-800/50',
        text: 'text-slate-400',
        border: 'border-slate-700',
        dot: 'bg-slate-500',
        glow: 'none',
      };
  }
}
