import React, { useRef, useState, useEffect } from 'react';
import {
  Upload,
  Clipboard,
  Trash2,
  FileCode,
  Sparkles,
  Check,
  Code
} from 'lucide-react';
import { SAMPLE_SNIPPETS } from './SampleSnippets';

interface CodeEditorProps {
  value: string;
  onChange: (val: string) => void;
  language: string;
  onLanguageChange: (lang: string) => void;
  onClear: () => void;
  disabled?: boolean;
}

export const CodeEditor: React.FC<CodeEditorProps> = ({
  value,
  onChange,
  language,
  onLanguageChange,
  onClear,
  disabled = false,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lineNumbersRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [copied, setCopied] = useState(false);

  const lines = value ? value.split('\n') : [''];
  const lineCount = lines.length;
  const charCount = value.length;

  // Sync scroll of line numbers and textarea
  const handleScroll = () => {
    if (textareaRef.current && lineNumbersRef.current) {
      lineNumbersRef.current.scrollTop = textareaRef.current.scrollTop;
    }
  };

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) onChange(text);
    } catch {
      // Fallback: focus textarea
      textareaRef.current?.focus();
    }
  };

  const handleCopy = async () => {
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error(e);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Auto-detect language from extension
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext === 'py') onLanguageChange('python');
    else if (ext === 'c' || ext === 'h') onLanguageChange('c');
    else if (ext === 'cpp' || ext === 'hpp' || ext === 'cc') onLanguageChange('cpp');
    else if (ext === 'js' || ext === 'jsx') onLanguageChange('javascript');
    else if (ext === 'ts' || ext === 'tsx') onLanguageChange('typescript');
    else if (ext === 'java') onLanguageChange('java');
    else if (ext === 'go') onLanguageChange('go');

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      if (content) onChange(content);
    };
    reader.readAsText(file);
    // Reset input
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleSelectSample = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const index = parseInt(e.target.value, 10);
    if (!isNaN(index) && SAMPLE_SNIPPETS[index]) {
      const sample = SAMPLE_SNIPPETS[index];
      onChange(sample.code);
      onLanguageChange(sample.language);
    }
  };

  return (
    <div className="flex flex-col rounded-xl border border-slate-800 bg-[#0d121f] overflow-hidden shadow-2xl transition-all">
      {/* Top Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 bg-slate-900/80 px-4 py-3">
        {/* Left tools: Language selector and Sample presets */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <div className="flex items-center gap-2">
            <Code className="h-4 w-4 text-purple-400" />
            <select
              value={language}
              onChange={(e) => onLanguageChange(e.target.value)}
              disabled={disabled}
              className="rounded-lg border border-slate-700 bg-slate-800/90 px-3 py-1.5 text-xs font-medium text-slate-200 focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
            >
              <option value="auto">Auto-Detect Language</option>
              <option value="python">Python</option>
              <option value="c">C / C++</option>
              <option value="javascript">JavaScript</option>
              <option value="typescript">TypeScript</option>
              <option value="java">Java</option>
              <option value="go">Go</option>
              <option value="php">PHP</option>
              <option value="ruby">Ruby</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
            <select
              onChange={handleSelectSample}
              defaultValue=""
              disabled={disabled}
              className="rounded-lg border border-purple-500/30 bg-purple-950/20 px-3 py-1.5 text-xs font-medium text-purple-300 hover:border-purple-500/50 focus:border-purple-500 focus:outline-none"
            >
              <option value="" disabled>Load Test Vulnerability Sample...</option>
              {SAMPLE_SNIPPETS.map((sample, idx) => (
                <option key={sample.title} value={idx} className="bg-slate-900 text-slate-200">
                  [{sample.category}] {sample.title}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Right tools: Upload file, Paste, Copy, Clear */}
        <div className="flex items-center gap-1.5 sm:gap-2">
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileUpload}
            className="hidden"
            accept=".py,.c,.cpp,.h,.hpp,.js,.jsx,.ts,.tsx,.java,.go,.php,.rb,.txt"
          />

          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
            className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/70 px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition-all disabled:opacity-50 cursor-pointer"
            title="Upload source file"
          >
            <Upload className="h-3.5 w-3.5 text-slate-400" />
            <span className="hidden sm:inline">Upload File</span>
          </button>

          <button
            type="button"
            onClick={handlePaste}
            disabled={disabled}
            className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/70 px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition-all disabled:opacity-50 cursor-pointer"
            title="Paste code from clipboard"
          >
            <Clipboard className="h-3.5 w-3.5 text-slate-400" />
            <span className="hidden sm:inline">Paste</span>
          </button>

          <button
            type="button"
            onClick={handleCopy}
            disabled={!value || disabled}
            className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/70 px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition-all disabled:opacity-50 cursor-pointer"
            title="Copy code"
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-400" />
                <span className="text-emerald-400">Copied</span>
              </>
            ) : (
              <>
                <FileCode className="h-3.5 w-3.5 text-slate-400" />
                <span className="hidden sm:inline">Copy</span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={onClear}
            disabled={!value || disabled}
            className="flex items-center gap-1.5 rounded-lg border border-rose-500/20 bg-rose-500/10 px-2.5 py-1.5 text-xs font-medium text-rose-300 hover:bg-rose-500/20 transition-all disabled:opacity-40 cursor-pointer"
            title="Clear code"
          >
            <Trash2 className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Clear</span>
          </button>
        </div>
      </div>

      {/* Editor Body with Gutter */}
      <div className="relative flex min-h-[380px] max-h-[600px] w-full bg-[#080c14] font-mono text-sm leading-6">
        {/* Line Numbers Gutter */}
        <div
          ref={lineNumbersRef}
          className="select-none overflow-hidden border-r border-slate-800/80 bg-[#060910] py-4 px-3 text-right font-mono text-xs text-slate-400 min-w-[3.5rem]"
        >
          {Array.from({ length: Math.max(lineCount, 16) }).map((_, i) => (
            <div key={i} className="h-6 leading-6">
              {i + 1}
            </div>
          ))}
        </div>

        {/* Text Area */}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onScroll={handleScroll}
          disabled={disabled}
          placeholder="// Paste or write source code here to analyze with CodeSentinel AI...
// Example:
// def execute_query(conn, user_id):
//     cursor = conn.cursor()
//     cursor.execute(f'SELECT * FROM users WHERE id = {user_id}')"
          className="w-full resize-y bg-transparent py-4 px-4 font-mono text-xs sm:text-sm text-slate-100 placeholder-slate-400 focus:outline-none disabled:opacity-60 leading-6 tab-4 selection:bg-purple-600/30 selection:text-purple-200"
          spellCheck={false}
        />
      </div>

      {/* Bottom Status Bar */}
      <div className="flex items-center justify-between border-t border-slate-800/80 bg-slate-900/60 px-4 py-2 text-[11px] text-slate-400 font-mono">
        <div className="flex items-center gap-4">
          <span>{lineCount} {lineCount === 1 ? 'line' : 'lines'}</span>
          <span>{charCount} characters</span>
          <span className="capitalize text-slate-400">Lang: {language}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          <span className="text-slate-400">Ready to inspect</span>
        </div>
      </div>
    </div>
  );
};
