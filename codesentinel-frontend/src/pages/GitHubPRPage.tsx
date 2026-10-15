import React, { useState } from 'react';
import {
  GitPullRequest,
  Play,
  FileDiff,
  AlertTriangle,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  ShieldAlert,
  ShieldCheck,
  Code,
  Sparkles,
  Layers,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { SeverityBadge } from '../components/common/SeverityBadge';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useScan } from '../context/ScanContext';
import { AnalyzePRRequest, AnalyzePRResponse } from '../types';
import { formatPercent } from '../utils/formatters';

const SAMPLE_DIFFS = [
  {
    name: 'SQL Injection Vulnerability in app.py',
    repo: 'acme/webapp-api',
    prNumber: 42,
    commitSha: 'a1b2c3d4',
    diff: `diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -10,3 +10,4 @@
 def query_user(user_input):
+    cursor.execute(f"SELECT * FROM users WHERE username = '{user_input}'")
+    return cursor.fetchall()
`
  },
  {
    name: 'Buffer Overflow in auth.c',
    repo: 'security-corp/firmware',
    prNumber: 17,
    commitSha: 'f9e8d7c6',
    diff: `diff --git a/auth.c b/auth.c
--- a/auth.c
+++ b/auth.c
@@ -25,2 +25,4 @@
 int process_token() {
+    char buf[16];
+    gets(buf);
`
  },
  {
    name: 'Safe Code Refactoring in service.py',
    repo: 'acme/auth-service',
    prNumber: 88,
    commitSha: '55667788',
    diff: `diff --git a/service.py b/service.py
--- a/service.py
+++ b/service.py
@@ -15,2 +15,3 @@
 def get_user_secure(db, user_id: int):
+    return db.query(User).filter(User.id == user_id).first()
`
  }
];

