import { motion } from 'framer-motion';
import { CheckCircle, AlertTriangle, XCircle, Shield, FileText, Scale } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { mockComplianceFrameworks } from '@/data/mockData';
import { ComplianceFramework } from '@/types';

export function PolicyAdvisorStep() {
  const getStatusIcon = (status: ComplianceFramework['status']) => {
    switch (status) {
      case 'compliant':
        return <CheckCircle size={20} className="text-success" />;
      case 'at-risk':
        return <AlertTriangle size={20} className="text-warning" />;
      default:
        return <XCircle size={20} className="text-danger" />;
    }
  };

  const getStatusColor = (status: ComplianceFramework['status']) => {
    switch (status) {
      case 'compliant':
        return 'status-success';
      case 'at-risk':
        return 'status-warning';
      default:
        return 'status-danger';
    }
  };

  const getProgressColor = (score: number) => {
    if (score >= 80) return 'bg-success';
    if (score >= 60) return 'bg-warning';
    return 'bg-danger';
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
              Compliance Policy Analysis
            </h3>
            <p className="text-muted-foreground">
              AI Agent 2 evaluates your data against regulatory frameworks
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <Scale size={20} className="text-primary" />
            <span className="text-sm font-medium text-foreground">
              {mockComplianceFrameworks.length} Frameworks Analyzed
            </span>
          </div>
        </div>

        {/* Overall Risk Score */}
        <div className="neumorphic-flat p-4 rounded-xl">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-foreground">
              Overall Compliance Risk Score
            </span>
            <span className="text-lg font-bold text-warning">
              Medium Risk
            </span>
          </div>
          <div className="flex items-center space-x-3">
            <Progress value={72} className="flex-1" />
            <span className="text-sm font-medium text-foreground">72/100</span>
          </div>
        </div>
      </div>

      {/* Compliance Frameworks */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {mockComplianceFrameworks.map((framework, index) => (
          <motion.div
            key={framework.id}
            className="neumorphic-card p-6"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3, delay: index * 0.1 }}
          >
            {/* Framework Header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-3">
                {getStatusIcon(framework.status)}
                <div>
                  <h4 className="font-semibold text-foreground">
                    {framework.name}
                  </h4>
                  <Badge className={`${getStatusColor(framework.status)} border text-xs`}>
                    {framework.status.replace('-', ' ').toUpperCase()}
                  </Badge>
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-foreground">
                  {framework.score}
                </div>
                <div className="text-xs text-muted-foreground">
                  Compliance Score
                </div>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="mb-4">
              <Progress 
                value={framework.score} 
                className={`h-2 ${getProgressColor(framework.score)}`}
              />
            </div>

            {/* Requirements */}
            <div className="space-y-3">
              <h5 className="text-sm font-medium text-foreground flex items-center">
                <FileText size={14} className="mr-2" />
                Requirements Status
              </h5>
              {framework.requirements.map((req) => (
                <div
                  key={req.id}
                  className="flex items-center justify-between py-2 px-3 neumorphic-flat rounded-lg"
                >
                  <div className="flex items-center space-x-2">
                    {req.status === 'satisfied' && (
                      <CheckCircle size={14} className="text-success" />
                    )}
                    {req.status === 'at-risk' && (
                      <AlertTriangle size={14} className="text-warning" />
                    )}
                    {req.status === 'violated' && (
                      <XCircle size={14} className="text-danger" />
                    )}
                    <span className="text-sm text-foreground">{req.name}</span>
                  </div>
                  <Badge 
                    variant="outline" 
                    className={`text-xs ${
                      req.status === 'satisfied' ? 'border-success text-success' :
                      req.status === 'at-risk' ? 'border-warning text-warning' :
                      'border-danger text-danger'
                    }`}
                  >
                    {req.status.replace('-', ' ')}
                  </Badge>
                </div>
              ))}
            </div>

            {/* Action Items */}
            <div className="mt-4 p-3 neumorphic-pressed rounded-lg">
              <h6 className="text-xs font-medium text-muted-foreground mb-2">
                RECOMMENDED ACTIONS
              </h6>
              <ul className="text-xs text-muted-foreground space-y-1">
                {framework.status === 'at-risk' && (
                  <li>• Review consent management processes</li>
                )}
                {framework.status === 'non-compliant' && (
                  <>
                    <li>• Implement data localization measures</li>
                    <li>• Appoint Data Protection Officer</li>
                  </>
                )}
                {framework.status === 'compliant' && (
                  <li>• Maintain current compliance measures</li>
                )}
              </ul>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Risk Dashboard */}
      <div className="neumorphic-card p-6">
        <h4 className="text-lg font-semibold text-foreground mb-4 flex items-center">
          <Shield size={20} className="mr-2 text-primary" />
          Risk Dashboard
        </h4>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="neumorphic-flat p-4 rounded-xl text-center">
            <div className="text-2xl font-bold text-danger mb-1">23</div>
            <div className="text-sm text-muted-foreground">High Risk Items</div>
          </div>
          <div className="neumorphic-flat p-4 rounded-xl text-center">
            <div className="text-2xl font-bold text-warning mb-1">45</div>
            <div className="text-sm text-muted-foreground">Medium Risk Items</div>
          </div>
          <div className="neumorphic-flat p-4 rounded-xl text-center">
            <div className="text-2xl font-bold text-success mb-1">156</div>
            <div className="text-sm text-muted-foreground">Compliant Items</div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}