import React from 'react';
import { Menu, ShieldCheck, ShieldAlert, RefreshCw, Terminal, ExternalLink, Sparkles } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useScan } from '../../context/ScanContext';
import { getApiBaseUrl } from '../../services/api';

interface HeaderProps {
  onToggleSidebar: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar }) => {
  const { health, refreshHealth } = useScan();
  const navigate = useNavigate();
  const location = useLocation();

  const getPageInfo = () => {
    switch (location.pathname) {
      case '/':
      case '/dashboard':
        return { title: 'Security Dashboard', subtitle: 'Overview of repository health and vulnerability metrics' };
      case '/scanner':
        return { title: 'AI Code Scanner', subtitle: 'Deep neural AST & token vulnerability analysis' };
      case '/results':
        return { title: 'Vulnerability Analysis Results', subtitle: 'Explainable AI occlusion scores and remediation guides' };
      case '/pull-request':
        return { title: 'GitHub PR Analysis', subtitle: 'Review changed code and informational scan findings' };
      case '/history':
        return { title: 'Scan History', subtitle: 'Audit log of past scans backed by PostgreSQL' };
      case '/reports':
        return { title: 'Security Reports', subtitle: 'Compliance reporting, CWE breakdowns, and risk trends' };
      case '/settings':
        return { title: 'System Settings', subtitle: 'API configuration, tokens, and health checks' };
      default:
        return { title: 'CodeSentinel Platform', subtitle: 'Continuous AI Security Monitoring' };
    }
  };

  const { title, subtitle } = getPageInfo();
  const apiUrl = getApiBaseUrl();

  return (
    <header className="sticky top-0 z-30 flex h-18 w-full items-center justify-between border-b border-slate-800/80 bg-[#090d16]/80 px-4 sm:px-6 backdrop-blur-md">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="rounded-lg border border-slate-800 bg-slate-900/60 p-2 text-slate-400 hover:bg-slate-800 hover:text-white lg:hidden"
          aria-label="Toggle menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div>
          <h1 className="text-base font-semibold text-white sm:text-lg flex items-center gap-2">
            {title}
            <span className="hidden sm:inline-flex items-center gap-1 rounded-md bg-purple-500/10 px-2 py-0.5 text-[10px] font-mono text-purple-300 border border-purple-500/20">
              <Sparkles className="w-2.5 h-2.5 text-amber-300" /> DEMO MODEL
            </span>
          </h1>
          <p className="hidden text-xs text-slate-400 sm:block">{subtitle}</p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Backend health indicator badge */}
        <button
          onClick={() => refreshHealth()}
          title={`Click to re-ping backend at ${apiUrl}`}
          className="group flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-1.5 text-xs text-slate-300 hover:border-slate-700 transition-all"
        >
          {health.status === 'online' ? (
            <>
              <ShieldCheck className="h-4 w-4 text-emerald-400" />
              <span className="hidden sm:inline text-slate-400">API:</span>
              <span className="font-semibold text-emerald-400">Online</span>
              <span className="font-mono text-[11px] text-slate-400">({health.latencyMs ?? 10}ms)</span>
            </>
          ) : health.status === 'checking' ? (
            <>
              <RefreshCw className="h-4 w-4 text-yellow-400 animate-spin" />
              <span className="font-medium text-yellow-400">Connecting...</span>
            </>
          ) : (
            <>
              <ShieldAlert className="h-4 w-4 text-rose-400" />
              <span className="font-semibold text-rose-400">API Offline</span>
            </>
          )}
        </button>

        {/* Quick action button: New Scan */}
        <button
          onClick={() => navigate('/scanner')}
          className="hidden sm:flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-md shadow-purple-500/20 hover:from-purple-500 hover:to-indigo-500 transition-all cursor-pointer"
        >
          <Terminal className="h-3.5 w-3.5" />
          <span>Scan Code</span>
        </button>

        {/* Documentation / Swagger API link */}
        <a
          href={`${apiUrl}/docs`}
          target="_blank"
          rel="noopener noreferrer"
          title="Open FastAPI Swagger Documentation"
          className="flex items-center gap-1 rounded-lg border border-slate-800 bg-slate-900/70 px-2.5 py-1.5 text-xs text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-all"
        >
          <span className="hidden md:inline">API Docs</span>
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      </div>
    </header>
  );
};
