import { useState } from "react";
import { motion } from "framer-motion";
import { SimpleDocumentUpload } from "@/components/ingestion/SimpleDocumentUpload";
import { SimpleDetectionStep } from "@/components/ingestion/SimpleDetectionStep";
import { SimpleMaskingStep } from "@/components/ingestion/SimpleMaskingStep";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle, Circle, Clock } from "lucide-react";

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
  icon: "upload" | "detection" | "masking";
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

export default function SimpleDocumentIngestion() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [currentPhase, setCurrentPhase] = useState<
    "upload" | "detection" | "masking"
  >("upload");
  const [steps, setSteps] = useState(workflowSteps);
  const [detectedPIIData, setDetectedPIIData] = useState<any>(null);
  const [maskingResults, setMaskingResults] = useState<any>(null);

  const handleUploadComplete = (files: UploadedFile[]) => {
    console.log("Upload completed:", files);
    setUploadedFiles(files);

    // Move to detection phase
    setCurrentPhase("detection");
    setSteps((prev) =>
      prev.map((step) => {
        if (step.id === "upload") return { ...step, status: "completed" };
        if (step.id === "detection") return { ...step, status: "active" };
        return step;
      })
    );
  };

  const handleDetectionComplete = (detectionResults: any) => {
    console.log("Detection completed:", detectionResults);
    setDetectedPIIData(detectionResults);

    // Move to masking phase
    setCurrentPhase("masking");
    setSteps((prev) =>
      prev.map((step) => {
        if (step.id === "detection") return { ...step, status: "completed" };
        if (step.id === "masking") return { ...step, status: "active" };
        return step;
      })
    );
  };

  const handleMaskingComplete = (results: any) => {
    console.log("Masking completed:", results);
    setMaskingResults(results);

    // Mark masking as completed
    setSteps((prev) =>
      prev.map((step) => {
        if (step.id === "masking") return { ...step, status: "completed" };
        return step;
      })
    );
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
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-8"
      >
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-3xl font-bold">Document PII Processing</h1>
          <p className="text-muted-foreground">
            Upload your document, detect PII, configure masking strategies, and
            download the protected version.
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
              <SimpleDocumentUpload onUploadComplete={handleUploadComplete} />
            )}

            {currentPhase === "detection" && (
              <SimpleDetectionStep
                uploadedFiles={uploadedFiles}
                onDetectionComplete={handleDetectionComplete}
              />
            )}

            {currentPhase === "masking" && detectedPIIData && (
              <SimpleMaskingStep
                detectedPIIData={detectedPIIData}
                onMaskingComplete={handleMaskingComplete}
              />
            )}
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
