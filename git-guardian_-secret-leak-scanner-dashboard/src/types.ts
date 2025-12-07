
// Represents the core details of a rule, used within a Finding.
export interface RuleInfo {
  id: string;
  description: string;
  severity: 'Critical' | 'High' | 'Medium' | 'Low';
}

// Represents a single detected secret finding from the API.
export interface Finding {
  id: number;
  repo: string;
  branch: string;
  file_path: string;
  line: number;
  masked_snippet: string;
  commit: string;
  author: string;
  created_at: string;
  status: 'New' | 'Resolved' | 'Ignored'; // Assumed for workflow management
  rule: RuleInfo;
}

// Represents a full rule definition, including the regex pattern.
export interface Rule extends RuleInfo {
  pattern: string;
  enabled: boolean;
}

// Represents the structure of the dashboard statistics from the API.
export interface Stats {
  total_findings: number;
  findings_24h: number;
  scans: number;
}

// Represents a whitelisted item.
export interface Whitelist {
    id: string;
    type: 'Pattern' | 'Path' | 'Commit';
    value: string;
    reason: string;
}

// Represents the result of a manual scan.
export interface ScanFinding {
    rule_id: string;
    severity: 'Critical' | 'High' | 'Medium' | 'Low';
    description: string;
    masked: string;
}

export interface ScanResult {
    message: string;
    found: ScanFinding[];
    duration_ms: number;
}
