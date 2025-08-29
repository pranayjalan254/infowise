import { useState } from 'react';
import { motion } from 'framer-motion';
import { CheckCircle, XCircle, AlertTriangle, RefreshCw, Eye, ThumbsUp, ThumbsDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { mockQAResults } from '@/data/mockData';
import { QAResult } from '@/types';

export function QAStep() {
  const [qaResults, setQAResults] = useState(mockQAResults);
  const [reprocessing, setReprocessing] = useState(false);

  const handleApprove = (id: string) => {
    setQAResults(prev => 
      prev.map(result => 
        result.id === id ? { ...result, status: 'approved' } : result
      )
    );
  };

  const handleReject = (id: string) => {
    setQAResults(prev => 
      prev.map(result => 
        result.id === id ? { ...result, status: 'rejected' } : result
      )
    );
  };

  const handleReprocess = () => {
    setReprocessing(true);
    setTimeout(() => {
      setReprocessing(false);
      // Simulate improved results
      setQAResults(prev => 
        prev.map(result => ({
          ...result,
          status: Math.random() > 0.5 ? 'approved' : 'pending'
        }))
      );
    }, 3000);
  };

  const getTypeIcon = (type: QAResult['type']) => {
    switch (type) {
      case 'missed_pii':
        return <AlertTriangle size={16} className="text-danger" />;
      case 'false_positive':
        return <XCircle size={16} className="text-warning" />;
      case 'masking_error':
        return <AlertTriangle size={16} className="text-warning" />;
      default:
        return <AlertTriangle size={16} className="text-muted-foreground" />;
    }
  };

  const getSeverityColor = (severity: QAResult['severity']) => {
    switch (severity) {
      case 'high':
        return 'status-danger';
      case 'medium':
        return 'status-warning';
      default:
        return 'status-success';
    }
  };

  const getStatusColor = (status: QAResult['status']) => {
    switch (status) {
      case 'approved':
        return 'status-success';
      case 'rejected':
        return 'status-danger';
      default:
        return 'status-warning';
    }
  };

  const approvedCount = qaResults.filter(r => r.status === 'approved').length;
  const rejectedCount = qaResults.filter(r => r.status === 'rejected').length;
  const pendingCount = qaResults.filter(r => r.status === 'pending').length;
  const qualityScore = Math.round((approvedCount / qaResults.length) * 100);

  return (
    <motion.div
      className="space-y-6"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Header */}
      <div className="neumorphic-card p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-xl font-semibold text-foreground">
              Quality Assurance Review
            </h3>
            <p className="text-muted-foreground">
              AI Agent 4 performs reflection and human-in-the-loop validation
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <Button
              variant="outline"
              size="sm"
              className="neumorphic-button"
            >
              <Eye size={16} className="mr-2" />
              View Full Report
            </Button>
            <Button
              onClick={handleReprocess}
              disabled={reprocessing}
              className="neumorphic-button"
            >
              {reprocessing ? (
                <RefreshCw size={16} className="mr-2 animate-spin" />
              ) : (
                <RefreshCw size={16} className="mr-2" />
              )}
              {reprocessing ? 'Reprocessing...' : 'Reprocess'}
            </Button>
          </div>
        </div>

        {/* Quality Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="neumorphic-flat p-4 rounded-xl text-center">
            <div className="text-2xl font-bold text-success mb-1">{qualityScore}%</div>
            <div className="text-sm text-muted-foreground">Quality Score</div>
          </div>
          <div className="neumorphic-flat p-4 rounded-xl text-center">
            <div className="text-2xl font-bold text-success mb-1">{approvedCount}</div>
            <div className="text-sm text-muted-foreground">Approved</div>
          </div>
          <div className="neumorphic-flat p-4 rounded-xl text-center">
            <div className="text-2xl font-bold text-danger mb-1">{rejectedCount}</div>
            <div className="text-sm text-muted-foreground">Rejected</div>
          </div>
          <div className="neumorphic-flat p-4 rounded-xl text-center">
            <div className="text-2xl font-bold text-warning mb-1">{pendingCount}</div>
            <div className="text-sm text-muted-foreground">Pending Review</div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-4">
          <div className="flex justify-between text-sm text-muted-foreground mb-2">
            <span>Review Progress</span>
            <span>{qaResults.length - pendingCount} of {qaResults.length} reviewed</span>
          </div>
          <Progress 
            value={(qaResults.length - pendingCount) / qaResults.length * 100} 
            className="h-2"
          />
        </div>
      </div>

      {/* QA Results */}
      <div className="neumorphic-card p-6">
        <h4 className="text-lg font-semibold text-foreground mb-4">
          Quality Assurance Findings
        </h4>
        
        <div className="space-y-4">
          {qaResults.map((result, index) => (
            <motion.div
              key={result.id}
              className="neumorphic-flat p-4 rounded-xl"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3 flex-1">
                  {getTypeIcon(result.type)}
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-2">
                      <h5 className="font-medium text-foreground capitalize">
                        {result.type.replace('_', ' ')}
                      </h5>
                      <Badge className={`${getSeverityColor(result.severity)} border text-xs`}>
                        {result.severity.toUpperCase()}
                      </Badge>
                      <Badge className={`${getStatusColor(result.status)} border text-xs`}>
                        {result.status.toUpperCase()}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {result.description}
                    </p>
                  </div>
                </div>
                
                {result.status === 'pending' && (
                  <div className="flex items-center space-x-2 ml-4">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleApprove(result.id)}
                      className="neumorphic-button text-success hover:bg-success/10"
                    >
                      <ThumbsUp size={14} className="mr-1" />
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleReject(result.id)}
                      className="neumorphic-button text-danger hover:bg-danger/10"
                    >
                      <ThumbsDown size={14} className="mr-1" />
                      Reject
                    </Button>
                  </div>
                )}
                
                {result.status === 'approved' && (
                  <div className="flex items-center space-x-2 text-success">
                    <CheckCircle size={16} />
                    <span className="text-sm font-medium">Approved</span>
                  </div>
                )}
                
                {result.status === 'rejected' && (
                  <div className="flex items-center space-x-2 text-danger">
                    <XCircle size={16} />
                    <span className="text-sm font-medium">Rejected</span>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Quality Insights */}
      <div className="neumorphic-card p-6">
        <h4 className="text-lg font-semibold text-foreground mb-4">
          Quality Insights & Recommendations
        </h4>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="neumorphic-flat p-4 rounded-xl">
            <h5 className="font-medium text-foreground mb-2">Accuracy Analysis</h5>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• PII Detection accuracy: 94.2%</li>
              <li>• False positive rate: 3.1%</li>
              <li>• Missed PII instances: 2.7%</li>
            </ul>
          </div>
          
          <div className="neumorphic-flat p-4 rounded-xl">
            <h5 className="font-medium text-foreground mb-2">Improvement Suggestions</h5>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• Fine-tune SSN detection patterns</li>
              <li>• Review email domain whitelist</li>
              <li>• Update masking templates</li>
            </ul>
          </div>
        </div>
      </div>

      {reprocessing && (
        <motion.div
          className="neumorphic-card p-6 text-center"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <RefreshCw size={24} className="mx-auto mb-2 animate-spin text-primary" />
          <h4 className="font-medium text-foreground mb-1">Reprocessing Data</h4>
          <p className="text-sm text-muted-foreground">
            Applying corrections and re-running quality checks...
          </p>
        </motion.div>
      )}
    </motion.div>
  );
}