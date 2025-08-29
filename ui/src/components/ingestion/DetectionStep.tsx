import { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Filter, Eye, AlertTriangle } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { mockPIIDetections } from '@/data/mockData';
import { PIIDetection } from '@/types';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

export function DetectionStep() {
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');

  const filteredDetections = mockPIIDetections.filter(detection => {
    const matchesSearch = detection.extractedValue.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         detection.type.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = typeFilter === 'all' || detection.type === typeFilter;
    const matchesSeverity = severityFilter === 'all' || detection.severity === severityFilter;
    
    return matchesSearch && matchesType && matchesSeverity;
  });

  const getSeverityColor = (severity: PIIDetection['severity']) => {
    switch (severity) {
      case 'high':
        return 'status-danger';
      case 'medium':
        return 'status-warning';
      default:
        return 'status-success';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'text-success';
    if (confidence >= 0.7) return 'text-warning';
    return 'text-danger';
  };

  return (
    <motion.div
      className="space-y-6"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Header */}
      <div className="neumorphic-card p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-xl font-semibold text-foreground">
              PII Detection Results
            </h3>
            <p className="text-muted-foreground">
              AI Agent 1 has identified {mockPIIDetections.length} potential PII instances
            </p>
          </div>
          <Button className="neumorphic-button">
            <Eye size={16} className="mr-2" />
            View Documents
          </Button>
        </div>

        {/* Filters */}
        <div className="flex items-center space-x-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" size={16} />
            <Input
              placeholder="Search detected PII..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="neumorphic-input pl-10"
            />
          </div>
          
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="neumorphic-input w-48">
              <SelectValue placeholder="Filter by type" />
            </SelectTrigger>
            <SelectContent className="neumorphic-card border-0">
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="Social Security Number">SSN</SelectItem>
              <SelectItem value="Email Address">Email</SelectItem>
              <SelectItem value="Phone Number">Phone</SelectItem>
              <SelectItem value="Credit Card Number">Credit Card</SelectItem>
              <SelectItem value="Date of Birth">Date of Birth</SelectItem>
            </SelectContent>
          </Select>

          <Select value={severityFilter} onValueChange={setSeverityFilter}>
            <SelectTrigger className="neumorphic-input w-48">
              <SelectValue placeholder="Filter by severity" />
            </SelectTrigger>
            <SelectContent className="neumorphic-card border-0">
              <SelectItem value="all">All Severities</SelectItem>
              <SelectItem value="high">High Risk</SelectItem>
              <SelectItem value="medium">Medium Risk</SelectItem>
              <SelectItem value="low">Low Risk</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Detection Results Table */}
      <div className="neumorphic-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-6 py-4 text-left text-sm font-medium text-foreground">
                  PII Type
                </th>
                <th className="px-6 py-4 text-left text-sm font-medium text-foreground">
                  Extracted Value
                </th>
                <th className="px-6 py-4 text-left text-sm font-medium text-foreground">
                  Location
                </th>
                <th className="px-6 py-4 text-left text-sm font-medium text-foreground">
                  Confidence
                </th>
                <th className="px-6 py-4 text-left text-sm font-medium text-foreground">
                  Severity
                </th>
                <th className="px-6 py-4 text-left text-sm font-medium text-foreground">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {filteredDetections.map((detection, index) => (
                <motion.tr
                  key={detection.id}
                  className="hover:bg-muted/30 transition-colors"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2, delay: index * 0.05 }}
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center space-x-2">
                      <AlertTriangle size={16} className="text-primary" />
                      <span className="font-medium text-foreground">
                        {detection.type}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <code className="neumorphic-pressed px-3 py-1 rounded-lg text-sm bg-muted">
                      {detection.extractedValue}
                    </code>
                  </td>
                  <td className="px-6 py-4 text-sm text-muted-foreground">
                    {detection.location}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`font-medium ${getConfidenceColor(detection.confidence)}`}>
                      {(detection.confidence * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <Badge className={`${getSeverityColor(detection.severity)} border`}>
                      {detection.severity.toUpperCase()}
                    </Badge>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center space-x-2">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="neumorphic-button text-xs"
                      >
                        Review
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="neumorphic-button text-xs"
                      >
                        Flag
                      </Button>
                    </div>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </motion.div>
  );
}