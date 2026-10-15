import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Code2,
  GitPullRequest,
  History,
  ShieldAlert,
  FileCheck,
  Settings,
  Shield,
  Activity,
  X
} from 'lucide-react';
import { useScan } from '../../context/ScanContext';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const { health } = useScan();

  const navItems = [
    {
      to: '/dashboard',
      label: 'Dashboard',
      icon: LayoutDashboard,
      badge: null,
    },
    {
      to: '/scanner',
      label: 'Code Scanner',
      icon: Code2,
      badge: 'AI Scan',
    },
    {
      to: '/results',
      label: 'Scan Results',
      icon: FileCheck,
      badge: null,
    },
    {
      to: '/pull-request',
      label: 'GitHub PR Analysis',
      icon: GitPullRequest,
      badge: null,
    },
    {
      to: '/history',
      label: 'Scan History',
      icon: History,
      badge: null,
    },
    {
      to: '/reports',
      label: 'Security Reports',
      icon: ShieldAlert,
      badge: null,
    },
    {
      to: '/settings',
      label: 'Settings',
      icon: Settings,
      badge: null,
    },
  ];

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm lg:hidden transition-opacity"
        />
      )}

      {/* Sidebar container */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-slate-800/80 bg-[#090d16]/95 backdrop-blur-xl transition-transform duration-300 ease-in-out lg:static lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand header */}
        <div className="flex h-18 items-center justify-between border-b border-slate-800/70 px-6">
          <NavLink to="/dashboard" className="flex items-center gap-3 group">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-cyan-500 shadow-[0_0_16px_rgba(139,92,246,0.4)] transition-transform group-hover:scale-105">
              <Shield className="h-5 w-5 text-white" />
              <span className="absolute -top-1 -right-1 flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-3 w-3 bg-cyan-500" />
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-lg font-bold tracking-tight text-white flex items-center gap-1.5">
                Code<span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-cyan-400">Sentinel</span>
              </span>
              <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400">
                AI Security Guard
              </span>
            </div>
          </NavLink>

          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800/70 hover:text-white lg:hidden"
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation items */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-1.5">
          <div className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Platform Navigation
          </div>

          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={onClose}
                className={({ isActive }) =>
                  `group relative flex items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? 'bg-gradient-to-r from-purple-600/20 via-indigo-600/15 to-transparent text-white border-l-3 border-purple-500 shadow-sm'
                      : 'text-slate-400 hover:bg-slate-850/60 hover:text-slate-200'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon
                      className={`h-4.5 w-4.5 transition-colors ${
                        isActive
                          ? 'text-purple-400'
                          : 'text-slate-400 group-hover:text-slate-300'
                      }`}
                    />
                    <span className="flex-1">{item.label}</span>
                    {item.badge && (
                      <span className="rounded-md bg-purple-500/10 px-2 py-0.5 text-[10px] font-semibold text-purple-300 border border-purple-500/20">
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            );
          })}
        </div>

        {/* Backend live status footer */}
        <div className="border-t border-slate-800/80 p-4 bg-slate-900/40">
          <div className="rounded-xl border border-slate-800/90 bg-slate-900/80 p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div
                  className={`h-2.5 w-2.5 rounded-full ${
                    health.status === 'online'
                      ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.7)] animate-pulse'
                      : health.status === 'checking'
                      ? 'bg-yellow-500 animate-spin'
                      : 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.7)]'
                  }`}
                />
                <span className="text-xs font-semibold text-slate-200">
                  FastAPI Engine
                </span>
              </div>
              <span
                className={`text-[11px] font-mono font-medium ${
                  health.status === 'online'
                    ? 'text-emerald-400'
                    : health.status === 'checking'
                    ? 'text-yellow-400'
                    : 'text-rose-400'
                }`}
              >
                {health.status === 'online'
                  ? `${health.latencyMs ?? 12}ms`
                  : health.status === 'checking'
                  ? 'Checking'
                  : 'Offline'}
              </span>
            </div>
            <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
              <span className="flex items-center gap-1">
                <Activity className="h-3 w-3" /> ONNX Neural Net
              </span>
              <span className="font-mono text-slate-400 text-[10px]">v0.1.0</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
