import { useState } from "react";
import { motion } from "framer-motion";
import { DocumentUpload } from "@/components/ingestion/DocumentUpload";
import { DocumentReview } from "@/components/ingestion/DocumentReview";
import { DetectionStep } from "@/components/ingestion/DetectionStep";
import { MaskingStep } from "@/components/ingestion/MaskingStep";
import { MaskingResultsStep } from "@/components/ingestion/MaskingResultsStep";
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

  // Debug logging
  console.log("DocumentIngestion state:", {
    currentPhase,
    currentStepIndex,
    workflowSteps,
    completedSteps,
    detectedPIIData: detectedPIIData ? "exists" : "null",
  });

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
    console.log("handleDetectionComplete called with:", detectionResults);
    setDetectedPIIData(detectionResults);

    // Mark detection step as completed and next as active
    const currentStepId = workflowSteps[currentStepIndex].id;
    console.log(
      "Current step ID:",
      currentStepId,
      "Current step index:",
      currentStepIndex
    );

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

    // Move to next step - this is the key fix
    const nextStepIndex = currentStepIndex + 1;
    setCurrentStepIndex(nextStepIndex);
    setCurrentPhase("masking");

    console.log("Set current phase to masking, step index to:", nextStepIndex);
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
            documentId={uploadedDocumentIds[0]}
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
        </>
      )}
    </motion.div>
  );
}
