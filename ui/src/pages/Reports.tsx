import { motion } from 'framer-motion';
import { Download, FileText, Calendar, Filter } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { mockComplianceFrameworks, chartData } from '@/data/mockData';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const reportTypes = [
  {
    id: 'compliance-summary',
    title: 'Compliance Summary Report',
    description: 'Overview of all regulatory compliance status',
    lastGenerated: '2 hours ago',
    status: 'ready'
  },
  {
    id: 'pii-audit',
    title: 'PII Detection Audit',
    description: 'Detailed analysis of PII found and processed',
    lastGenerated: '1 day ago',
    status: 'ready'
  },
  {
    id: 'risk-assessment',
    title: 'Risk Assessment Report',
    description: 'Risk analysis across all data categories',
    lastGenerated: '3 hours ago',
    status: 'ready'
  },
  {
    id: 'masking-effectiveness',
    title: 'Masking Effectiveness Analysis',
    description: 'Quality and effectiveness of data masking',
    lastGenerated: '5 hours ago',
    status: 'generating'
  },
  {
    id: 'compliance-trend',
    title: 'Compliance Trend Analysis',
    description: 'Historical compliance performance trends',
    lastGenerated: '1 week ago',
    status: 'ready'
  },
  {
    id: 'data-lineage',
    title: 'Data Lineage Report',
    description: 'Complete data processing and transformation history',
    lastGenerated: '2 days ago',
    status: 'ready'
  }
];

export default function Reports() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <h1 className="text-3xl font-bold text-display text-foreground mb-2">
          Reports & Analytics
        </h1>
        <p className="text-muted-foreground">
          Generate and export comprehensive compliance and privacy reports
        </p>
      </motion.div>

      {/* Quick Actions */}
      <motion.div
        className="neumorphic-card p-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-foreground">
            Quick Actions
          </h3>
          <div className="flex items-center space-x-2">
            <Button variant="outline" size="sm" className="neumorphic-button">
              <Filter size={16} className="mr-2" />
              Filter Reports
            </Button>
            <Button variant="outline" size="sm" className="neumorphic-button">
              <Calendar size={16} className="mr-2" />
              Schedule Report
            </Button>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Button className="neumorphic-button h-auto p-4 flex-col space-y-2">
            <FileText size={24} />
            <span className="text-sm">Generate All Reports</span>
          </Button>
          <Button variant="outline" className="neumorphic-button h-auto p-4 flex-col space-y-2">
            <Download size={24} />
            <span className="text-sm">Export to PDF</span>
          </Button>
          <Button variant="outline" className="neumorphic-button h-auto p-4 flex-col space-y-2">
            <Calendar size={24} />
            <span className="text-sm">Custom Date Range</span>
          </Button>
          <Button variant="outline" className="neumorphic-button h-auto p-4 flex-col space-y-2">
            <Filter size={24} />
            <span className="text-sm">Advanced Filters</span>
          </Button>
        </div>
      </motion.div>

      {/* Compliance Dashboard */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <motion.div
          className="chart-container"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, delay: 0.2 }}
        >
          <h3 className="text-lg font-semibold text-foreground mb-4">
            Compliance Framework Status
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData.complianceScores}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis 
                dataKey="framework" 
                fontSize={12}
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
              />
              <YAxis 
                fontSize={12}
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
              />
              <Tooltip 
                contentStyle={{
                  backgroundColor: 'hsl(var(--popover))',
                  border: 'none',
                  borderRadius: '12px',
                  boxShadow: 'var(--shadow-light), var(--shadow-dark)'
                }}
              />
              <Bar 
                dataKey="score" 
                fill="hsl(var(--primary))"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </motion.div>

        <motion.div
          className="chart-container"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, delay: 0.3 }}
        >
          <h3 className="text-lg font-semibold text-foreground mb-4">
            Risk Distribution
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={chartData.sensitivityAnalysis}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                dataKey="value"
              >
                {chartData.sensitivityAnalysis.map((entry, index) => (
                  <Cell key={index} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-center space-x-4 mt-4">
            {chartData.sensitivityAnalysis.map((item) => (
              <div key={item.name} className="flex items-center space-x-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-sm text-muted-foreground">
                  {item.name} Risk
                </span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Available Reports */}
      <motion.div
        className="neumorphic-card p-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.4 }}
      >
        <h3 className="text-lg font-semibold text-foreground mb-4">
          Available Reports
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {reportTypes.map((report, index) => (
            <motion.div
              key={report.id}
              className="neumorphic-card p-4 hover:neumorphic-raised transition-all duration-300"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
            >
              <div className="flex items-start justify-between mb-3">
                <FileText size={20} className="text-primary flex-shrink-0" />
                <Badge 
                  className={`text-xs ${
                    report.status === 'ready' ? 'status-success border' : 'status-warning border'
                  }`}
                >
                  {report.status === 'ready' ? 'Ready' : 'Generating...'}
                </Badge>
              </div>
              
              <h4 className="font-medium text-foreground mb-2">
                {report.title}
              </h4>
              <p className="text-sm text-muted-foreground mb-3">
                {report.description}
              </p>
              
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">
                  Updated {report.lastGenerated}
                </span>
                <Button 
                  size="sm" 
                  variant="ghost"
                  disabled={report.status === 'generating'}
                  className="neumorphic-button text-xs"
                >
                  <Download size={12} className="mr-1" />
                  Export
                </Button>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Compliance Framework Details */}
      <motion.div
        className="neumorphic-card p-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.5 }}
      >
        <h3 className="text-lg font-semibold text-foreground mb-4">
          Regulatory Compliance Status
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {mockComplianceFrameworks.map((framework, index) => (
            <motion.div
              key={framework.id}
              className="neumorphic-flat p-4 rounded-xl"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
            >
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-medium text-foreground">{framework.name}</h4>
                <div className="text-right">
                  <div className="text-lg font-bold text-foreground">
                    {framework.score}%
                  </div>
                  <Badge 
                    className={`text-xs ${
                      framework.status === 'compliant' ? 'status-success border' :
                      framework.status === 'at-risk' ? 'status-warning border' :
                      'status-danger border'
                    }`}
                  >
                    {framework.status.replace('-', ' ').toUpperCase()}
                  </Badge>
                </div>
              </div>
              
              <div className="space-y-2">
                {framework.requirements.slice(0, 2).map((req) => (
                  <div key={req.id} className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{req.name}</span>
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
              
              <Button 
                size="sm" 
                variant="ghost" 
                className="neumorphic-button w-full mt-3 text-xs"
              >
                <FileText size={12} className="mr-1" />
                Generate {framework.name} Report
              </Button>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}