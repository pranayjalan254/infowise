import { useState } from "react";
import { motion } from "framer-motion";
import {
  ChevronLeft,
  ChevronRight,
  CheckCircle,
  FileText,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DocumentUpload } from "@/components/ingestion/DocumentUpload";
import { WorkflowSteps } from "@/components/ingestion/WorkflowSteps";
import { DetectionStep } from "@/components/ingestion/DetectionStep";
import { PolicyAdvisorStep } from "@/components/ingestion/PolicyAdvisorStep";
import { MaskingStep } from "@/components/ingestion/MaskingStep";
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
  { id: "detection", name: "Detection", status: "pending" },
  { id: "policy", name: "Policy Advisor", status: "pending" },
  { id: "masking", name: "Masking", status: "pending" },
  { id: "qa", name: "Quality Assurance", status: "pending" },
];

export default function DocumentIngestion() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [hasStartedProcessing, setHasStartedProcessing] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<string[]>([]);
  const [workflowSteps, setWorkflowSteps] = useState(initialWorkflowSteps);
  const navigate = useNavigate();

  const handleUploadComplete = (files: UploadedFile[]) => {
    setUploadedFiles(files);
    setHasStartedProcessing(true);
    // Mark first step as active
    setWorkflowSteps((prev) =>
      prev.map((step, index) =>
        index === 0 ? { ...step, status: "active" } : step
      )
    );
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
      setCurrentStepIndex((prev) => prev - 1);
    }
  };

  const getCurrentStepContent = () => {
    const currentStep = workflowSteps[currentStepIndex];

    switch (currentStep.id) {
      case "detection":
        return <DetectionStep />;
      case "policy":
        return <PolicyAdvisorStep />;
      case "masking":
        return <MaskingStep />;
      case "qa":
        return <QAStep />;
      default:
        return <DetectionStep />;
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
          Document Ingestion
        </h1>
        <p className="text-muted-foreground">
          {!hasStartedProcessing
            ? "Upload documents to begin the privacy and compliance workflow"
            : "Process documents through the complete privacy and compliance workflow"}
        </p>
      </motion.div>

      {!hasStartedProcessing ? (
        /* Upload Phase */
        <DocumentUpload onUploadComplete={handleUploadComplete} />
      ) : (
        /* Workflow Phase */
        <>
          {/* Uploaded Files Summary */}
          <motion.div
            className="neumorphic-card p-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-foreground">
                Uploaded Documents ({uploadedFiles.length})
              </h3>
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate("/dashboard")}
                className="neumorphic-button"
              >
                <FileText size={16} className="mr-2" />
                View on Dashboard
                <ArrowRight size={14} className="ml-2" />
              </Button>
            </div>

            <div className="grid gap-3">
              {uploadedFiles.slice(0, 3).map((file) => (
                <div
                  key={file.id}
                  className="flex items-center justify-between p-3 neumorphic-flat rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <FileText className="w-5 h-5 text-blue-500" />
                    <div>
                      <div className="font-medium text-foreground text-sm">
                        {file.name}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </div>
                    </div>
                  </div>
                  <CheckCircle className="w-5 h-5 text-green-500" />
                </div>
              ))}

              {uploadedFiles.length > 3 && (
                <div className="text-center text-sm text-muted-foreground">
                  ... and {uploadedFiles.length - 3} more documents
                </div>
              )}
            </div>
          </motion.div>

          {/* Workflow Steps Navigation */}
          <WorkflowSteps
            steps={workflowSteps}
            currentStep={workflowSteps[currentStepIndex].id}
            currentStepIndex={currentStepIndex}
            totalSteps={workflowSteps.length}
          />

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
                    Next Step
                    <ChevronRight size={16} className="ml-2" />
                  </Button>
                )}
              </div>
            </div>
          </motion.div>

          {/* Processing Summary */}
          <motion.div
            className="neumorphic-card p-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.3 }}
          >
            <h3 className="text-lg font-semibold text-foreground mb-4">
              Processing Summary
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="neumorphic-flat p-4 rounded-xl text-center">
                <div className="text-2xl font-bold text-foreground mb-1">
                  {uploadedFiles.length}
                </div>
                <div className="text-sm text-muted-foreground">Documents</div>
              </div>

              <div className="neumorphic-flat p-4 rounded-xl text-center">
                <div className="text-2xl font-bold text-primary mb-1">
                  {currentStepIndex >= 0 ? "147" : "0"}
                </div>
                <div className="text-sm text-muted-foreground">
                  PII Detected
                </div>
              </div>

              <div className="neumorphic-flat p-4 rounded-xl text-center">
                <div className="text-2xl font-bold text-warning mb-1">
                  {currentStepIndex >= 1 ? "23" : "0"}
                </div>
                <div className="text-sm text-muted-foreground">Risk Items</div>
              </div>

              <div className="neumorphic-flat p-4 rounded-xl text-center">
                <div className="text-2xl font-bold text-success mb-1">
                  {currentStepIndex >= 2 ? "124" : "0"}
                </div>
                <div className="text-sm text-muted-foreground">
                  Items Masked
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </motion.div>
  );
}
