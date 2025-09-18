import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Brain, CheckCircle2, AlertCircle, Eye, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { simpleProcessingApi } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  progress: number;
  status: "uploading" | "completed" | "error";
}

interface SimpleDetectionStepProps {
  uploadedFiles: UploadedFile[];
  onDetectionComplete: (detectionResults: any) => void;
}

export function SimpleDetectionStep({
  uploadedFiles,
  onDetectionComplete,
}: SimpleDetectionStepProps) {
  const [isDetecting, setIsDetecting] = useState(false);
  const [detectionProgress, setDetectionProgress] = useState(0);
  const [detectionStatus, setDetectionStatus] = useState<string>("");
  const [detectionResults, setDetectionResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [pdfError, setPdfError] = useState(false);
  const { toast } = useToast();

  const handleStartDetection = async () => {
    if (uploadedFiles.length === 0) {
      toast({
        title: "No files uploaded",
        description: "Please upload a document first.",
        variant: "destructive",
      });
      return;
    }

    setIsDetecting(true);
    setDetectionProgress(0);
    setDetectionStatus("Initializing PII detection...");
    setError(null);

    try {
      const documentId = uploadedFiles[0].id; // Use first (and only) uploaded file

      setDetectionStatus("Analyzing document structure...");
      setDetectionProgress(20);

      // Small delay to show status update
      await new Promise((resolve) => setTimeout(resolve, 500));

      setDetectionStatus("Extracting text content...");
      setDetectionProgress(40);

      await new Promise((resolve) => setTimeout(resolve, 300));

      setDetectionStatus("Running PII detection models...");
      setDetectionProgress(60);

      // Generate PII configuration using the simple API
      console.log("Starting PII detection for document:", documentId);
      const response = await simpleProcessingApi.generateConfig(documentId);

      setDetectionStatus("Processing detection results...");
      setDetectionProgress(90);

      await new Promise((resolve) => setTimeout(resolve, 200));

      setDetectionProgress(100);
      setDetectionStatus("Detection completed successfully!");

      if (response.status === "success" && response.data) {
        console.log("PII detection completed:", response.data);

        // Transform the config data to match the expected format
        const transformedResults = {
          document_id: response.data.document_id,
          total_pii: response.data.total_pii,
          config_data: response.data.config_data.map(
            (item: any, index: number) => ({
              id: item.id || `pii_${index}`,
              type: item.type,
              text: item.text,
              confidence: 0.9, // Default confidence since simple detector doesn't provide it
              location: `Page ${item.page + 1}`, // Convert to 1-based display
              severity: getSeverityFromType(item.type),
              suggested_strategy: item.strategy,
              coordinates: item.coordinates,
            })
          ),
        };

        setDetectionResults(transformedResults);

        toast({
          title: "PII Detection Complete",
          description: `Found ${response.data.total_pii} PII entities in the document.`,
        });

        // Notify parent component
        onDetectionComplete(transformedResults);
      } else {
        throw new Error(response.error?.message || "Detection failed");
      }
    } catch (error) {
      console.error("Detection error:", error);
      setDetectionProgress(100);
      setDetectionStatus("Detection failed");
      setError(error instanceof Error ? error.message : "Detection failed");

      toast({
        title: "Detection Failed",
        description:
          error instanceof Error
            ? error.message
            : "An error occurred during PII detection.",
        variant: "destructive",
      });
    } finally {
      setIsDetecting(false);
    }
  };

  // Map PII types to severity levels
  const getSeverityFromType = (type: string): "low" | "medium" | "high" => {
    const highSeverityTypes = [
      "SSN",
      "CREDIT_CARD",
      "BANK_ACCOUNT",
      "AADHAAR",
      "PASSPORT",
    ];
    const mediumSeverityTypes = [
      "PHONE",
      "EMAIL",
      "DATE_OF_BIRTH",
      "DRIVER_LICENSE",
    ];

    if (highSeverityTypes.includes(type)) return "high";
    if (mediumSeverityTypes.includes(type)) return "medium";
    return "low";
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "high":
        return "destructive";
      case "medium":
        return "secondary";
      default:
        return "outline";
    }
  };

  const getTypeDisplayName = (type: string): string => {
    const typeMap: { [key: string]: string } = {
      PERSON: "Person Name",
      ORG: "Organization",
      LOC: "Location",
      EMAIL: "Email Address",
      PHONE: "Phone Number",
      SSN: "Social Security Number",
      CREDIT_CARD: "Credit Card",
      DATE_OF_BIRTH: "Date of Birth",
      ADDRESS: "Address",
      PASSPORT: "Passport Number",
      DRIVER_LICENSE: "Driver License",
      BANK_ACCOUNT: "Bank Account",
    };
    return typeMap[type] || type;
  };

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center space-y-4"
      >
        <div className="mx-auto w-16 h-16 bg-blue-100 dark:bg-blue-900/20 rounded-full flex items-center justify-center">
          <Brain className="w-8 h-8 text-blue-600 dark:text-blue-400" />
        </div>
        <h2 className="text-2xl font-semibold">PII Detection</h2>
        <p className="text-muted-foreground max-w-md mx-auto">
          We'll scan your document to identify personally identifiable
          information (PII) using advanced AI models.
        </p>
      </motion.div>

      {/* Document Info */}
      {uploadedFiles.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center space-x-4">
                <CheckCircle2 className="w-5 h-5 text-green-500" />
                <div>
                  <p className="font-medium">{uploadedFiles[0].name}</p>
                  <p className="text-sm text-muted-foreground">
                    Ready for PII detection
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* PDF Preview */}
      {uploadedFiles.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="space-y-4"
        >
          <div className="flex items-center justify-between">
            <h3 className="font-medium flex items-center">
              <Eye className="w-5 h-5 mr-2" />
              Document Preview
            </h3>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                if (uploadedFiles[0]) {
                  window.open(
                    simpleProcessingApi.getPreviewUrl(uploadedFiles[0].id),
                    "_blank"
                  );
                }
              }}
            >
              <Download className="w-4 h-4 mr-2" />
              Open PDF
            </Button>
          </div>
          <Card>
            <CardContent className="p-4">
              <div className="rounded-lg overflow-hidden bg-white">
                {!pdfError ? (
                  <iframe
                    src={simpleProcessingApi.getPreviewUrl(
                      uploadedFiles[0]?.id || ""
                    )}
                    className="w-full h-[500px] border-0"
                    title="Document Preview"
                    onError={() => setPdfError(true)}
                    onLoad={() => setPdfError(false)}
                  />
                ) : (
                  <div className="w-full h-[500px] flex flex-col items-center justify-center bg-gray-100 dark:bg-gray-700 rounded-lg">
                    <Brain className="w-16 h-16 text-gray-400 mb-4" />
                    <p className="text-gray-600 dark:text-gray-300 mb-2">
                      PDF preview not available
                    </p>
                    <p className="text-sm text-gray-500 mb-4">
                      The document is ready for PII detection but cannot be
                      previewed in the browser.
                    </p>
                    <Button
                      onClick={() => {
                        if (uploadedFiles[0]) {
                          window.open(
                            simpleProcessingApi.getPreviewUrl(
                              uploadedFiles[0].id
                            ),
                            "_blank"
                          );
                        }
                      }}
                    >
                      <Download className="w-4 h-4 mr-2" />
                      Open in New Tab
                    </Button>
                  </div>
                )}
              </div>
              <div className="mt-4 text-center">
                <p className="text-sm text-muted-foreground">
                  {uploadedFiles[0]?.name || "Document Preview"}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Ready for PII detection • PDF Document
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Detection Progress */}
      {isDetecting && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          <div className="text-center">
            <p className="font-medium">Analyzing document for PII...</p>
            <p className="text-sm text-muted-foreground">{detectionStatus}</p>
          </div>
          <Progress value={detectionProgress} className="w-full" />
          <p className="text-xs text-center text-muted-foreground">
            {detectionProgress}% complete
          </p>
        </motion.div>
      )}

      {/* Error Display */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center space-x-2 p-4 bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-lg"
        >
          <AlertCircle className="w-5 h-5 text-red-500" />
          <div>
            <p className="font-medium text-red-900 dark:text-red-100">
              Detection Failed
            </p>
            <p className="text-sm text-red-700 dark:text-red-200">{error}</p>
          </div>
        </motion.div>
      )}

      {/* Detection Results */}
      {detectionResults && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Detection Results</h3>
            <Badge variant="secondary">
              {detectionResults.total_pii} PII entities found
            </Badge>
          </div>

          <Card>
            <CardContent className="p-4 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {detectionResults.config_data.slice(0, 9).map((pii: any) => (
                  <div key={pii.id} className="p-3 border rounded-lg space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">
                        {getTypeDisplayName(pii.type)}
                      </span>
                      <Badge
                        variant={getSeverityColor(pii.severity) as any}
                        className="text-xs"
                      >
                        {pii.severity}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground truncate">
                      {pii.text}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {pii.location}
                    </p>
                  </div>
                ))}
              </div>

              {detectionResults.config_data.length > 9 && (
                <p className="text-sm text-muted-foreground text-center">
                  And {detectionResults.config_data.length - 9} more...
                </p>
              )}
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Action Buttons */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="flex justify-center pt-4"
      >
        {!detectionResults && !isDetecting && (
          <Button
            onClick={handleStartDetection}
            disabled={uploadedFiles.length === 0}
            className="px-8"
          >
            <Brain className="w-4 h-4 mr-2" />
            Start PII Detection
          </Button>
        )}

        {detectionResults && (
          <Button
            onClick={() => onDetectionComplete(detectionResults)}
            className="px-8"
          >
            Continue to Masking Configuration
          </Button>
        )}
      </motion.div>
    </div>
  );
}
