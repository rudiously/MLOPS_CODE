import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Code2,
  GitPullRequest,
  Activity,
  ArrowRight,
  TrendingUp,
  RefreshCw,
  ExternalLink,
  CheckCircle2,
  Clock
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend
} from 'recharts';
import { StatCard } from '../components/common/StatCard';
import { SeverityBadge } from '../components/common/SeverityBadge';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useScan } from '../context/ScanContext';
import { CodeSentinelApi, formatApiError } from '../services/api';
import { HistoryItem } from '../types';
import { formatDate, formatRelativeTime } from '../utils/formatters';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { health, refreshHealth } = useScan();

  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [totalScans, setTotalScans] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const historyRes = await CodeSentinelApi.getHistory({ page: 1, page_size: 50 });
      setHistoryItems(historyRes.items || []);
      setTotalScans(historyRes.total || 0);
    } catch (err) {
      console.warn('Dashboard fetch warning:', err);
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  // Compute metrics from real history data
  const metrics = useMemo(() => {
    let critical = 0;
    let high = 0;
    let medium = 0;
    let low = 0;

    historyItems.forEach((item) => {
      const sev = item.severity?.toLowerCase();
      if (sev === 'critical') critical++;
      else if (sev === 'high') high++;
      else if (sev === 'medium') medium++;
      else if (sev === 'low') low++;
    });

    const totalVulnerabilities = critical + high + medium + low;

    return {
      totalScans,
      totalVulnerabilities,
      critical,
      high,
      medium,
      low,
    };
  }, [historyItems, totalScans]);

  // Chart data for Severity distribution
  const severityChartData = useMemo(() => {
    const data = [
      { name: 'Critical', value: metrics.critical, color: '#f43f5e' },
      { name: 'High', value: metrics.high, color: '#f59e0b' },
      { name: 'Medium', value: metrics.medium, color: '#eab308' },
      { name: 'Low', value: metrics.low, color: '#10b981' },
    ];
    // If all are 0, show a neutral baseline
    if (data.every((d) => d.value === 0)) {
      return [
        { name: 'No Vulnerabilities', value: 1, color: '#334155' }
      ];
    }
    return data.filter((d) => d.value > 0);
  }, [metrics]);

  // Aggregate recent scans by status
  const scansByStatus = useMemo(() => {
    const completed = historyItems.filter((i) => i.status === 'completed').length;
    const running = historyItems.filter((i) => i.status === 'running').length;
    const failed = historyItems.filter((i) => i.status === 'failed').length;
    return [
      { name: 'Completed', count: completed, fill: '#10b981' },
      { name: 'Running', count: running, fill: '#6366f1' },
      { name: 'Failed', count: failed, fill: '#f43f5e' },
    ];
  }, [historyItems]);

  return (
    <div className="space-y-6">
      {/* Top Banner / Hero */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 via-purple-950/20 to-slate-900 p-6 backdrop-blur-xl">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="flex h-2 w-2 rounded-full bg-cyan-400 animate-ping" />
              <span className="text-xs font-semibold uppercase tracking-wider text-cyan-400">
                Enterprise AI Security Platform
              </span>
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
              CodeSentinel Defense Command
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 max-w-2xl">
              Real-time deep learning vulnerability analysis, automated PR gatekeeper, and continuous CI/CD risk assessment powered by ONNX neural transformers.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={() => navigate('/scanner')}
              className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 px-4 py-2.5 text-xs sm:text-sm font-semibold text-white shadow-lg shadow-purple-600/25 hover:from-purple-500 hover:to-indigo-500 transition-all cursor-pointer"
            >
              <Code2 className="h-4 w-4" />
              <span>Analyze Code</span>
            </button>
            <button
              onClick={() => navigate('/pull-request')}
              className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800/80 px-4 py-2.5 text-xs sm:text-sm font-semibold text-slate-200 hover:bg-slate-700 hover:text-white transition-all cursor-pointer"
            >
              <GitPullRequest className="h-4 w-4 text-purple-400" />
              <span>Inspect PR</span>
            </button>
            <button
              onClick={fetchDashboardData}
              title="Refresh real metrics"
              className="rounded-xl border border-slate-800 bg-slate-900/80 p-2.5 text-slate-400 hover:text-white transition-all cursor-pointer"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Real-time Backend Engine Health Status strip */}
        <div className="mt-5 pt-4 border-t border-slate-800/80 flex flex-wrap items-center justify-between text-xs text-slate-400 gap-2">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span
                className={`h-2 w-2 rounded-full ${
                  health.status === 'online' ? 'bg-emerald-400' : 'bg-rose-400'
                }`}
              />
              Backend:{' '}
              <strong className={health.status === 'online' ? 'text-emerald-400' : 'text-rose-400'}>
                {health.status === 'online' ? 'Connected' : 'Offline'}
              </strong>
            </span>
            <span className="text-slate-400">|</span>
            <span>Latency: <strong className="text-slate-200 font-mono">{health.status === 'online' ? `${health.latencyMs ?? 0} ms` : 'Offline'}</strong></span>
            <span className="text-slate-400">|</span>
            <span>Database: <strong className="text-slate-200">PostgreSQL (psycopg3)</strong></span>
          </div>

          <span className="font-mono text-[11px] text-slate-400">
            Model: codesentinel-onnx (AST + Occlusion XAI)
          </span>
        </div>
      </div>

      {/* Offline Guidance Banner */}
      {health.status === 'offline' && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-xs text-amber-300 flex items-start justify-between gap-3 backdrop-blur-md">
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-amber-200">FastAPI Backend is Offline or Unreachable</p>
              <p className="text-amber-300/80 mt-0.5">
                The frontend is running at <code className="font-mono text-amber-200">http://localhost:5173</code>. To enable live inference and database history, start the backend with <code className="font-mono text-amber-200">uvicorn app.main:app --port 8000 --reload</code>, or configure your endpoint in <button onClick={() => navigate('/settings')} className="underline font-semibold hover:text-white cursor-pointer">Settings</button>.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Primary Metrics Grid (6 Key Metrics Required) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5 sm:gap-4">
        <StatCard
          title="Total Scans"
          value={metrics.totalScans}
          subtitle="All repository audits"
          icon={<Activity className="h-5 w-5" />}
          color="blue"
        />
        <StatCard
          title="Detected Issues"
          value={metrics.totalVulnerabilities}
          subtitle="Flagged code units"
          icon={<ShieldAlert className="h-5 w-5" />}
          color="purple"
        />
        <StatCard
          title="Critical"
          value={metrics.critical}
          subtitle="Immediate action req."
          icon={<AlertTriangle className="h-5 w-5" />}
          color="red"
          badge={metrics.critical > 0 ? 'Urgent' : undefined}
        />
        <StatCard
          title="High-Risk"
          value={metrics.high}
          subtitle="Severely exposed"
          icon={<AlertTriangle className="h-5 w-5" />}
          color="amber"
        />
        <StatCard
          title="Medium-Risk"
          value={metrics.medium}
          subtitle="Conditional threats"
          icon={<ShieldAlert className="h-5 w-5" />}
          color="amber"
        />
        <StatCard
          title="Low-Risk"
          value={metrics.low}
          subtitle="Minor security smells"
          icon={<ShieldCheck className="h-5 w-5" />}
          color="emerald"
        />
      </div>

      {/* Charts and Security Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Vulnerability Distribution Chart */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-md flex flex-col justify-between">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div>
              <h3 className="text-sm font-semibold text-white">Vulnerability Distribution</h3>
              <p className="text-xs text-slate-400">Severity tier composition</p>
            </div>
            <TrendingUp className="h-4 w-4 text-purple-400" />
          </div>

          <div className="h-56 w-full flex items-center justify-center my-2">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={severityChartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={75}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {severityChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderColor: '#334155',
                    borderRadius: '8px',
                    fontSize: '12px',
                    color: '#f8fafc',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Legend */}
          <div className="grid grid-cols-2 gap-2 text-xs border-t border-slate-800/80 pt-3">
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-rose-500" />
              <span className="text-slate-400">Critical ({metrics.critical})</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
              <span className="text-slate-400">High ({metrics.high})</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-yellow-500" />
              <span className="text-slate-400">Medium ({metrics.medium})</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
              <span className="text-slate-400">Low ({metrics.low})</span>
            </div>
          </div>
        </div>

        {/* Scan Status Breakdown Chart */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-md flex flex-col justify-between">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div>
              <h3 className="text-sm font-semibold text-white">Execution Outcomes</h3>
              <p className="text-xs text-slate-400">Pipeline scan statuses</p>
            </div>
            <Activity className="h-4 w-4 text-cyan-400" />
          </div>

          <div className="h-56 w-full flex items-center justify-center my-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={scansByStatus}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderColor: '#334155',
                    borderRadius: '8px',
                    fontSize: '12px',
                    color: '#f8fafc',
                  }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="border-t border-slate-800/80 pt-3 text-xs text-slate-400 flex items-center justify-between">
            <span>Historical Success Ratio</span>
            <span className="font-mono text-emerald-400 font-semibold">
              {historyItems.length > 0
                ? `${Math.round(
                    (historyItems.filter((i) => i.status === 'completed').length /
                      historyItems.length) *
                      100
                  )}%`
                : '100%'}
            </span>
          </div>
        </div>

        {/* Security Overview & Posture */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-md flex flex-col justify-between space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div>
              <h3 className="text-sm font-semibold text-white">Security Posture</h3>
              <p className="text-xs text-slate-400">Real-time health assessment</p>
            </div>
            <ShieldCheck className="h-5 w-5 text-emerald-400" />
          </div>

          <div className="space-y-3">
            <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Overall Threat Index</span>
                <span className="font-mono font-bold text-slate-200">
                  {metrics.critical > 0 ? 'CRITICAL RISK' : metrics.high > 0 ? 'ELEVATED' : 'SECURE'}
                </span>
              </div>
              <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-800">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    metrics.critical > 0
                      ? 'bg-rose-500 w-[90%]'
                      : metrics.high > 0
                      ? 'bg-amber-500 w-[60%]'
                      : 'bg-emerald-500 w-[15%]'
                  }`}
                />
              </div>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">AI Model Version:</span>
                <span className="font-mono text-purple-300">demo-synthetic-0.1</span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Explainability Engine:</span>
                <span className="font-mono text-cyan-300">Occlusion-Rollout</span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">CI/CD Gatekeeper:</span>
                <span className="text-amber-300 font-semibold">Disabled until model validation</span>
              </div>
            </div>
          </div>

          <button
            onClick={() => navigate('/scanner')}
            className="w-full flex items-center justify-center gap-2 rounded-lg border border-purple-500/30 bg-purple-950/30 py-2.5 text-xs font-semibold text-purple-300 hover:bg-purple-900/40 transition-all cursor-pointer"
          >
            <span>Launch Code Analysis</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Recent Analysis History Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-md overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-800/80 px-6 py-4">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-purple-400" />
            <h3 className="text-sm font-semibold text-white">Recent Security Scans</h3>
          </div>
          <button
            onClick={() => navigate('/history')}
            className="flex items-center gap-1 text-xs font-medium text-purple-400 hover:text-purple-300 transition-colors cursor-pointer"
          >
            <span>View Full History ({totalScans})</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>

        {loading ? (
          <div className="py-12">
            <LoadingSpinner text="Loading recent scan history..." />
          </div>
        ) : historyItems.length === 0 ? (
          <div className="py-12 px-6 text-center space-y-3">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <Code2 className="h-6 w-6" />
            </div>
            <p className="text-sm font-semibold text-white">No Pull Request Scans Found</p>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Scan history is stored in your PostgreSQL database whenever a PR is analyzed via the API or GitHub Action. Test the system now using the Code Scanner or PR Inspector.
            </p>
            <div className="pt-2">
              <button
                onClick={() => navigate('/scanner')}
                className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-md hover:from-purple-500 hover:to-indigo-500 transition-all cursor-pointer"
              >
                <Code2 className="h-4 w-4" />
                <span>Run First Scan</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800/80 bg-slate-950/60 font-semibold uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="py-3 px-6">Repository</th>
                  <th className="py-3 px-4">PR #</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Worst Severity</th>
                  <th className="py-3 px-4">Scanned At</th>
                  <th className="py-3 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {historyItems.slice(0, 5).map((scan) => (
                  <tr
                    key={scan.scan_id}
                    className="hover:bg-slate-850/50 transition-colors"
                  >
                    <td className="py-3 px-6 font-mono font-medium text-slate-200">
                      {scan.repo}
                    </td>
                    <td className="py-3 px-4 font-mono text-purple-300">
                      #{scan.pr_number}
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={scan.status} />
                    </td>
                    <td className="py-3 px-4">
                      {scan.severity ? (
                        <SeverityBadge severity={scan.severity} size="sm" />
                      ) : (
                        <span className="text-slate-400">None</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      {formatRelativeTime(scan.started_at)}
                    </td>
                    <td className="py-3 px-6 text-right">
                      <button
                        onClick={() => navigate('/history')}
                        className="rounded px-2.5 py-1 text-[11px] font-medium text-purple-400 hover:bg-purple-500/10 transition-colors cursor-pointer"
                      >
                        Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
