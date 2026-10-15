import React from 'react';
import { ShieldAlert, BookOpen, ExternalLink } from 'lucide-react';
import { CWEEstimate } from '../../types';
import { getCWEInfo } from '../../utils/cweDatabase';
import { formatPercent } from '../../utils/formatters';

interface CWEDetailsCardProps {
  predictedCwes: CWEEstimate[];
}

export const CWEDetailsCard: React.FC<CWEDetailsCardProps> = ({ predictedCwes = [] }) => {
  if (predictedCwes.length === 0) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-md">
        <h3 className="text-sm font-semibold text-slate-300">CWE Classification</h3>
        <p className="mt-2 text-xs text-slate-400">No specific CWE classification detected.</p>
      </div>
    );
  }

  // Top predicted CWE
  const topCwe = predictedCwes[0];
  const topInfo = getCWEInfo(topCwe?.cwe_id);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-md space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
        <div className="flex items-center gap-2">
          <ShieldAlert className="h-5 w-5 text-purple-400" />
          <h3 className="text-base font-semibold text-white">
            CWE Vulnerability Classification
          </h3>
        </div>
        <span className="text-xs font-mono text-slate-400">
          Neural Softmax Distribution
        </span>
      </div>

      {/* Primary Flagged CWE */}
      <div className="rounded-lg border border-purple-500/30 bg-purple-950/20 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="rounded bg-purple-500/20 px-2 py-0.5 font-mono text-xs font-bold text-purple-300 border border-purple-500/30">
              {topInfo.id}
            </span>
            <span className="text-sm font-bold text-white">
              {topInfo.name}
            </span>
          </div>
          <span className="rounded-full bg-purple-500/10 px-2.5 py-0.5 text-xs font-semibold text-purple-300">
            {topInfo.owaspTop10}
          </span>
        </div>
        <p className="mt-2 text-xs text-slate-300 leading-relaxed">
          {topInfo.description}
        </p>
      </div>

      {/* Probability bars for top candidates */}
      <div className="space-y-2.5 pt-1">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Model Prediction Probabilities
        </div>
        {predictedCwes.map((item, idx) => {
          const info = getCWEInfo(item.cwe_id);
          const percent = Math.min(100, Math.max(0, item.score * 100));

          return (
            <div key={idx} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="font-mono text-slate-300 font-medium flex items-center gap-1.5">
                  <span className="text-slate-400">#{idx + 1}</span> {item.cwe_id}: {info.name}
                </span>
                <span className="font-mono font-bold text-slate-200">
                  {formatPercent(item.score)}
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    idx === 0
                      ? 'bg-gradient-to-r from-purple-500 to-indigo-500'
                      : 'bg-slate-600'
                  }`}
                  style={{ width: `${percent}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* External reference link */}
      <div className="pt-2 flex items-center justify-between text-xs border-t border-slate-800/80">
        <span className="text-slate-400 flex items-center gap-1">
          <BookOpen className="h-3.5 w-3.5" /> MITRE CWE Database
        </span>
        <a
          href={
            topInfo.id.startsWith('CWE-')
              ? `https://cwe.mitre.org/data/definitions/${topInfo.id.replace('CWE-', '')}.html`
              : 'https://cwe.mitre.org'
          }
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-purple-400 hover:text-purple-300 hover:underline"
        >
          <span>View MITRE Documentation</span>
          <ExternalLink className="h-3 w-3" />
        </a>
      </div>
    </div>
  );
};
