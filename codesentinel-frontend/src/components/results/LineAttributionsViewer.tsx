import React from 'react';
import { AlertTriangle, Crosshair, HelpCircle } from 'lucide-react';
import { LineAttribution } from '../../types';

interface LineAttributionsViewerProps {
  codeSnippet: string;
  attributions: LineAttribution[];
}

export const LineAttributionsViewer: React.FC<LineAttributionsViewerProps> = ({
  codeSnippet,
  attributions = [],
}) => {
  const lines = codeSnippet ? codeSnippet.split('\n') : [];

  // Map line number to attribution info
  const attrMap = new Map<number, LineAttribution>();
  attributions.forEach((attr) => {
    attrMap.set(attr.line, attr);
  });

  return (
    <div className="rounded-xl border border-slate-800 bg-[#0d121f] overflow-hidden shadow-lg">
      <div className="flex items-center justify-between border-b border-slate-800/80 bg-slate-900/80 px-4 py-3">
        <div className="flex items-center gap-2">
          <Crosshair className="h-4 w-4 text-rose-400" />
          <h3 className="text-sm font-semibold text-white">
            Model Explainability: Culprit Line Attributions (Occlusion Impact)
          </h3>
        </div>
        <div className="flex items-center gap-1 text-[11px] text-slate-400">
          <HelpCircle className="h-3.5 w-3.5 text-slate-400" />
          <span>Higher score = greater contribution to vulnerability</span>
        </div>
      </div>

      {attributions.length === 0 ? (
        <div className="p-6 text-center text-xs text-slate-400">
          No specific line attributions returned by the model for this snippet.
        </div>
      ) : (
        <div className="overflow-x-auto">
          {/* Summary table of attributed lines */}
          <div className="p-4 bg-slate-950/40 border-b border-slate-800/60">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
              {attributions.map((attr, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between rounded-lg border border-rose-500/20 bg-rose-500/5 px-3 py-2 text-xs"
                >
                  <div className="flex items-center gap-2">
                    <span className="flex h-5 w-5 items-center justify-center rounded bg-rose-500/20 font-mono text-[11px] font-bold text-rose-300">
                      L{attr.line}
                    </span>
                    <span className="font-mono text-slate-300 truncate max-w-[140px]" title={attr.snippet}>
                      {attr.snippet || `Line ${attr.line}`}
                    </span>
                  </div>
                  <span className="rounded bg-rose-500/20 px-1.5 py-0.5 font-mono text-[11px] font-bold text-rose-300">
                    +{Math.abs(attr.score).toFixed(3)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Interactive Code Viewer highlighting culprit lines */}
          <div className="p-3 bg-[#080c14] font-mono text-xs leading-6 overflow-x-auto">
            {lines.map((line, idx) => {
              const lineNum = idx + 1;
              const attr = attrMap.get(lineNum);
              const isFlagged = Boolean(attr);

              return (
                <div
                  key={idx}
                  className={`flex items-start group rounded transition-colors ${
                    isFlagged
                      ? 'bg-rose-950/40 border-l-3 border-rose-500 pl-2'
                      : 'hover:bg-slate-900/60 pl-3'
                  }`}
                >
                  {/* Line Number */}
                  <span
                    className={`select-none text-right pr-4 font-mono text-xs w-10 flex-shrink-0 ${
                      isFlagged ? 'text-rose-400 font-bold' : 'text-slate-400'
                    }`}
                  >
                    {lineNum}
                  </span>

                  {/* Flag Icon */}
                  <span className="w-5 flex-shrink-0 pt-1">
                    {isFlagged && (
                      <AlertTriangle className="h-3.5 w-3.5 text-rose-400" />
                    )}
                  </span>

                  {/* Code text */}
                  <span
                    className={`flex-1 whitespace-pre font-mono text-xs sm:text-sm ${
                      isFlagged ? 'text-rose-200 font-medium' : 'text-slate-300'
                    }`}
                  >
                    {line || ' '}
                  </span>

                  {/* Attribution Impact Tag */}
                  {isFlagged && (
                    <span className="ml-3 select-none rounded bg-rose-500/20 px-2 py-0.5 text-[10px] font-mono font-bold text-rose-300 border border-rose-500/30">
                      Occlusion Δ {Math.abs(attr!.score).toFixed(3)}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
