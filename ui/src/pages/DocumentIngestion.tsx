import { useState } from "react";
import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DocumentUpload } from "@/components/ingestion/DocumentUpload";
import { DocumentReview } from "@/components/ingestion/DocumentReview";
import { DetectionStep } from "@/components/ingestion/DetectionStep";
import { MaskingStep } from "@/components/ingestion/MaskingStep";
import { MaskingResultsStep } from "@/components/ingestion/MaskingResultsStep";
import { QAStep } from "@/components/ingestion/QAStep";
import { useNavigate } from "react-router-dom";

interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  progress: number;
  status: "uploading" | "completed" | "error";
}

interface WorkflowStep {
  id: string;
  name: string;
  status: "pending" | "active" | "completed";
}

const initialWorkflowSteps: WorkflowStep[] = [
  { id: "detection", name: "PII Detection", status: "pending" },
  { id: "masking", name: "Masking", status: "pending" },
  { id: "results", name: "Results", status: "pending" },
];

export default function DocumentIngestion() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [uploadedDocumentIds, setUploadedDocumentIds] = useState<string[]>([]);
  const [currentPhase, setCurrentPhase] = useState<
    "upload" | "review" | "detection" | "masking" | "results"
  >("upload");
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<string[]>([]);
  const [workflowSteps, setWorkflowSteps] = useState(initialWorkflowSteps);
  const [detectedPIIData, setDetectedPIIData] = useState<any>(null);
  const navigate = useNavigate();

  const handleUploadComplete = (files: UploadedFile[]) => {
    setUploadedFiles(files);
    // Extract document IDs from uploaded files
    const documentIds = files.map((file) => file.id);
    setUploadedDocumentIds(documentIds);
    setCurrentPhase("review");
  };

  const handleDetectPII = () => {
    setCurrentPhase("detection");
    // Mark first step as active
    setWorkflowSteps((prev) =>
      prev.map((step, index) =>
        index === 0 ? { ...step, status: "active" } : step
      )
    );
  };

  const handleDetectionComplete = (detectionResults: any) => {
    setDetectedPIIData(detectionResults);

    // Mark detection step as completed and next as active
    const currentStepId = workflowSteps[currentStepIndex].id;
    setCompletedSteps((prev) => [...prev, currentStepId]);

    setWorkflowSteps((prev) =>
      prev.map((step, index) => {
        if (index === currentStepIndex) {
          return { ...step, status: "completed" };
        } else if (index === currentStepIndex + 1) {
          return { ...step, status: "active" };
        }
        return step;
      })
    );

    // Move to next step
    setCurrentStepIndex((prev) => prev + 1);
    setCurrentPhase("masking");
  };

  const handleMaskPII = () => {
    // Mark current step as completed and next as active
    const currentStepId = workflowSteps[currentStepIndex].id;
    setCompletedSteps((prev) => [...prev, currentStepId]);

    setWorkflowSteps((prev) =>
      prev.map((step, index) => {
        if (index === currentStepIndex) {
          return { ...step, status: "completed" };
        } else if (index === currentStepIndex + 1) {
          return { ...step, status: "active" };
        }
        return step;
      })
    );

    // Move to next step
    setCurrentStepIndex((prev) => prev + 1);
    setCurrentPhase("results");
  };

  const handleWorkflowComplete = () => {
    // Navigate to dashboard or another page
    navigate("/dashboard");
  };

  const handleNextStep = () => {
    if (currentStepIndex < workflowSteps.length - 1) {
      // Mark current step as completed and next as active
      const currentStepId = workflowSteps[currentStepIndex].id;
      setCompletedSteps((prev) => [...prev, currentStepId]);

      setWorkflowSteps((prev) =>
        prev.map((step, index) => {
          if (index === currentStepIndex) {
            return { ...step, status: "completed" };
          } else if (index === currentStepIndex + 1) {
            return { ...step, status: "active" };
          }
          return step;
        })
      );

      // Move to next step
      setCurrentStepIndex((prev) => prev + 1);
    }
  };

  const handlePreviousStep = () => {
    if (currentStepIndex > 0) {
      setWorkflowSteps((prev) =>
        prev.map((step, index) => {
          if (index === currentStepIndex) {
            return { ...step, status: "pending" };
          } else if (index === currentStepIndex - 1) {
            return { ...step, status: "active" };
          }
          return step;
        })
      );

      // Move to previous step
    }
  };

  const getCurrentStepContent = () => {
    const currentStep = workflowSteps[currentStepIndex];

    switch (currentStep.id) {
      case "detection":
        return (
          <DetectionStep
            documentIds={uploadedDocumentIds}
            onDetectionComplete={handleDetectionComplete}
          />
        );
      case "masking":
        return (
          <MaskingStep
            onMaskPII={handleMaskPII}
            detectedPIIData={detectedPIIData}
          />
        );
      case "results":
        return (
          <MaskingResultsStep
            onComplete={handleWorkflowComplete}
            detectedPIIData={detectedPIIData}
            documentId={uploadedDocumentIds[0]} // Pass the current document ID
          />
        );
      default:
        return (
          <DetectionStep
            documentIds={uploadedDocumentIds}
            onDetectionComplete={handleDetectionComplete}
          />
        );
    }
  };

  const isLastStep = currentStepIndex === workflowSteps.length - 1;
  const isFirstStep = currentStepIndex === 0;

  return (
    <motion.div
      className="space-y-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <h1 className="text-3xl font-bold text-display text-foreground mb-2">
          {currentPhase === "upload"
            ? "Document Ingestion"
            : currentPhase === "review"
            ? ""
            : ""}
        </h1>
        <p className="text-muted-foreground">
          {currentPhase === "upload"
            ? "Upload documents to begin the privacy and compliance workflow"
            : currentPhase === "review"
            ? ""
            : ""}
        </p>
      </motion.div>

      {currentPhase === "upload" ? (
        /* Upload Phase */
        <DocumentUpload onUploadComplete={handleUploadComplete} />
      ) : currentPhase === "review" ? (
        /* Document Review Phase */
        <DocumentReview
          uploadedDocumentIds={uploadedDocumentIds}
          onDetectPII={handleDetectPII}
        />
      ) : currentPhase === "detection" ? (
        /* PII Detection Phase */
        <DetectionStep
          documentIds={uploadedDocumentIds}
          onDetectionComplete={handleDetectionComplete}
        />
      ) : (
        <>
          {/* Step Content */}
          <motion.div
            key={currentStepIndex}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3 }}
          >
            {getCurrentStepContent()}
          </motion.div>

          {/* Navigation Controls */}
          <motion.div
            className="neumorphic-card p-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.2 }}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <Button
                  variant="outline"
                  onClick={handlePreviousStep}
                  disabled={isFirstStep}
                  className="neumorphic-button"
                >
                  <ChevronLeft size={16} className="mr-2" />
                  Previous Step
                </Button>

                <div className="text-sm text-muted-foreground">
                  {uploadedFiles.length} document
                  {uploadedFiles.length !== 1 ? "s" : ""} uploaded
                </div>
              </div>

              <div className="flex items-center space-x-4">
                <div className="text-sm text-muted-foreground">
                  {completedSteps.length} of {workflowSteps.length} steps
                  completed
                </div>

                {isLastStep ? (
                  <Button className="neumorphic-button">
                    <CheckCircle size={16} className="mr-2" />
                    Complete Processing
                  </Button>
                ) : (
                  <Button
                    onClick={handleNextStep}
                    className="neumorphic-button"
                  >
                    Next
                    <ChevronRight size={16} className="ml-2" />
                  </Button>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </motion.div>
  );
}
