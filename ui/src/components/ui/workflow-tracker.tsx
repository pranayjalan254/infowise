import { motion } from 'framer-motion';
import { Check, Circle, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { WorkflowStep } from '@/types';

interface WorkflowTrackerProps {
  steps: WorkflowStep[];
}

export function WorkflowTracker({ steps }: WorkflowTrackerProps) {
  const getStepIcon = (status: WorkflowStep['status']) => {
    switch (status) {
      case 'completed':
        return <Check size={16} />;
      case 'active':
        return <Circle size={16} className="animate-pulse" />;
      default:
        return <Clock size={16} />;
    }
  };

  const getStepClassName = (status: WorkflowStep['status']) => {
    switch (status) {
      case 'completed':
        return 'step-completed';
      case 'active':
        return 'step-active';
      default:
        return 'step-pending';
    }
  };

  return (
    <div className="neumorphic-card p-6">
      <h3 className="text-lg font-semibold text-foreground mb-6">
        Workflow Progress
      </h3>
      
      <div className="space-y-4">
        {steps.map((step, index) => (
          <motion.div
            key={step.id}
            className="flex items-center space-x-4"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: index * 0.1 }}
          >
            <div className={cn(
              'w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0',
              getStepClassName(step.status)
            )}>
              {getStepIcon(step.status)}
            </div>
            
            <div className="flex-1">
              <h4 className="font-medium text-foreground">
                {step.name}
              </h4>
              <p className="text-sm text-muted-foreground">
                {step.description}
              </p>
            </div>
            
            {index < steps.length - 1 && (
              <div className="w-px h-8 bg-border absolute ml-5 mt-12" />
            )}
          </motion.div>
        ))}
      </div>
    </div>
  );
}