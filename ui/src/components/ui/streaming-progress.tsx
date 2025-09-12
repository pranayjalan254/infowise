import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, CheckCircle, Loader2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

interface PageProgress {
  page: number;
  message: string;
  piiCount: number;
  timestamp: Date;
  completed: boolean;
}

interface StreamingProgressProps {
  documentName?: string;
  totalPages?: number;
  className?: string;
}

export function StreamingProgress({
  documentName,
  totalPages,
  className = "",
}: StreamingProgressProps) {
  const [pages, setPages] = useState<PageProgress[]>([]);
  const [currentPage, setCurrentPage] = useState<number | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [totalPiiFound, setTotalPiiFound] = useState(0);

  const addPageProgress = (pageData: {
    page: number;
    message: string;
    piiCount: number;
    totalFound?: number;
  }) => {
    const newPageProgress: PageProgress = {
      page: pageData.page,
      message: pageData.message,
      piiCount: pageData.piiCount,
      timestamp: new Date(),
      completed: true,
    };

    setPages((prev) => {
      const filtered = prev.filter((p) => p.page !== pageData.page);
      return [...filtered, newPageProgress].sort((a, b) => a.page - b.page);
    });

    if (pageData.totalFound !== undefined) {
      setTotalPiiFound(pageData.totalFound);
    }
  };

  const setCurrentProcessingPage = (page: number) => {
    setCurrentPage(page);

    // Add a "processing" entry for the current page
    setPages((prev) => {
      const filtered = prev.filter((p) => p.page !== page);
      const processingEntry: PageProgress = {
        page,
        message: `Analyzing page ${page}...`,
        piiCount: 0,
        timestamp: new Date(),
        completed: false,
      };
      return [...filtered, processingEntry].sort((a, b) => a.page - b.page);
    });
  };

  const markComplete = () => {
    setIsComplete(true);
    setCurrentPage(null);
  };

  // Expose methods to parent component
  useEffect(() => {
    (window as any).streamingProgress = {
      addPageProgress,
      setCurrentProcessingPage,
      markComplete,
    };

    return () => {
      delete (window as any).streamingProgress;
    };
  }, []);

  const getProgressPercentage = () => {
    if (!totalPages) return 0;
    const completedPages = pages.filter((p) => p.completed).length;
    return Math.round((completedPages / totalPages) * 100);
  };

  const getVisiblePages = () => {
    // Show last 5 completed pages plus current processing page
    const completed = pages.filter((p) => p.completed).slice(-5);
    const processing = pages.filter((p) => !p.completed);
    return [...completed, ...processing];
  };

  return (
    <Card className={`p-6 ${className}`}>
      <div className="space-y-6">
        {/* Header */}
        <div className="text-center space-y-3">
          <div className="flex items-center justify-center space-x-2">
            {isComplete ? (
              <CheckCircle className="w-6 h-6 text-green-500" />
            ) : (
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
            )}
            <h3 className="text-lg font-semibold">
              {isComplete ? "PII Detection Complete" : "Detecting PII..."}
            </h3>
          </div>

          {documentName && (
            <p className="text-sm text-muted-foreground">
              Processing: <span className="font-medium">{documentName}</span>
            </p>
          )}

          {totalPages && (
            <div className="space-y-2">
              <Progress value={getProgressPercentage()} className="w-full" />
              <p className="text-xs text-muted-foreground">
                {pages.filter((p) => p.completed).length} of {totalPages} pages
                processed
              </p>
            </div>
          )}
        </div>

        {/* Page Progress List */}
        <div className="space-y-2 max-h-64 overflow-y-auto">
          <AnimatePresence mode="popLayout">
            {getVisiblePages().map((pageProgress) => (
              <motion.div
                key={`page-${pageProgress.page}`}
                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                animate={{
                  opacity: 1,
                  y: 0,
                  scale: 1,
                  backgroundColor: pageProgress.completed
                    ? "transparent"
                    : "hsl(var(--primary) / 0.05)",
                }}
                exit={{ opacity: 0, y: -20, scale: 0.95 }}
                transition={{
                  duration: 0.3,
                  ease: "easeOut",
                  backgroundColor: { duration: 0.5 },
                }}
                className={`
                  p-3 rounded-lg border transition-all duration-300
                  ${
                    pageProgress.completed
                      ? "border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950"
                      : "border-primary/20 bg-primary/5 shadow-sm"
                  }
                `}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    {pageProgress.completed ? (
                      <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />
                    ) : (
                      <div className="relative">
                        <Search className="w-4 h-4 text-primary flex-shrink-0" />
                        <div className="absolute inset-0 animate-ping">
                          <Search className="w-4 h-4 text-primary/50" />
                        </div>
                      </div>
                    )}

                    <div className="min-w-0 flex-1">
                      <p
                        className={`text-sm font-medium ${
                          pageProgress.completed
                            ? "text-green-700 dark:text-green-300"
                            : "text-primary"
                        }`}
                      >
                        {pageProgress.message}
                      </p>

                      {pageProgress.completed && (
                        <p className="text-xs text-muted-foreground">
                          {pageProgress.piiCount === 0
                            ? "No PII found"
                            : `${pageProgress.piiCount} PII entities detected`}
                        </p>
                      )}
                    </div>
                  </div>

                  {pageProgress.completed && pageProgress.piiCount > 0 && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 0.2, type: "spring" }}
                      className="bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 text-xs px-2 py-1 rounded-full font-medium"
                    >
                      {pageProgress.piiCount}
                    </motion.div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        {/* Summary */}
        {(isComplete || totalPiiFound > 0) && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center p-4 bg-muted/50 rounded-lg"
          >
            <p className="text-sm font-medium">
              Total PII Entities Found:
              <span className="ml-2 text-lg font-bold text-primary">
                {totalPiiFound}
              </span>
            </p>

            {isComplete && (
              <p className="text-xs text-muted-foreground mt-1">
                Detection completed successfully
              </p>
            )}
          </motion.div>
        )}
      </div>
    </Card>
  );
}

// Hook for using the streaming progress
export function useStreamingProgress() {
  const addPageProgress = (pageData: {
    page: number;
    message: string;
    piiCount: number;
    totalFound?: number;
  }) => {
    (window as any).streamingProgress?.addPageProgress(pageData);
  };

  const setCurrentProcessingPage = (page: number) => {
    (window as any).streamingProgress?.setCurrentProcessingPage(page);
  };

  const markComplete = () => {
    (window as any).streamingProgress?.markComplete();
  };

  return {
    addPageProgress,
    setCurrentProcessingPage,
    markComplete,
  };
}
