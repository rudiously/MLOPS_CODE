import React from 'react';
import { CheckCircle2, ShieldCheck, Copy, Check } from 'lucide-react';
import { getCWEInfo } from '../../utils/cweDatabase';

interface RemediationCardProps {
  cweId: string | null | undefined;
  severity: string;
}

export const RemediationCard: React.FC<RemediationCardProps> = ({ cweId, severity }) => {
  const [copied, setCopied] = React.useState(false);
  const info = getCWEInfo(cweId);

  const getRemediationSteps = () => {
    switch (info.id) {
      case 'CWE-89':
        return [
          'Switch immediately from string concatenation or formatted f-strings to parameterized query bindings.',
          'Adopt ORM query builders (e.g. SQLAlchemy, Prisma, Hibernate) which automatically enforce bound parameters.',
          'Enforce strict input validation using schema libraries (e.g., Pydantic, Zod) with regex allowlists.',
          'Run automated SAST / DAST tools in the CI/CD pull request gatekeeper pipeline.'
        ];
      case 'CWE-119':
        return [
          'Deprecate unbounded buffer functions such as gets(), strcpy(), sprintf() in favor of bounded variants (fgets(), snprintf(), strncpy()).',
          'Enable compiler security flags (-fstack-protector-strong, -D_FORTIFY_SOURCE=2, ASLR).',
          'Validate input lengths against sizeof(destination_buffer) - 1 before memory writes.',
          'Consider rewriting memory-critical routines in memory-safe languages such as Rust or Go.'
        ];
      case 'CWE-79':
        return [
          'Contextually encode all dynamic data prior to HTML/DOM insertion (e.g., DOMPurify or framework auto-escaping).',
          'Deploy a Content Security Policy (CSP) header restricting script-src to cryptographic nonces or hashes.',
          'Avoid using dangerous innerHTML, document.write(), or eval() constructs with user-controlled input.',
          'Set HttpOnly and SameSite flags on session cookies to prevent token theft via script access.'
        ];
      default:
        return [
          'Audit all untrusted input vectors entering this method.',
          'Implement defense-in-depth sanitization and strict type checking.',
          'Write automated unit and security regression tests covering edge-case inputs.',
          'Submit the code for senior peer review and architectural vulnerability assessment.'
        ];
    }
  };

  const steps = getRemediationSteps();

  const handleCopySteps = () => {
    const text = `Remediation Guidance for ${info.id} (${info.name}):\n\n` +
      `Summary: ${info.remediation}\n\nRecommended Actions:\n` +
      steps.map((s, i) => `${i + 1}. ${s}`).join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-md space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-emerald-400" />
          <h3 className="text-base font-semibold text-white">
            Recommended Security Remediation
          </h3>
        </div>
        <button
          onClick={handleCopySteps}
          className="flex items-center gap-1 text-xs text-slate-400 hover:text-white transition-colors cursor-pointer"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-emerald-400" />
              <span className="text-emerald-400">Copied</span>
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" />
              <span>Copy Guidance</span>
            </>
          )}
        </button>
      </div>

      <div className="rounded-lg bg-emerald-950/20 border border-emerald-500/20 p-3.5 text-xs text-emerald-200 leading-relaxed">
        <p className="font-semibold text-emerald-300 mb-1">Architectural Fix Summary:</p>
        <p>{info.remediation}</p>
      </div>

      <div className="space-y-2">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Actionable Mitigation Checklist
        </div>
        <div className="space-y-2">
          {steps.map((step, idx) => (
            <div key={idx} className="flex items-start gap-2.5 text-xs text-slate-300">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 mt-0.5 flex-shrink-0" />
              <span>{step}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
