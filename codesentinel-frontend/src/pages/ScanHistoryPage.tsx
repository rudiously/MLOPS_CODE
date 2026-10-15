import React, { useEffect, useState } from 'react';
import {
  History,
  Search,
  Filter,
  RefreshCw,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  FileCode,
  X,
  Clock,
  Layers,
  ShieldCheck,
  ShieldAlert
} from 'lucide-react';
import { SeverityBadge } from '../components/common/SeverityBadge';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { CodeSentinelApi, formatApiError } from '../services/api';
import { AnalyzePRResponse, HistoryItem } from '../types';
import { formatDate, formatRelativeTime, formatPercent } from '../utils/formatters';

export const ScanHistoryPage: React.FC = () => {
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [repoFilter, setRepoFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string>('');

  // Selected scan modal state
  const [selectedScan, setSelectedScan] = useState<HistoryItem | null>(null);
  const [scanDetails, setScanDetails] = useState<AnalyzePRResponse | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [detailsError, setDetailsError] = useState<string | null>(null);

  const fetchHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const filters: Record<string, any> = {
        page,
        page_size: pageSize,
      };
      if (repoFilter && repoFilter.trim()) {
        filters.repo = repoFilter.trim();
      }
      if (severityFilter && severityFilter !== 'all') {
        filters.severity = severityFilter;
      }

      const res = await CodeSentinelApi.getHistory(filters);
      setHistoryItems(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [page, severityFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (repoFilter && repoFilter.trim() && !repoFilter.includes('/')) {
      setError('Repository filter must be formatted as "owner/name" (e.g. acme/demo-service)');
      return;
    }
    setPage(1);
    fetchHistory();
  };

  const handleOpenDetails = async (scan: HistoryItem) => {
    setSelectedScan(scan);
    setScanDetails(null);
    setDetailsError(null);
    setDetailsLoading(true);

    try {
      const details = await CodeSentinelApi.getScanDetails(scan.scan_id);
      setScanDetails(details);
    } catch (err) {
      setDetailsError(formatApiError(err));
    } finally {
      setDetailsLoading(false);
    }
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="border-b border-slate-800/80 pb-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-purple-400 text-xs font-semibold uppercase tracking-wider mb-1">
            <History className="h-3.5 w-3.5" />
            <span>Audit Trail</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
            Security Scan History
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl">
            Query real-time scan records backed by the CodeSentinel PostgreSQL database. Inspect finding counts, severities, and CI/CD gate conclusions.
          </p>
        </div>

        <button
          onClick={fetchHistory}
          className="flex items-center gap-2 self-start sm:self-auto rounded-xl border border-slate-700 bg-slate-800/80 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 hover:text-white transition-all cursor-pointer"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Records</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-md">
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-3 h-4 w-4 text-slate-400" />
            <input
              type="text"
              value={repoFilter}
              onChange={(e) => setRepoFilter(e.target.value)}
              placeholder="Search repository (e.g. acme/webapp)..."
              className="w-full rounded-lg border border-slate-700 bg-slate-950/70 pl-10 pr-4 py-2 text-xs sm:text-sm text-white placeholder-slate-400 focus:border-purple-500 focus:outline-none"
            />
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-950/70 px-3 py-1.5">
              <Filter className="h-3.5 w-3.5 text-slate-400" />
              <select
                value={severityFilter}
                onChange={(e) => {
                  setSeverityFilter(e.target.value);
                  setPage(1);
                }}
                className="bg-transparent text-xs text-slate-200 focus:outline-none cursor-pointer"
              >
                <option value="" className="bg-slate-900">All Severities</option>
                <option value="critical" className="bg-slate-900">Critical</option>
                <option value="high" className="bg-slate-900">High</option>
                <option value="medium" className="bg-slate-900">Medium</option>
                <option value="low" className="bg-slate-900">Low</option>
              </select>
            </div>

            <button
              type="submit"
              className="rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:from-purple-500 hover:to-indigo-500 transition-all cursor-pointer"
            >
              Filter
            </button>
          </div>
        </form>
      </div>

      {/* Error notification */}
      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs sm:text-sm text-rose-300 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-rose-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-rose-200">Unable to load scan history</p>
            <p className="text-rose-300/90">{error}</p>
          </div>
        </div>
      )}

      {/* Table Card */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-md overflow-hidden">
        {loading ? (
          <div className="py-16">
            <LoadingSpinner text="Fetching audit trail from PostgreSQL..." />
          </div>
        ) : historyItems.length === 0 ? (
          <div className="py-16 px-6 text-center space-y-3">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <History className="h-6 w-6" />
            </div>
            <p className="text-base font-semibold text-white">No Scan Records Match Filters</p>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Scan records appear here after running Pull Request scans via POST /analyze-pr or GitHub webhooks.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800/80 bg-slate-950/60 font-semibold uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="py-3 px-6">Repository</th>
                  <th className="py-3 px-4">PR #</th>
                  <th className="py-3 px-4">Scan Date & Time</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Risk Level</th>
                  <th className="py-3 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {historyItems.map((item) => (
                  <tr
                    key={item.scan_id}
                    className="hover:bg-slate-850/50 transition-colors"
                  >
                    <td className="py-3.5 px-6 font-mono font-medium text-slate-200">
                      {item.repo}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-purple-300">
                      #{item.pr_number}
                    </td>
                    <td className="py-3.5 px-4 text-slate-400">
                      <div>{formatDate(item.started_at)}</div>
                      <div className="text-[10px] text-slate-400">
                        {formatRelativeTime(item.started_at)}
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={item.status} />
                    </td>
                    <td className="py-3.5 px-4">
                      {item.severity ? (
                        <SeverityBadge severity={item.severity} size="sm" />
                      ) : (
                        <span className="text-slate-400 text-xs">None</span>
                      )}
                    </td>
                    <td className="py-3.5 px-6 text-right">
                      <button
                        onClick={() => handleOpenDetails(item)}
                        className="rounded-lg border border-purple-500/30 bg-purple-500/10 px-3 py-1.5 text-xs font-semibold text-purple-300 hover:bg-purple-500/20 transition-all cursor-pointer"
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination controls */}
        {total > 0 && (
          <div className="flex items-center justify-between border-t border-slate-800/80 bg-slate-950/40 px-6 py-3 text-xs text-slate-400">
            <div>
              Showing <span className="font-semibold text-slate-200">{(page - 1) * pageSize + 1}</span> to{' '}
              <span className="font-semibold text-slate-200">
                {Math.min(page * pageSize, total)}
              </span>{' '}
              of <span className="font-semibold text-slate-200">{total}</span> scans
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="flex items-center gap-1 rounded border border-slate-700 bg-slate-800 px-2.5 py-1 text-slate-300 hover:bg-slate-700 disabled:opacity-40 cursor-pointer"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
                <span>Prev</span>
              </button>
              <span className="font-mono px-2 text-slate-300">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="flex items-center gap-1 rounded border border-slate-700 bg-slate-800 px-2.5 py-1 text-slate-300 hover:bg-slate-700 disabled:opacity-40 cursor-pointer"
              >
                <span>Next</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* View Details Action Modal */}
      {selectedScan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="relative w-full max-w-3xl max-h-[85vh] overflow-y-auto rounded-2xl border border-slate-800 bg-[#0d121f] p-6 shadow-2xl space-y-5">
            {/* Modal header */}
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
              <div className="flex items-center gap-3">
                <div className="rounded-xl bg-purple-500/10 p-2.5 text-purple-400 border border-purple-500/20">
                  <FileCode className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">
                    Scan Audit Detail
                  </h3>
                  <p className="text-xs text-slate-400 font-mono">
                    ID: {selectedScan.scan_id}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedScan(null)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors cursor-pointer"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Scan Metadata strip */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="rounded-lg bg-slate-900/80 p-3 border border-slate-800">
                <span className="text-slate-400 text-[11px]">Repository</span>
                <p className="font-mono font-bold text-slate-200 truncate">{selectedScan.repo}</p>
              </div>
              <div className="rounded-lg bg-slate-900/80 p-3 border border-slate-800">
                <span className="text-slate-400 text-[11px]">PR Number</span>
                <p className="font-mono font-bold text-purple-300">#{selectedScan.pr_number}</p>
              </div>
              <div className="rounded-lg bg-slate-900/80 p-3 border border-slate-800">
                <span className="text-slate-400 text-[11px]">Status</span>
                <div className="mt-0.5"><StatusBadge status={selectedScan.status} /></div>
              </div>
              <div className="rounded-lg bg-slate-900/80 p-3 border border-slate-800">
                <span className="text-slate-400 text-[11px]">Worst Severity</span>
                <div className="mt-0.5">
                  {selectedScan.severity ? (
                    <SeverityBadge severity={selectedScan.severity} size="sm" />
                  ) : (
                    <span className="text-slate-400">None</span>
                  )}
                </div>
              </div>
            </div>

            {/* Findings details section */}
            <div className="space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Vulnerability Findings
              </h4>

              {detailsLoading ? (
                <div className="py-8">
                  <LoadingSpinner text="Retrieving finding details from PostgreSQL..." />
                </div>
              ) : detailsError ? (
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-xs text-amber-300">
                  {detailsError}
                </div>
              ) : scanDetails && scanDetails.findings.length > 0 ? (
                <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
                  {scanDetails.findings.map((f, i) => (
                    <div
                      key={i}
                      className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 space-y-2 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-rose-300 font-semibold">
                          {f.file_path}:{f.line_number}
                        </span>
                        <div className="flex items-center gap-2">
                          {f.cwe_id && (
                            <span className="rounded bg-purple-500/20 px-2 py-0.5 font-mono text-[10px] text-purple-300">
                              {f.cwe_id}
                            </span>
                          )}
                          <SeverityBadge severity={f.severity} size="sm" />
                        </div>
                      </div>
                      <div className="rounded bg-[#080c14] p-2 font-mono text-slate-300 overflow-x-auto text-[11px]">
                        <code>{f.snippet}</code>
                      </div>
                      <div className="flex items-center justify-between text-[10px] text-slate-400">
                        <span>Confidence: {formatPercent(f.confidence)}</span>
                        <span>Model: {f.model_version}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-6 text-center text-xs text-slate-400">
                  No individual findings recorded for this scan.
                </div>
              )}
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-800">
              <button
                onClick={() => setSelectedScan(null)}
                className="rounded-lg bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
