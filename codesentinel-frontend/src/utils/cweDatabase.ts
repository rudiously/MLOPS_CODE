import { CWEInfo } from '../types';

export const CWE_DATABASE: Record<string, CWEInfo> = {
  'CWE-89': {
    id: 'CWE-89',
    name: 'SQL Injection (SQLi)',
    description: 'The software constructs all or part of an SQL command using externally influenced input from an upstream component, but it does not neutralize or incorrectly neutralizes special elements that could modify the intended SQL command.',
    owaspTop10: 'A03:2021 – Injection',
    remediation: 'Use parameterized queries, prepared statements (e.g. PDO, PreparedStatement), or Object-Relational Mappings (ORM) rather than concatenating user input directly into SQL strings. Validate inputs using strict allowlists.'
  },
  'CWE-79': {
    id: 'CWE-79',
    name: 'Cross-Site Scripting (XSS)',
    description: 'The software does not neutralize or incorrectly neutralizes user-controllable input before it is placed in output that is used as a web page that is served to other users.',
    owaspTop10: 'A03:2021 – Injection',
    remediation: 'Contextually encode all untrusted data before rendering it in HTML, JavaScript, CSS, or attribute contexts. Utilize a strict Content Security Policy (CSP) and modern frameworks that auto-escape (e.g., React, Angular).'
  },
  'CWE-119': {
    id: 'CWE-119',
    name: 'Memory Buffer Errors (Buffer Overflow)',
    description: 'The software performs operations on a memory buffer, but it can read from or write to a memory location that is outside the intended boundary of the buffer.',
    owaspTop10: 'A06:2021 – Vulnerable and Outdated Components',
    remediation: 'Use memory-safe languages (Rust, Go, Java, Python). In C/C++, use bounded APIs (e.g., snprintf instead of sprintf, fgets instead of gets) and ensure bounds checking before performing pointer arithmetic or indexing.'
  },
  'CWE-78': {
    id: 'CWE-78',
    name: 'OS Command Injection',
    description: 'The software constructs an OS command using externally-influenced input from an upstream component, but it does not neutralize or incorrectly neutralizes special elements that could modify the intended OS command.',
    owaspTop10: 'A03:2021 – Injection',
    remediation: 'Avoid invoking OS commands directly. Use built-in programming language APIs instead. If external commands are required, use argument arrays (e.g., subprocess.run(["ls", dir])) rather than shell strings (shell=True).'
  },
  'CWE-22': {
    id: 'CWE-22',
    name: 'Improper Limitation of a Pathname (Path Traversal)',
    description: 'The software uses external input to construct a pathname that is intended to identify a file or directory located under a restricted parent directory, but the software does not properly neutralize special elements such as "..".',
    owaspTop10: 'A01:2021 – Broken Access Control',
    remediation: 'Sanitize path components with canonicalization checks. Resolve paths against an allowed base directory and reject or strip any path segments that attempt directory traversal.'
  },
  '__other__': {
    id: 'CWE-Other',
    name: 'General Security Anomaly',
    description: 'The deep learning classifier identified patterns strongly correlated with security defects or anti-patterns that deviate from safe coding practices.',
    owaspTop10: 'A04:2021 – Insecure Design',
    remediation: 'Conduct a peer security review of the flagged block. Audit input sources, privilege boundaries, and resource lifetimes.'
  }
};

export function getCWEInfo(cweId: string | null | undefined): CWEInfo {
  if (!cweId) return CWE_DATABASE['__other__'];
  const normalized = cweId.toUpperCase().trim();
  return CWE_DATABASE[normalized] || {
    id: normalized,
    name: `${normalized} Security Weakness`,
    description: `Common Weakness Enumeration entry ${normalized}. Flagged by the neural vulnerability detector.`,
    owaspTop10: 'Security Vulnerability',
    remediation: 'Audit flagged code against standard OWASP and NIST secure coding guidelines.'
  };
}
