import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Code2,
  Play,
  RotateCcw,
  AlertCircle,
  Sparkles,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  Terminal,
  FileSearch
} from 'lucide-react';
import { CodeEditor } from '../components/scanner/CodeEditor';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useScan } from '../context/ScanContext';

export const CodeScannerPage: React.FC = () => {
  const navigate = useNavigate();
  const {
    currentCodeSnippet,
    currentLanguage,
    runFileScan,
    clearCurrentScan,
    isScanning,
    scanError
  } = useScan();

  const [code, setCode] = useState<string>(() => currentCodeSnippet || '');
  const [language, setLanguage] = useState<string>(() => currentLanguage || 'auto');
  const [localError, setLocalError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    if (!code || !code.trim()) {
      setLocalError('Please paste or write source code before initiating analysis.');
      return;
    }
    setLocalError(null);

    try {
      await runFileScan(code, language);
      navigate('/results');
    } catch (err: any) {
      setLocalError(err.message || 'Analysis failed. Check backend connectivity.');
    }
  };

  const handleClear = () => {
    setCode('');
    setLocalError(null);
    clearCurrentScan();
  };

  return (
    <div className="space-y-6">
      {/* Header section */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2 text-purple-400 text-xs font-semibold uppercase tracking-wider mb-1">
            <Sparkles className="h-3.5 w-3.5" />
            <span>AI Neural Inference</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Static & Semantic Vulnerability Scanner
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl">
            Pass code snippets directly to CodeSentinel's deep learning ONNX model for instant vulnerability classification, CWE identification, and line-level occlusion attribution.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={handleClear}
            disabled={isScanning || !code}
            className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800/80 px-4 py-2.5 text-xs font-semibold text-slate-300 hover:bg-slate-700 hover:text-white transition-all disabled:opacity-40 cursor-pointer"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Reset</span>
          </button>

          <button
            type="button"
            onClick={handleAnalyze}
            disabled={isScanning || !code.trim()}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-600 px-5 py-2.5 text-xs sm:text-sm font-semibold text-white shadow-lg shadow-purple-600/30 hover:from-purple-500 hover:to-cyan-500 transition-all disabled:opacity-50 cursor-pointer"
          >
            {isScanning ? (
              <>
                <LoadingSpinner size="sm" />
                <span>Analyzing Neural Graph...</span>
              </>
            ) : (
              <>
                <Play className="h-4 w-4 fill-current" />
                <span>Analyze Code</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {(localError || scanError) && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs sm:text-sm text-rose-300 flex items-start gap-3 backdrop-blur-md">
          <AlertCircle className="h-5 w-5 text-rose-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold text-rose-200">Analysis Error</p>
            <p className="text-rose-300/90">{localError || scanError}</p>
          </div>
        </div>
      )}

      {/* Code Editor Component */}
      <div className="relative">
        <CodeEditor
          value={code}
          onChange={setCode}
          language={language}
          onLanguageChange={setLanguage}
          onClear={handleClear}
          disabled={isScanning}
        />

        {/* Scanning Overlay Animation */}
        {isScanning && (
          <div className="absolute inset-0 z-20 flex flex-col items-center justify-center rounded-xl bg-slate-950/80 backdrop-blur-md">
            <div className="relative mb-4 flex items-center justify-center">
              <div className="h-20 w-20 rounded-full border-2 border-purple-500/20 border-t-purple-500 animate-spin" />
              <div className="absolute h-14 w-14 rounded-full border-2 border-cyan-500/30 border-b-cyan-400 animate-spin-reverse" />
              <FileSearch className="absolute h-8 w-8 text-purple-400 animate-pulse" />
            </div>
            <p className="text-base font-bold text-white tracking-wide">
              Analyzing AST & Token Embeddings
            </p>
            <p className="text-xs text-slate-400 mt-1">
              Executing ONNX session & calculating occlusion line attributions...
            </p>
          </div>
        )}
      </div>

      {/* Instructions & Features info grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
        <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-4">
          <div className="flex items-center gap-2 font-semibold text-slate-200 mb-1.5">
            <Terminal className="h-4 w-4 text-purple-400" />
            <span>Endpoint: POST /score-file</span>
          </div>
          <p className="text-slate-400 leading-relaxed">
            Sends your snippet directly to the FastAPI server which runs it through the tokenizer and ONNX runtime without external cloud dependencies.
          </p>
        </div>

        <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-4">
          <div className="flex items-center gap-2 font-semibold text-slate-200 mb-1.5">
            <ShieldAlert className="h-4 w-4 text-amber-400" />
            <span>Multi-CWE Classifier</span>
          </div>
          <p className="text-slate-400 leading-relaxed">
            Computes multi-class probability scores across known CWE vulnerabilities including SQL Injection (CWE-89), XSS (CWE-79), and Buffer Overflows (CWE-119).
          </p>
        </div>

        <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-4">
          <div className="flex items-center gap-2 font-semibold text-slate-200 mb-1.5">
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            <span>Explainable AI (XAI)</span>
          </div>
          <p className="text-slate-400 leading-relaxed">
            Masks lines systematically using occlusion attribution to pinpoint the exact syntax tokens responsible for triggering the vulnerability score.
          </p>
        </div>
      </div>
    </div>
  );
};
