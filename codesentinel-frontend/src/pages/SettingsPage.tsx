import React, { useState } from 'react';
import {
  Settings,
  Server,
  Key,
  ShieldCheck,
  ShieldAlert,
  RefreshCw,
  Save,
  RotateCcw,
  Check,
  Globe,
  Sliders,
  ExternalLink,
  Info
} from 'lucide-react';
import { useScan } from '../context/ScanContext';
import {
  getApiBaseUrl,
  setCustomApiBaseUrl,
  getAuthToken,
  setAuthToken,
  CodeSentinelApi
} from '../services/api';

export const SettingsPage: React.FC = () => {
  const { health, refreshHealth } = useScan();

  const [apiUrl, setApiUrl] = useState<string>(() => getApiBaseUrl());
  const [jwtToken, setJwtToken] = useState<string>(() => getAuthToken() || '');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
    latencyMs?: number;
  } | null>(null);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleSave = () => {
    setCustomApiBaseUrl(apiUrl);
    setAuthToken(jwtToken);
    setSavedSuccess(true);
    refreshHealth();
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  const handleResetDefaults = () => {
    const defaultUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    setApiUrl(defaultUrl);
    setJwtToken('');
    setCustomApiBaseUrl(null);
    setAuthToken(null);
    setSavedSuccess(true);
    refreshHealth();
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);

    // Save temporary URL to test
    setCustomApiBaseUrl(apiUrl);
    try {
      const res = await CodeSentinelApi.checkHealth();
      if (res.status === 'online') {
        setTestResult({
          success: true,
          message: `Successfully connected to FastAPI backend at ${apiUrl}`,
          latencyMs: res.latencyMs,
        });
      } else {
        setTestResult({
          success: false,
          message: `Backend responded with non-healthy status. Error: ${res.error || 'Unknown error'}`,
        });
      }
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err.message || `Unable to reach ${apiUrl}. Verify the FastAPI container or uvicorn process is active.`,
      });
    } finally {
      setTesting(false);
      refreshHealth();
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-slate-800/80 pb-5">
        <div className="flex items-center gap-2 text-purple-400 text-xs font-semibold uppercase tracking-wider mb-1">
          <Sliders className="h-3.5 w-3.5" />
          <span>System Configuration</span>
        </div>
        <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
          CodeSentinel Platform Settings
        </h2>
        <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl">
          Configure API endpoints, Bearer authentication tokens, and inspect real-time connection diagnostics with the FastAPI backend.
        </p>
      </div>

      {/* Save Success Banner */}
      {savedSuccess && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-xs sm:text-sm text-emerald-300 flex items-center gap-3">
          <Check className="h-5 w-5 text-emerald-400" />
          <span>Settings saved successfully! Updated API configuration is now active.</span>
        </div>
      )}

      {/* Backend API Configuration */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-md space-y-5">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-purple-500/10 p-2.5 text-purple-400 border border-purple-500/20">
              <Server className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">FastAPI Backend Connection</h3>
              <p className="text-xs text-slate-400">Target host for API requests and ML model inference</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold border ${
                health.status === 'online'
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                  : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  health.status === 'online' ? 'bg-emerald-400' : 'bg-rose-400'
                }`}
              />
              {health.status === 'online' ? `Online (${health.latencyMs ?? 10}ms)` : 'Offline'}
            </span>
          </div>
        </div>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
              <span>Backend API Base URL</span>
              <span className="text-[11px] font-mono text-slate-400">
                Default: {import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}
              </span>
            </label>
            <div className="relative">
              <Globe className="absolute left-3.5 top-3 h-4 w-4 text-slate-400" />
              <input
                type="text"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                placeholder="http://localhost:8000"
                className="w-full rounded-lg border border-slate-700 bg-slate-950/70 pl-10 pr-4 py-2.5 text-xs sm:text-sm text-white font-mono focus:border-purple-500 focus:outline-none"
              />
            </div>
            <p className="text-[11px] text-slate-400">
              For local dev, use <code className="text-purple-300 font-mono">http://localhost:8000</code>. In Docker, configure through <code className="text-purple-300 font-mono">VITE_API_BASE_URL</code> or Nginx reverse proxy.
            </p>
          </div>

          {/* Test Connection Button & Result */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={testing}
              className="flex items-center gap-2 rounded-lg border border-purple-500/40 bg-purple-950/30 px-4 py-2 text-xs font-semibold text-purple-300 hover:bg-purple-900/40 transition-all cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${testing ? 'animate-spin' : ''}`} />
              <span>{testing ? 'Testing Health...' : 'Test Backend Connection'}</span>
            </button>

            {testResult && (
              <span
                className={`text-xs font-medium flex items-center gap-1.5 ${
                  testResult.success ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {testResult.success ? (
                  <ShieldCheck className="h-4 w-4 text-emerald-400" />
                ) : (
                  <ShieldAlert className="h-4 w-4 text-rose-400" />
                )}
                <span>
                  {testResult.message}{' '}
                  {testResult.latencyMs != null && `(${testResult.latencyMs}ms)`}
                </span>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Dashboard Authentication (JWT) */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-md space-y-5">
        <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
          <div className="rounded-xl bg-purple-500/10 p-2.5 text-purple-400 border border-purple-500/20">
            <Key className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">Dashboard Authentication (JWT)</h3>
            <p className="text-xs text-slate-400">Bearer token passed in HTTP Authorization header</p>
          </div>
        </div>

        <div className="space-y-3">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">
              JWT Bearer Token (Optional)
            </label>
            <input
              type="password"
              value={jwtToken}
              onChange={(e) => setJwtToken(e.target.value)}
              placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
              className="w-full rounded-lg border border-slate-700 bg-slate-950/70 px-4 py-2.5 text-xs sm:text-sm text-white font-mono focus:border-purple-500 focus:outline-none"
            />
          </div>

          <div className="rounded-lg bg-slate-950/40 p-3.5 border border-slate-800 text-xs text-slate-400 space-y-1">
            <p className="font-semibold text-slate-300 flex items-center gap-1.5">
              <Info className="h-3.5 w-3.5 text-purple-400" />
              Auth Mode in Backend:
            </p>
            <p>
              By default, <code className="text-purple-300 font-mono">REQUIRE_DASHBOARD_AUTH=false</code> in the backend .env, so no token is required during local development. If set to true, requests to <code className="text-purple-300 font-mono">GET /history</code> require an HS256 signed JWT with a numeric GitHub user ID.
            </p>
          </div>
        </div>
      </div>

      {/* Save & Reset Actions */}
      <div className="flex items-center justify-between border-t border-slate-800/80 pt-5">
        <button
          type="button"
          onClick={handleResetDefaults}
          className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/80 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-700 hover:text-white transition-all cursor-pointer"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          <span>Reset to Defaults</span>
        </button>

        <button
          type="button"
          onClick={handleSave}
          className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 px-6 py-2.5 text-xs sm:text-sm font-semibold text-white shadow-lg shadow-purple-600/30 hover:from-purple-500 hover:to-indigo-500 transition-all cursor-pointer"
        >
          <Save className="h-4 w-4" />
          <span>Save Changes</span>
        </button>
      </div>
    </div>
  );
};
