export interface WorkflowStep {
  id: string;
  name: string;
  status: 'pending' | 'active' | 'completed';
  description: string;
}

export interface PIIDetection {
  id: string;
  type: string;
  extractedValue: string;
  confidence: number;
  location: string;
  severity: 'low' | 'medium' | 'high';
}

export interface ComplianceFramework {
  id: string;
  name: string;
  status: 'compliant' | 'at-risk' | 'non-compliant';
  score: number;
  requirements: ComplianceRequirement[];
}

export interface ComplianceRequirement {
  id: string;
  name: string;
  status: 'satisfied' | 'at-risk' | 'violated';
  description: string;
}

export interface MaskingOption {
  id: string;
  name: string;
  description: string;
  example: string;
}

export interface QAResult {
  id: string;
  type: 'missed_pii' | 'false_positive' | 'masking_error';
  description: string;
  severity: 'low' | 'medium' | 'high';
  status: 'pending' | 'approved' | 'rejected';
}

export interface DashboardMetric {
  id: string;
  title: string;
  value: string | number;
  change: number;
  trend: 'up' | 'down' | 'stable';
  icon: string;
}