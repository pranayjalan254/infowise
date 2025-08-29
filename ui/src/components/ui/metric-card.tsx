import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { DashboardMetric } from '@/types';
import * as LucideIcons from 'lucide-react';

interface MetricCardProps {
  metric: DashboardMetric;
  index: number;
}

export function MetricCard({ metric, index }: MetricCardProps) {
  const IconComponent = (LucideIcons as any)[metric.icon] || LucideIcons.BarChart3;
  
  const getTrendIcon = () => {
    switch (metric.trend) {
      case 'up':
        return <TrendingUp size={16} className="text-success" />;
      case 'down':
        return <TrendingDown size={16} className="text-danger" />;
      default:
        return <Minus size={16} className="text-muted-foreground" />;
    }
  };

  const getTrendColor = () => {
    switch (metric.trend) {
      case 'up':
        return 'text-success';
      case 'down':
        return 'text-danger';
      default:
        return 'text-muted-foreground';
    }
  };

  return (
    <motion.div
      className="neumorphic-card p-6 hover:neumorphic-raised transition-all duration-300"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.1 }}
      whileHover={{ y: -2 }}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="neumorphic-raised p-3 rounded-xl">
          <IconComponent size={24} className="text-primary" />
        </div>
        <div className="flex items-center space-x-1">
          {getTrendIcon()}
          <span className={cn('text-sm font-medium', getTrendColor())}>
            {metric.change > 0 ? '+' : ''}{metric.change}%
          </span>
        </div>
      </div>
      
      <div>
        <h3 className="text-2xl font-bold text-foreground mb-1">
          {metric.value}
        </h3>
        <p className="text-sm text-muted-foreground">
          {metric.title}
        </p>
      </div>
    </motion.div>
  );
}