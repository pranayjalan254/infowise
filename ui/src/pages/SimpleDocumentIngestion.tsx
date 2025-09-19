import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { SimpleDocumentUpload } from "@/components/ingestion/SimpleDocumentUpload";
import { SimpleMaskingStep } from "@/components/ingestion/SimpleMaskingStep";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { CheckCircle, Circle, Clock, FileText, Wand2 } from "lucide-react";
import { cn } from "@/lib/utils";
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

interface FileProcessingState {
  fileId: string;
  fileName: string;
  currentStep: "upload" | "detection" | "masking";
  detectionStatus: "pending" | "processing" | "completed" | "error";
  maskingStatus: "pending" | "processing" | "completed" | "error";
  detectedPIIData: any;
  maskingResults: any;
  error?: string;
  // Enhanced progress tracking
  estimatedPages?: number;
  currentPage?: number;
  detectionProgress?: number;
  processingMessages?: string[];
  totalPiiFound?: number;
}

interface WorkflowStep {
  id: string;
  name: string;
  status: "pending" | "active" | "completed";
  icon: "upload" | "review" | "detection" | "masking";
}

const workflowSteps: WorkflowStep[] = [
  { id: "upload", name: "Document Upload", status: "active", icon: "upload" },
  {
    id: "detection",
    name: "PII Detection",
    status: "pending",
    icon: "detection",
  },
  { id: "masking", name: "PII Masking", status: "pending", icon: "masking" },
];

// Utility function to determine severity from PII type
const getSeverityFromType = (type: string): "low" | "medium" | "high" => {
  const highRiskTypes = ["ssn", "credit_card", "passport", "driver_license"];
  const mediumRiskTypes = ["phone", "email", "address", "date_of_birth"];

  const lowercaseType = type.toLowerCase();

  if (highRiskTypes.some((riskType) => lowercaseType.includes(riskType))) {
    return "high";
  } else if (
    mediumRiskTypes.some((riskType) => lowercaseType.includes(riskType))
  ) {
    return "medium";
  }
  return "low";
};

