import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Search,
  Filter,
  Eye,
  AlertTriangle,
  Loader2,
  RefreshCw,
  ChevronRight,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  StreamingProgress,
  useStreamingProgress,
} from "@/components/ui/streaming-progress";
import { piiApi } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface PIIItem {
  id: string;
  type: string;
  text: string;
  confidence: number;
  location: string;
  severity: "low" | "medium" | "high";
  suggested_strategy: string;
  coordinates: {
    page: number;
    x0: number;
    y0: number;
    x1: number;
    y1: number;
  };
}

interface DetectionStepProps {
  documentIds: string[];
  onDetectionComplete?: (results: any) => void;
}

export function DetectionStep({
  documentIds,
  onDetectionComplete,
}: DetectionStepProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [piiDetections, setPiiDetections] = useState<PIIItem[]>([]);
  const [isDetecting, setIsDetecting] = useState(false);
  const [hasDetectionRun, setHasDetectionRun] = useState(false);
  const [detectedPIIData, setDetectedPIIData] = useState<any>(null);
  const [detectionStats, setDetectionStats] = useState<{
    totalDocuments: number;
    totalPII: number;
    documentName?: string;
    totalPages?: number;
  } | null>(null);
  const { toast } = useToast();
  const { addPageProgress, setCurrentProcessingPage, markComplete } =
    useStreamingProgress();

  // Run PII detection when component mounts or document IDs change
  useEffect(() => {
    if (documentIds.length > 0 && !hasDetectionRun) {
      runPIIDetection();
    }
  }, [documentIds, hasDetectionRun]);

  const runPIIDetection = async () => {
    if (documentIds.length === 0) {
      toast({
        title: "No documents",
        description: "Please upload documents first.",
        variant: "destructive",
      });
      return;
    }

    setIsDetecting(true);
    try {
      if (documentIds.length === 1) {
        // Single document detection with streaming
        const eventSource = piiApi.detectPIIStream(
          documentIds[0],
          (event) => {
            switch (event.type) {
              case "status":
                // Initial status messages
                break;

              case "info":
                if (event.total_pages) {
                  setDetectionStats((prev) => ({
                    ...prev,
                    totalPages: event.total_pages,
                    totalDocuments: 1,
                    totalPII: 0,
                  }));
                }
                break;

              case "progress":
                // Page processing started
                if (event.page) {
                  setCurrentProcessingPage(event.page);
                }
                break;

              case "page_complete":
                // Page processing completed
                if (event.page && event.message) {
                  addPageProgress({
                    page: event.page,
                    message: event.message,
                    piiCount: event.pii_count || 0,
                    totalFound: event.total_found,
                  });
                }
                break;

              case "complete":
                // Detection completed
                if (event.result) {
                  console.log(
                    "Detection complete, setting results:",
                    event.result
                  );

                  // Set the detection results first
                  setPiiDetections(event.result.pii_items);
                  setDetectionStats((prev) => ({
                    totalDocuments: 1,
                    totalPII: event.result.total_pii_detected,
                    documentName: event.result.document_name,
                    totalPages: prev?.totalPages || 0,
                  }));

                  // Mark detection as completed
                  setHasDetectionRun(true);
                  markComplete();

                  // Show success toast
                  toast({
                    title: "PII Detection Complete",
                    description: `Found ${event.result.total_pii_detected} PII items in ${event.result.document_name}. Review the results below.`,
                  });

                  // Set detecting to false to show results
                  console.log("Setting isDetecting to false - showing results");
                  setIsDetecting(false);

                  // Store the results for later callback when user chooses to proceed
                  setDetectedPIIData(event.result);
                } else {
                  console.error("No result data in complete event");
                  setIsDetecting(false);
                }
                break;

              case "error":
                console.error("PII detection error:", event.message);
                toast({
                  title: "Detection Failed",
                  description: event.message,
                  variant: "destructive",
                });
                console.log("Setting isDetecting to false due to error");
                setIsDetecting(false);
                break;
            }
          },
          (error) => {
            console.error("Streaming error:", error);
            toast({
              title: "Connection Error",
              description: "Lost connection during detection",
              variant: "destructive",
            });
            setIsDetecting(false);
          }
        );
      } else {
        // Batch detection for multiple documents with streaming
        const streamController = piiApi.batchDetectPIIStream(
          documentIds,
          (event) => {
            switch (event.type) {
              case "batch_start":
                setDetectionStats({
                  totalDocuments: event.total_documents,
                  totalPII: 0,
                });
                break;

              case "document_start":
                // New document started
                break;

              case "progress":
                if (event.page) {
                  setCurrentProcessingPage(event.page);
                }
                break;

              case "page_complete":
                if (event.page && event.message) {
                  addPageProgress({
                    page: event.page,
                    message: event.message,
                    piiCount: event.pii_count || 0,
                    totalFound: event.total_found,
                  });
                }
                break;

              case "complete":
                // Individual document completed
                if (event.result) {
                  setPiiDetections((prev) => [
                    ...prev,
                    ...event.result.pii_items,
                  ]);
                }
                break;

              case "batch_complete":
                setHasDetectionRun(true);
                markComplete();
                setIsDetecting(false);

                toast({
                  title: "Batch PII Detection Complete",
                  description: `Processed ${
                    detectionStats?.totalDocuments || 0
                  } documents. Review the results below.`,
                });

                // Store results for later callback
                if (piiDetections.length > 0) {
                  setDetectedPIIData({
                    pii_items: piiDetections,
                    total_pii_detected: piiDetections.length,
                    detection_date: new Date().toISOString(),
                  });
                }
                break;

              case "error":
                console.error("Batch PII detection error:", event.message);
                toast({
                  title: "Detection Failed",
                  description: event.message,
                  variant: "destructive",
                });
                setIsDetecting(false);
                break;
            }
          },
          (error) => {
            console.error("Batch streaming error:", error);
            toast({
              title: "Connection Error",
              description: "Lost connection during batch detection",
              variant: "destructive",
            });
            setIsDetecting(false);
          }
        );
      }
    } catch (error) {
      console.error("PII detection failed:", error);
      toast({
        title: "Detection Failed",
        description:
          error instanceof Error ? error.message : "Failed to detect PII",
        variant: "destructive",
      });
      setIsDetecting(false);
    }
  };

  const filteredDetections = piiDetections.filter((detection) => {
    const matchesSearch =
      detection.text.toLowerCase().includes(searchTerm.toLowerCase()) ||
      detection.type.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = typeFilter === "all" || detection.type === typeFilter;
    const matchesSeverity =
      severityFilter === "all" || detection.severity === severityFilter;

    return matchesSearch && matchesType && matchesSeverity;
  });

  // Debug logging
  console.log("DetectionStep state:", {
    isDetecting,
    hasDetectionRun,
    piiDetectionsCount: piiDetections.length,
    detectionStats,
    hasDetectedPIIData: !!detectedPIIData,
  });

  const getSeverityColor = (severity: PIIItem["severity"]) => {
    switch (severity) {
      case "high":
        return "status-danger";
      case "medium":
        return "status-warning";
      default:
        return "status-success";
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return "text-success";
    if (confidence >= 0.7) return "text-warning";
    return "text-danger";
  };

  const getAvailableTypes = () => {
    const types = [...new Set(piiDetections.map((d) => d.type))];
    return types.sort();
  };

  // Add render path debugging
  if (isDetecting) {
    console.log("Rendering: StreamingProgress");
    return (
      <motion.div
        className="space-y-6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <StreamingProgress
          documentName={detectionStats?.documentName}
          totalPages={detectionStats?.totalPages}
          className="max-w-2xl mx-auto"
        />
      </motion.div>
    );
  }

  if (!hasDetectionRun && piiDetections.length === 0) {
    console.log("Rendering: Start Detection Button");
    return (
      <motion.div
        className="flex flex-col items-center justify-center py-12 space-y-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <AlertTriangle className="w-12 h-12 text-muted-foreground" />
        <h3 className="text-lg font-semibold text-foreground">
          Ready to Detect PII
        </h3>
        <p className="text-muted-foreground text-center max-w-md">
          Click the button below to start detecting personally identifiable
          information in your uploaded documents.
        </p>
        <Button onClick={runPIIDetection} className="neumorphic-button">
          <Search size={16} className="mr-2" />
          Start PII Detection
        </Button>
      </motion.div>
    );
  }

  console.log("Rendering: Detection Results");

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
              {detectionStats
                ? `Found ${detectionStats.totalPII} PII items in ${
                    detectionStats.totalDocuments === 1
                      ? detectionStats.documentName
                      : `${detectionStats.totalDocuments} documents`
                  }`
                : "PII detection completed"}
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <Button
              onClick={runPIIDetection}
              className="neumorphic-button"
              size="sm"
            >
              <RefreshCw size={16} className="mr-2" />
              Re-detect
            </Button>
            <Button className="neumorphic-button" size="sm">
              <Eye size={16} className="mr-2" />
              View Documents
            </Button>
            {detectedPIIData && onDetectionComplete && (
              <Button
                onClick={() => onDetectionComplete(detectedPIIData)}
                className="neumorphic-button bg-primary text-primary-foreground hover:bg-primary/90"
                size="sm"
              >
                Proceed to Masking
                <ChevronRight size={16} className="ml-2" />
              </Button>
            )}
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center space-x-4">
          <div className="relative flex-1 max-w-md">
            <Search
              className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground"
              size={16}
            />
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
              {getAvailableTypes().map((type) => (
                <SelectItem key={type} value={type}>
                  {type}
                </SelectItem>
              ))}
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
                  Suggested Strategy
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
                      {detection.text}
                    </code>
                  </td>
                  <td className="px-6 py-4 text-sm text-muted-foreground">
                    {detection.location}
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`font-medium ${getConfidenceColor(
                        detection.confidence
                      )}`}
                    >
                      {(detection.confidence * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <Badge
                      className={`${getSeverityColor(
                        detection.severity
                      )} border`}
                    >
                      {detection.severity.toUpperCase()}
                    </Badge>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-muted-foreground">
                      {detection.suggested_strategy}
                    </span>
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

        {filteredDetections.length === 0 && piiDetections.length > 0 && (
          <div className="p-8 text-center">
            <AlertTriangle className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">
              No Results Found
            </h3>
            <p className="text-muted-foreground">
              No PII items match your current filters. Try adjusting your search
              criteria.
            </p>
          </div>
        )}

        {piiDetections.length === 0 && hasDetectionRun && (
          <div className="p-8 text-center">
            <AlertTriangle className="w-12 h-12 text-success mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">
              No PII Detected
            </h3>
            <p className="text-muted-foreground">
              Great! No personally identifiable information was found in your
              documents.
            </p>
          </div>
        )}
      </div>
    </motion.div>
  );
}
