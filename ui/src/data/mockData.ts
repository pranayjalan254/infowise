import { PIIDetection, ComplianceFramework, MaskingOption, QAResult, DashboardMetric, WorkflowStep } from '@/types';

export const mockPIIDetections: PIIDetection[] = [
  {
    id: '1',
    type: 'Social Security Number',
    extractedValue: '***-**-****',
    confidence: 0.95,
    location: 'Document 1, Page 2, Line 15',
    severity: 'high'
  },
  {
    id: '2',
    type: 'Email Address',
    extractedValue: 'john.doe@email.com',
    confidence: 0.98,
    location: 'Document 1, Page 1, Line 8',
    severity: 'medium'
  },
  {
    id: '3',
    type: 'Phone Number',
    extractedValue: '(555) 123-4567',
    confidence: 0.92,
    location: 'Document 2, Page 1, Line 3',
    severity: 'medium'
  },
  {
    id: '4',
    type: 'Credit Card Number',
    extractedValue: '****-****-****-1234',
    confidence: 0.97,
    location: 'Document 3, Page 1, Line 12',
    severity: 'high'
  },
  {
    id: '5',
    type: 'Date of Birth',
    extractedValue: '01/15/1985',
    confidence: 0.89,
    location: 'Document 1, Page 1, Line 5',
    severity: 'medium'
  }
];

export const mockComplianceFrameworks: ComplianceFramework[] = [
  {
    id: 'gdpr',
    name: 'GDPR',
    status: 'at-risk',
    score: 75,
    requirements: [
      { id: '1', name: 'Data Minimization', status: 'satisfied', description: 'Collect only necessary data' },
      { id: '2', name: 'Consent Management', status: 'at-risk', description: 'Explicit user consent required' },
      { id: '3', name: 'Right to Erasure', status: 'satisfied', description: 'Ability to delete personal data' }
    ]
  },
  {
    id: 'hipaa',
    name: 'HIPAA',
    status: 'compliant',
    score: 92,
    requirements: [
      { id: '1', name: 'Administrative Safeguards', status: 'satisfied', description: 'Security officer assigned' },
      { id: '2', name: 'Physical Safeguards', status: 'satisfied', description: 'Facility access controls in place' },
      { id: '3', name: 'Technical Safeguards', status: 'satisfied', description: 'Access control and encryption' }
    ]
  },
  {
    id: 'dpdpa',
    name: 'DPDPA',
    status: 'non-compliant',
    score: 45,
    requirements: [
      { id: '1', name: 'Data Localization', status: 'violated', description: 'Data must be stored in India' },
      { id: '2', name: 'Data Protection Officer', status: 'at-risk', description: 'DPO appointment required' }
    ]
  },
  {
    id: 'glba',
    name: 'GLBA',
    status: 'compliant',
    score: 88,
    requirements: [
      { id: '1', name: 'Safeguards Rule', status: 'satisfied', description: 'Written information security program' },
      { id: '2', name: 'Privacy Rule', status: 'satisfied', description: 'Privacy notices provided' }
    ]
  }
];

export const mockMaskingOptions: MaskingOption[] = [
  {
    id: 'substitution',
    name: 'Substitution',
    description: 'Replace with realistic fake data',
    example: 'john.doe@email.com → jane.smith@email.com'
  },
  {
    id: 'redaction',
    name: 'Complete Redaction',
    description: 'Replace entire value with placeholder',
    example: 'john.doe@email.com → [REDACTED]'
  },
  {
    id: 'partial',
    name: 'Partial Masking',
    description: 'Hide part of the value',
    example: 'john.doe@email.com → j***.***@email.com'
  }
];

export const mockQAResults: QAResult[] = [
  {
    id: '1',
    type: 'missed_pii',
    description: 'Potential SSN found but not detected: XXX-XX-XXXX',
    severity: 'high',
    status: 'pending'
  },
  {
    id: '2',
    type: 'false_positive',
    description: 'Employee ID incorrectly flagged as SSN',
    severity: 'medium',
    status: 'approved'
  },
  {
    id: '3',
    type: 'masking_error',
    description: 'Email masking left domain visible',
    severity: 'low',
    status: 'rejected'
  }
];

export const mockDashboardMetrics: DashboardMetric[] = [
  {
    id: '1',
    title: 'Uploaded Documents',
    value: 1247,
    change: 12.5,
    trend: 'up',
    icon: 'FileText'
  },
  {
    id: '2',
    title: 'Detected PII',
    value: 8934,
    change: -3.2,
    trend: 'down',
    icon: 'Shield'
  },
  {
    id: '3',
    title: 'Compliance Risk Score',
    value: 78,
    change: 5.1,
    trend: 'up',
    icon: 'AlertTriangle'
  },
  {
    id: '4',
    title: 'Masked Records',
    value: 7821,
    change: 18.7,
    trend: 'up',
    icon: 'Eye'
  },
  {
    id: '5',
    title: 'Synthetic Data Generated',
    value: '2.3M',
    change: 23.4,
    trend: 'up',
    icon: 'Database'
  }
];

export const mockWorkflowSteps: WorkflowStep[] = [
  {
    id: 'detection',
    name: 'Detection',
    status: 'completed',
    description: 'AI scans and identifies PII across all documents'
  },
  {
    id: 'policy',
    name: 'Policy Advisor',
    status: 'active',
    description: 'Compliance analysis and risk assessment'
  },
  {
    id: 'masking',
    name: 'Masking',
    status: 'pending',
    description: 'Apply data protection and anonymization'
  },
  {
    id: 'qa',
    name: 'Quality Assurance',
    status: 'pending',
    description: 'Human review and validation of results'
  }
];

export const chartData = {
  sensitivityAnalysis: [
    { name: 'Low', value: 234, color: '#10B981' },
    { name: 'Medium', value: 456, color: '#F59E0B' },
    { name: 'High', value: 123, color: '#EF4444' }
  ],
  complianceScores: [
    { framework: 'GDPR', score: 75 },
    { framework: 'HIPAA', score: 92 },
    { framework: 'DPDPA', score: 45 },
    { framework: 'GLBA', score: 88 }
  ],
  monthlyTrends: [
    { month: 'Jan', documents: 1200, piiDetected: 8500, masked: 7800 },
    { month: 'Feb', documents: 1350, piiDetected: 9200, masked: 8600 },
    { month: 'Mar', documents: 1180, piiDetected: 8100, masked: 7500 },
    { month: 'Apr', documents: 1420, piiDetected: 9800, masked: 9200 },
    { month: 'May', documents: 1580, piiDetected: 10500, masked: 9800 },
    { month: 'Jun', documents: 1247, piiDetected: 8934, masked: 7821 }
  ]
};