export default function SimpleDocumentIngestion() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [currentPhase, setCurrentPhase] = useState<
    "upload" | "detection" | "masking"
  >("upload");
  const [steps, setSteps] = useState(workflowSteps);
  const [fileProcessingStates, setFileProcessingStates] = useState<
    FileProcessingState[]
  >([]);
  const [activeFileTab, setActiveFileTab] = useState<string>("");
  const [isDetectionRunning, setIsDetectionRunning] = useState(false);
  const [detectionStartTime, setDetectionStartTime] = useState<Date | null>(
    null
  );
  const [overallDetectionProgress, setOverallDetectionProgress] = useState(0);
  const [detectionMessage, setDetectionMessage] = useState<string>("");
  const [isMaskingRunning, setIsMaskingRunning] = useState(false);
  const [maskingMessage, setMaskingMessage] = useState<string>("");
  const { toast } = useToast();

  const handleUploadComplete = async (files: UploadedFile[]) => {
    console.log("Upload completed:", files);
    setUploadedFiles(files);

    // Initialize processing states for each file
    const initialProcessingStates: FileProcessingState[] = files.map(
      (file) => ({
        fileId: file.id,
        fileName: file.name,
        currentStep: "upload" as const,
        detectionStatus: "pending" as const,
        maskingStatus: "pending" as const,
        detectedPIIData: null,
        maskingResults: null,
      })
    );

    setFileProcessingStates(initialProcessingStates);

    // Set the first file as active tab
    if (files.length > 0) {
      setActiveFileTab(files[0].id);
    }

    // Stay in upload phase and let user review files before starting detection
    toast({
      title: "Upload Complete",
      description: `Successfully uploaded ${files.length} file(s). Review your documents and click "Start PII Detection" when ready.`,
    });
  };

  const handleStartDetection = async () => {
    try {
      setIsDetectionRunning(true);
      setDetectionStartTime(new Date());
      setOverallDetectionProgress(0);
      setDetectionMessage("Initializing PII detection...");

      // Update steps to show detection is active
      setSteps((prev) =>
        prev.map((step) =>
          step.id === "detection"
            ? { ...step, status: "active" }
            : step.id === "upload"
            ? { ...step, status: "completed" }
            : step
        )
      );

      setCurrentPhase("detection");

      // Update all file processing states to show detection is starting
      setFileProcessingStates((prev) =>
        prev.map((state) => ({
          ...state,
          detectionStatus: "processing",
          currentStep: "detection",
        }))
      );

      // Simple progress simulation - slow progress that doesn't reach 100%
      const progressInterval = setInterval(() => {
        setOverallDetectionProgress((prev) => {
          if (prev < 85) {
            // Slow progress in the beginning
            if (prev < 20) {
              setDetectionMessage("Analyzing document structure...");
              return prev + Math.random() * 2 + 0.5;
            }
            // Medium progress in the middle
            else if (prev < 50) {
              setDetectionMessage("Extracting text content...");
              return prev + Math.random() * 1.5 + 0.3;
            }
            // Very slow progress towards the end
            else {
              setDetectionMessage("Running PII detection models...");
              return prev + Math.random() * 0.5 + 0.1;
            }
          }
          return prev; // Stay at ~85% until API completes
        });
      }, 800);

      // Wait a bit for UI to show progress, then make the API call
      await new Promise((resolve) => setTimeout(resolve, 2000));

      try {
        const documentIds = uploadedFiles.map((file) => file.id);
        const response = await simpleProcessingApi.generateConfigBulk(
          documentIds
        );

        clearInterval(progressInterval);

        // Complete the progress
        setOverallDetectionProgress(100);
        setDetectionMessage("Detection completed successfully!");

        if (response.status === "success" && response.data) {
          const { successful_configs, failed_configs } = response.data;

          // Update processing states with detection results
          setFileProcessingStates((prev) =>
            prev.map((state) => {
              const successConfig = successful_configs.find(
                (config: any) => config.document_id === state.fileId
              );
              const failedConfig = failed_configs.find(
                (config: any) => config.document_id === state.fileId
              );

              if (successConfig) {
                return {
                  ...state,
                  detectionStatus: "completed" as const,
                  detectedPIIData: {
                    document_id: successConfig.document_id,
                    total_pii: successConfig.total_pii,
                    config_data: successConfig.config_data.map(
                      (item: any, index: number) => ({
                        id: item.id || `pii_${index}`,
                        type: item.type,
                        text: item.text,
                        confidence: 0.9,
                        location: `Page ${item.page + 1}`,
                        severity: getSeverityFromType(item.type),
                        suggested_strategy: item.strategy,
                        coordinates: item.coordinates,
                      })
                    ),
                  },
                  currentStep: "masking" as const,
                };
              } else if (failedConfig) {
                return {
                  ...state,
                  detectionStatus: "error" as const,
                  error: failedConfig.error,
                };
              }
              return state;
            })
          );

          // Move to masking phase
          setCurrentPhase("masking");
          setSteps((prev) =>
            prev.map((step) => {
              if (step.id === "detection")
                return { ...step, status: "completed" };
              if (step.id === "masking") return { ...step, status: "active" };
              return step;
            })
          );

          toast({
            title: "PII Detection Complete",
            description: `Detected PII in ${successful_configs.length} of ${uploadedFiles.length} files.`,
          });
        }
      } catch (apiError) {
        clearInterval(progressInterval);
        console.error("API Error during detection:", apiError);

        setOverallDetectionProgress(100);
        setDetectionMessage("Detection failed");

        setFileProcessingStates((prev) =>
          prev.map((state) => ({
            ...state,
            detectionStatus: "error",
            error: "Failed to detect PII. Please try again.",
          }))
        );

        toast({
          title: "Detection Failed",
          description:
            "Failed to detect PII in the documents. Please try again.",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Detection error:", error);
      setOverallDetectionProgress(100);
      setDetectionMessage("Detection failed");

      setFileProcessingStates((prev) =>
        prev.map((state) => ({
          ...state,
          detectionStatus: "error",
          error: "An unexpected error occurred during detection.",
        }))
      );

      toast({
        title: "Error",
        description: "An unexpected error occurred during PII detection.",
        variant: "destructive",
      });
    } finally {
      setIsDetectionRunning(false);
    }
  };

  const handleMaskingComplete = (fileId: string, results: any) => {
    console.log("Individual masking completed for file:", fileId, results);

    setFileProcessingStates((prev) =>
      prev.map((state) =>
        state.fileId === fileId
          ? { ...state, maskingStatus: "completed", maskingResults: results }
          : state
      )
    );

    // Check if all files have completed masking
    const updatedStates = fileProcessingStates.map((state) =>
      state.fileId === fileId
        ? { ...state, maskingStatus: "completed" as const }
        : state
    );

    const allMaskingComplete = updatedStates.every(
      (state) => state.maskingStatus === "completed"
    );

    if (allMaskingComplete) {
      // Mark masking as completed
      setSteps((prev) =>
        prev.map((step) => {
          if (step.id === "masking") return { ...step, status: "completed" };
          return step;
        })
      );
    }
  };

  const handleBulkMasking = async () => {
    try {
      setIsMaskingRunning(true);
      setMaskingMessage("Initializing masking process...");

      // Get all document IDs that have completed detection
      const documentsToMask = fileProcessingStates
        .filter(
          (state) =>
            state.detectionStatus === "completed" && state.detectedPIIData
        )
        .map((state) => state.fileId);

      if (documentsToMask.length === 0) {
        toast({
          title: "No files ready",
          description: "No files have completed PII detection yet.",
          variant: "destructive",
        });
        return;
      }

      setMaskingMessage("Preparing documents for masking...");

      // Set all files to processing state
      setFileProcessingStates((prev) =>
        prev.map((state) =>
          documentsToMask.includes(state.fileId)
            ? { ...state, maskingStatus: "processing" as const }
            : state
        )
      );

      // Wait a moment to show the loading state
      await new Promise((resolve) => setTimeout(resolve, 1000));

      setMaskingMessage("Applying PII masking to all documents...");

      console.log("Starting bulk masking for documents:", documentsToMask);
      const response = await simpleProcessingApi.applyMaskingBulk(
        documentsToMask
      );

      setMaskingMessage("Processing masking results...");

      if (response.status === "success" && response.data) {
        const { successful_maskings, failed_maskings } = response.data;

        // Update processing states with masking results
        setFileProcessingStates((prev) =>
          prev.map((state) => {
            const successMasking = successful_maskings.find(
              (masking: any) => masking.document_id === state.fileId
            );
            const failedMasking = failed_maskings.find(
              (masking: any) => masking.document_id === state.fileId
            );

            if (successMasking) {
              return {
                ...state,
                maskingStatus: "completed" as const,
                maskingResults: successMasking,
              };
            } else if (failedMasking) {
              return {
                ...state,
                maskingStatus: "error" as const,
                error: failedMasking.error,
              };
            }
            return state;
          })
        );

        // Mark masking as completed
        setSteps((prev) =>
          prev.map((step) => {
            if (step.id === "masking") return { ...step, status: "completed" };
            return step;
          })
        );

        setMaskingMessage("Masking completed successfully!");

        toast({
          title: "Masking Complete",
          description: `Successfully masked ${successful_maskings.length} of ${documentsToMask.length} files.`,
        });
      }
    } catch (error) {
      console.error("Bulk masking error:", error);
      setMaskingMessage("Masking failed");

      // Update all processing files to error state
      setFileProcessingStates((prev) =>
        prev.map((state) =>
          state.maskingStatus === "processing"
            ? {
                ...state,
                maskingStatus: "error" as const,
                error:
                  error instanceof Error ? error.message : "Masking failed",
              }
            : state
        )
      );

      toast({
        title: "Masking Failed",
        description:
          error instanceof Error ? error.message : "Failed to mask documents",
        variant: "destructive",
      });
    } finally {
      setIsMaskingRunning(false);
    }
  };

  const getFileProcessingState = (
    fileId: string
  ): FileProcessingState | undefined => {
    return fileProcessingStates.find((state) => state.fileId === fileId);
  };

  const getStepIcon = (step: WorkflowStep) => {
    const iconClass = "w-5 h-5";

    if (step.status === "completed") {
      return <CheckCircle className={`${iconClass} text-green-500`} />;
    } else if (step.status === "active") {
      return <Clock className={`${iconClass} text-blue-500`} />;
    } else {
      return <Circle className={`${iconClass} text-gray-400`} />;
    }
  };

  const getStepStatus = (step: WorkflowStep) => {
    switch (step.status) {
      case "completed":
        return (
          <Badge variant="default" className="bg-green-100 text-green-800">
            Completed
          </Badge>
        );
      case "active":
        return (
          <Badge variant="default" className="bg-blue-100 text-blue-800">
            Active
          </Badge>
        );
      default:
        return <Badge variant="outline">Pending</Badge>;
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-8"
      >
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-3xl font-bold">Document PII Processing</h1>
          <p className="text-muted-foreground">
            Upload your documents, detect PII, configure masking strategies, and
            download the protected versions.
          </p>
        </div>

        {/* Progress Steps */}
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              {steps.map((step, index) => (
                <div key={step.id} className="flex items-center">
                  <div className="flex items-center space-x-3">
                    {getStepIcon(step)}
                    <div className="text-center">
                      <p className="font-medium">{step.name}</p>
                      {getStepStatus(step)}
                    </div>
                  </div>
                  {index < steps.length - 1 && (
                    <div className="hidden sm:block w-12 h-px bg-gray-300 mx-8" />
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Current Phase Content */}
        <Card>
          <CardContent className="p-8">
            {currentPhase === "upload" && (
              <SimpleDocumentUpload
                onUploadComplete={handleUploadComplete}
                onStartDetection={handleStartDetection}
                uploadedFiles={uploadedFiles}
              />
            )}

            {(currentPhase === "detection" || currentPhase === "masking") &&
              uploadedFiles.length > 0 && (
                <div className="space-y-6">
                  {/* Overall Status Display */}
                  <div className="flex justify-between items-center">
                    <div className="text-sm text-muted-foreground">
                      Processing {uploadedFiles.length} files
                    </div>
                    {currentPhase === "masking" && (
                      <Button
                        onClick={handleBulkMasking}
                        disabled={isMaskingRunning}
                        className="flex items-center space-x-2"
                      >
                        {isMaskingRunning ? (
                          <>
                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            <span>Applying Masking...</span>
                          </>
                        ) : (
                          <>
                            <Wand2 className="w-4 h-4" />
                            <span>Apply Masking to All Files</span>
                          </>
                        )}
                      </Button>
                    )}
                  </div>

                  {/* Global Masking Loading State */}
                  {isMaskingRunning && (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="text-center space-y-4 p-6 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 border border-purple-200 dark:border-purple-800 rounded-lg"
                    >
                      <div className="mx-auto w-16 h-16 bg-purple-100 dark:bg-purple-900/20 rounded-full flex items-center justify-center">
                        <Wand2 className="w-8 h-8 text-purple-600 dark:text-purple-400" />
                      </div>
                      <h3 className="text-lg font-medium text-purple-900 dark:text-purple-100">
                        Applying PII Masking
                      </h3>
                      <p className="text-purple-700 dark:text-purple-300 max-w-md mx-auto">
                        {maskingMessage}
                      </p>
                      <div className="animate-pulse flex justify-center">
                        <div className="flex space-x-1">
                          <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce"></div>
                          <div
                            className="w-2 h-2 bg-purple-500 rounded-full animate-bounce"
                            style={{ animationDelay: "0.1s" }}
                          ></div>
                          <div
                            className="w-2 h-2 bg-purple-500 rounded-full animate-bounce"
                            style={{ animationDelay: "0.2s" }}
                          ></div>
                        </div>
                      </div>
                      <div className="text-sm text-purple-600 dark:text-purple-400">
                        Processing {uploadedFiles.length} documents...
                      </div>
                    </motion.div>
                  )}

                  {/* File Tabs */}
                  <Tabs
                    value={activeFileTab}
                    onValueChange={setActiveFileTab}
                    className="w-full"
                  >
                    <TabsList
                      className="grid w-full"
                      style={{
                        gridTemplateColumns: `repeat(${uploadedFiles.length}, 1fr)`,
                      }}
                    >
                      {uploadedFiles.map((file) => {
                        const processingState = getFileProcessingState(file.id);
                        return (
                          <TabsTrigger
                            key={file.id}
                            value={file.id}
                            className="flex items-center space-x-2"
                          >
                            <FileText className="w-4 h-4" />
                            <span className="truncate max-w-[120px]">
                              {file.name}
                            </span>
                            {processingState && (
                              <div className="flex space-x-1">
                                <div
                                  className={cn(
                                    "w-2 h-2 rounded-full",
                                    processingState.detectionStatus ===
                                      "completed"
                                      ? "bg-green-500"
                                      : processingState.detectionStatus ===
                                        "processing"
                                      ? "bg-blue-500 animate-pulse"
                                      : processingState.detectionStatus ===
                                        "error"
                                      ? "bg-red-500"
                                      : "bg-gray-300"
                                  )}
                                />
                                <div
                                  className={cn(
                                    "w-2 h-2 rounded-full",
                                    processingState.maskingStatus ===
                                      "completed"
                                      ? "bg-green-500"
                                      : processingState.maskingStatus ===
                                        "processing"
                                      ? "bg-blue-500 animate-pulse"
                                      : processingState.maskingStatus ===
                                        "error"
                                      ? "bg-red-500"
                                      : "bg-gray-300"
                                  )}
                                />
                              </div>
                            )}
                          </TabsTrigger>
                        );
                      })}
                    </TabsList>

                    {uploadedFiles.map((file) => {
                      const processingState = getFileProcessingState(file.id);
                      return (
                        <TabsContent
                          key={file.id}
                          value={file.id}
                          className="space-y-6"
                        >
                          {currentPhase === "detection" && (
                            <div className="text-center space-y-6">
                              <h3 className="text-lg font-medium">
                                PII Detection
                              </h3>
                              <p className="text-muted-foreground">
                                {processingState?.detectionStatus ===
                                  "processing" && detectionMessage}
                                {processingState?.detectionStatus ===
                                  "completed" &&
                                  `Found ${
                                    processingState.detectedPIIData
                                      ?.total_pii || 0
                                  } PII entities`}
                                {processingState?.detectionStatus === "error" &&
                                  "Detection failed"}
                              </p>
                              {processingState?.detectionStatus ===
                                "processing" && (
                                <div className="space-y-4">
                                  <Progress
                                    value={overallDetectionProgress}
                                    className="w-full max-w-md mx-auto"
                                  />
                                  <div className="text-sm text-muted-foreground">
                                    {Math.round(overallDetectionProgress)}%
                                    complete
                                  </div>
                                  <div className="animate-pulse flex justify-center">
                                    <div className="flex space-x-1">
                                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
                                      <div
                                        className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"
                                        style={{ animationDelay: "0.1s" }}
                                      ></div>
                                      <div
                                        className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"
                                        style={{ animationDelay: "0.2s" }}
                                      ></div>
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          )}

                          {currentPhase === "masking" &&
                            processingState?.detectedPIIData && (
                              <SimpleMaskingStep
                                detectedPIIData={
                                  processingState.detectedPIIData
                                }
                                onMaskingComplete={(results) =>
                                  handleMaskingComplete(file.id, results)
                                }
                                showApplyButton={false}
                                maskingResults={processingState.maskingResults}
                              />
                            )}

                          {/* Processing Status for Current File */}
                          {processingState && (
                            <div className="text-center space-y-2">
                              <div className="flex justify-center space-x-4 text-sm text-muted-foreground">
                                <div className="flex items-center space-x-2">
                                  <div
                                    className={cn(
                                      "w-3 h-3 rounded-full",
                                      processingState.detectionStatus ===
                                        "completed"
                                        ? "bg-green-500"
                                        : processingState.detectionStatus ===
                                          "processing"
                                        ? "bg-blue-500 animate-pulse"
                                        : processingState.detectionStatus ===
                                          "error"
                                        ? "bg-red-500"
                                        : "bg-gray-300"
                                    )}
                                  />
                                  <span>
                                    Detection: {processingState.detectionStatus}
                                  </span>
                                </div>
                                <div className="flex items-center space-x-2">
                                  <div
                                    className={cn(
                                      "w-3 h-3 rounded-full",
                                      processingState.maskingStatus ===
                                        "completed"
                                        ? "bg-green-500"
                                        : processingState.maskingStatus ===
                                          "processing"
                                        ? "bg-blue-500 animate-pulse"
                                        : processingState.maskingStatus ===
                                          "error"
                                        ? "bg-red-500"
                                        : "bg-gray-300"
                                    )}
                                  />
                                  <span>
                                    Masking: {processingState.maskingStatus}
                                  </span>
                                </div>
                              </div>
                              {processingState.error && (
                                <p className="text-red-500 text-sm">
                                  {processingState.error}
                                </p>
                              )}
                            </div>
                          )}
                        </TabsContent>
                      );
                    })}
                  </Tabs>
                </div>
              )}
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