export const GitHubPRPage: React.FC = () => {
  const { runPRScan, isPRScanning, prError } = useScan();

  const [prUrl, setPrUrl] = useState('');
  const [repo, setRepo] = useState('acme/demo-service');
  const [prNumber, setPrNumber] = useState<number>(7);
  const [commitSha, setCommitSha] = useState('');
  const [diff, setDiff] = useState(SAMPLE_DIFFS[0].diff);
  const [installationId, setInstallationId] = useState<string>('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [scanResult, setScanResult] = useState<AnalyzePRResponse | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  // Auto-parse URL when user inputs a GitHub PR link
  const handleUrlChange = (url: string) => {
    setPrUrl(url);
    setLocalError(null);

    // Matches https://github.com/owner/repo/pull/123 or owner/repo/pull/123
    const match = url.match(/(?:https?:\/\/github\.com\/)?([^/\s]+)\/([^/\s]+)\/pull\/(\d+)/i);
    if (match) {
      const owner = match[1];
      const repoName = match[2];
      const prNum = parseInt(match[3], 10);
      setRepo(`${owner}/${repoName}`);
      setPrNumber(prNum);
    }
  };

  const handleSelectSample = (sample: typeof SAMPLE_DIFFS[0]) => {
    setRepo(sample.repo);
    setPrNumber(sample.prNumber);
    setCommitSha(sample.commitSha);
    setDiff(sample.diff);
    setPrUrl(`https://github.com/${sample.repo}/pull/${sample.prNumber}`);
    setLocalError(null);
  };

  const handleAnalyze = async () => {
    const cleanRepo = repo.trim().replace(/^\/+|\/+$/g, '');
    if (!cleanRepo || !cleanRepo.includes('/') || cleanRepo.split('/').length !== 2) {
      setLocalError('Please provide a valid repository in "owner/repo" format (e.g. acme/webapp-api).');
      return;
    }
    if (!prNumber || prNumber <= 0) {
      setLocalError('Please provide a valid Pull Request number.');
      return;
    }
    if (!diff && !installationId) {
      setLocalError('Either provide the unified Git Diff or provide an Installation ID for GitHub App authentication.');
      return;
    }

    setLocalError(null);

    const payload: AnalyzePRRequest = {
      repo: cleanRepo,
      pr_number: Number(prNumber),
    };

    if (diff && diff.trim()) payload.diff = diff;
    if (commitSha && commitSha.trim()) payload.commit_sha = commitSha.trim();
    if (installationId && installationId.trim()) payload.installation_id = Number(installationId);

    try {
      const res = await runPRScan(payload);
      setScanResult(res);
    } catch (err: any) {
      setLocalError(err.message || 'PR analysis failed.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-slate-800/80 pb-5">
        <div className="flex items-center gap-2 text-purple-400 text-xs font-semibold uppercase tracking-wider mb-1">
          <GitPullRequest className="h-3.5 w-3.5" />
          <span>PR Diff Analysis</span>
        </div>
        <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
          GitHub Pull Request Security Inspector
        </h2>
        <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl">
          Intercept security regressions before merging. Connects with <code className="text-purple-300 font-mono">POST /analyze-pr</code> to parse changed diff units and record scan audits into PostgreSQL.
        </p>
      </div>

      {/* Preset test buttons */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-slate-400 font-medium">Quick Test Scenarios:</span>
        {SAMPLE_DIFFS.map((sample) => (
          <button
            key={sample.name}
            onClick={() => handleSelectSample(sample)}
            className="rounded-lg border border-slate-700 bg-slate-800/80 px-2.5 py-1 text-xs text-slate-300 hover:border-purple-500/50 hover:text-white transition-all cursor-pointer"
          >
            {sample.name}
          </button>
        ))}
      </div>

      {/* Main Form Card */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-md space-y-5">
        {/* Error notification */}
        {(localError || prError) && (
          <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-xs sm:text-sm text-rose-300 flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-rose-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-rose-200">Validation or API Error</p>
              <p>{localError || prError}</p>
            </div>
          </div>
        )}

        {/* PR URL input */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
            <span>GitHub Pull Request URL</span>
            <span className="text-slate-400 text-[11px] font-normal">Auto-extracts repo & PR number</span>
          </label>
          <div className="relative">
            <input
              type="text"
              value={prUrl}
              onChange={(e) => handleUrlChange(e.target.value)}
              placeholder="https://github.com/organization/repo-name/pull/42"
              className="w-full rounded-lg border border-slate-700 bg-slate-950/70 px-4 py-2.5 text-xs sm:text-sm text-white placeholder-slate-400 focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 font-mono"
            />
          </div>
        </div>

        {/* Two-column repo & PR number */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="sm:col-span-2 space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">
              Target Repository (owner/name) <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              placeholder="acme/webapp"
              className="w-full rounded-lg border border-slate-700 bg-slate-950/70 px-4 py-2 text-xs sm:text-sm text-white font-mono focus:border-purple-500 focus:outline-none"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">
              PR Number <span className="text-rose-400">*</span>
            </label>
            <input
              type="number"
              min={1}
              value={prNumber}
              onChange={(e) => setPrNumber(parseInt(e.target.value, 10) || 1)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950/70 px-4 py-2 text-xs sm:text-sm text-white font-mono focus:border-purple-500 focus:outline-none"
            />
          </div>
        </div>

        {/* Unified Git Diff Input */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <FileDiff className="h-4 w-4 text-purple-400" />
              <span>Unified Git Diff Content</span>
            </label>
            <span className="text-[11px] text-slate-400">
              Standard git diff format (parsed line-by-line by backend)
            </span>
          </div>
          <textarea
            rows={8}
            value={diff}
            onChange={(e) => setDiff(e.target.value)}
            placeholder="diff --git a/app.py b/app.py&#10;--- a/app.py&#10;+++ b/app.py&#10;@@ -1,2 +1,3 @@..."
            className="w-full rounded-lg border border-slate-700 bg-[#080c14] p-3 text-xs text-slate-200 font-mono placeholder-slate-400 focus:border-purple-500 focus:outline-none leading-5"
          />
        </div>

        {/* Advanced Options Toggle */}
        <div className="pt-2 border-t border-slate-800">
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-1 text-xs font-medium text-slate-400 hover:text-white transition-colors cursor-pointer"
          >
            {showAdvanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            <span>Advanced GitHub App Settings (Installation ID, Commit SHA)</span>
          </button>

          {showAdvanced && (
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-4 rounded-lg bg-slate-950/40 p-4 border border-slate-800">
              <div className="space-y-1">
                <label className="text-xs text-slate-300">Commit SHA (Optional)</label>
                <input
                  type="text"
                  value={commitSha}
                  onChange={(e) => setCommitSha(e.target.value)}
                  placeholder="e.g. 7b3dcb6..."
                  className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-white font-mono focus:border-purple-500 focus:outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs text-slate-300">GitHub App Installation ID (Optional)</label>
                <input
                  type="number"
                  value={installationId}
                  onChange={(e) => setInstallationId(e.target.value)}
                  placeholder="e.g. 123456"
                  className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-white font-mono focus:border-purple-500 focus:outline-none"
                />
                <p className="text-[10px] text-slate-400">
                  Required only if omitting the diff to let backend fetch directly via GitHub App API.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Submit Button */}
        <div className="flex items-center justify-end pt-2">
          <button
            type="button"
            onClick={handleAnalyze}
            disabled={isPRScanning}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-600 px-6 py-2.5 text-xs sm:text-sm font-semibold text-white shadow-lg shadow-purple-600/30 hover:from-purple-500 hover:to-cyan-500 transition-all disabled:opacity-50 cursor-pointer"
          >
            {isPRScanning ? (
              <>
                <LoadingSpinner size="sm" />
                <span>Running PR Security Audit...</span>
              </>
            ) : (
              <>
                <Play className="h-4 w-4 fill-current" />
                <span>Analyze Pull Request</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Analysis Results Display */}
      {scanResult && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-md space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800/80 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-purple-400">
                  Scan ID: {scanResult.scan_id}
                </span>
                <span className="text-slate-400 text-xs">•</span>
                <span className="font-mono text-xs text-slate-400">{repo} #{prNumber}</span>
              </div>
              <h3 className="text-lg font-bold text-white mt-1">
                PR Security Findings Summary
              </h3>
            </div>

            <div className="flex items-center gap-3">
              <StatusBadge status={scanResult.status} />
              {scanResult.severity ? (
                <SeverityBadge severity={scanResult.severity} size="md" />
              ) : (
                <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-400 border border-emerald-500/30">
                  PASS (No Flaws)
                </span>
              )}
            </div>
          </div>

          {/* Finding Cards */}
          {scanResult.findings.length === 0 ? (
            <div className="rounded-lg border border-emerald-500/20 bg-emerald-950/10 p-6 text-center space-y-2">
              <CheckCircle2 className="mx-auto h-8 w-8 text-emerald-400" />
              <p className="text-sm font-semibold text-emerald-300">Clean Diff – No Vulnerabilities Detected</p>
              <p className="text-xs text-slate-400">
                None of the modified code chunks in this pull request triggered neural vulnerability classifiers.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Flagged Security Issues ({scanResult.findings.length})
              </div>

              <div className="space-y-3">
                {scanResult.findings.map((finding, idx) => (
                  <div
                    key={idx}
                    className="rounded-xl border border-rose-500/20 bg-slate-950/70 p-4 space-y-3 hover:border-rose-500/40 transition-all"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-2.5">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-rose-300">
                          {finding.file_path}:{finding.line_number}
                        </span>
                        {finding.cwe_id && (
                          <span className="rounded bg-purple-500/20 px-2 py-0.5 font-mono text-[11px] font-semibold text-purple-300 border border-purple-500/30">
                            {finding.cwe_id}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-400 font-mono">
                          Confidence: {formatPercent(finding.confidence)}
                        </span>
                        <SeverityBadge severity={finding.severity} size="sm" />
                      </div>
                    </div>

                    {/* Snippet display */}
                    <div className="rounded-lg bg-[#080c14] p-3 font-mono text-xs text-rose-200 border border-slate-800/80 overflow-x-auto">
                      <code>{finding.snippet}</code>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span>Model Version: {finding.model_version}</span>
                      <span className="text-amber-300 font-medium">Informational only — merge blocking is disabled</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
