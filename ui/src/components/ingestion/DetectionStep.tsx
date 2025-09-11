import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Search,
  Filter,
  Eye,
  AlertTriangle,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
  const [detectionStats, setDetectionStats] = useState<{
    totalDocuments: number;
    totalPII: number;
    documentName?: string;
  } | null>(null);
  const { toast } = useToast();

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
        // Single document detection
        const response = await piiApi.detectPII(documentIds[0]);
        if (response.status === "success" && response.data) {
          setPiiDetections(response.data.pii_items);
          setDetectionStats({
            totalDocuments: 1,
            totalPII: response.data.total_pii_detected,
            documentName: response.data.document_name,
          });
          setHasDetectionRun(true);

          if (onDetectionComplete) {
            onDetectionComplete(response.data);
          }

          toast({
            title: "PII Detection Complete",
            description: `Found ${response.data.total_pii_detected} PII items in ${response.data.document_name}`,
          });
        }
      } else {
        // Batch detection for multiple documents
        const response = await piiApi.batchDetectPII(documentIds);
        if (response.status === "success" && response.data) {
          // Combine all PII items from all documents
          const allPiiItems: PIIItem[] = [];
          response.data.results.forEach((result) => {
            allPiiItems.push(...result.pii_items);
          });

          setPiiDetections(allPiiItems);
          setDetectionStats({
            totalDocuments: response.data.total_processed,
            totalPII: allPiiItems.length,
          });
          setHasDetectionRun(true);

          if (onDetectionComplete) {
            onDetectionComplete(response.data);
          }

          toast({
            title: "Batch PII Detection Complete",
            description: `Found ${allPiiItems.length} PII items across ${response.data.total_processed} documents`,
          });
        }
      }
    } catch (error) {
      console.error("PII detection failed:", error);
      toast({
        title: "Detection Failed",
        description:
          error instanceof Error ? error.message : "Failed to detect PII",
        variant: "destructive",
      });
    } finally {
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

  if (isDetecting) {
    return (
      <motion.div
        className="flex flex-col items-center justify-center py-12 space-y-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <h3 className="text-lg font-semibold text-foreground">
          Detecting PII...
        </h3>
        <p className="text-muted-foreground text-center max-w-md">
          Our AI agent is analyzing your{" "}
          {documentIds.length === 1
            ? "document"
            : `${documentIds.length} documents`}{" "}
          to identify personally identifiable information.
        </p>
      </motion.div>
    );
  }

  if (!hasDetectionRun) {
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
            <Button className="neumorphic-button">
              <Eye size={16} className="mr-2" />
              View Documents
            </Button>
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
