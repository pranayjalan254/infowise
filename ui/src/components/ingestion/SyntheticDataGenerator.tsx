import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Play,
  Download,
  FileText,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  Eye,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { documentsApi, syntheticDataApi } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

interface Document {
  id: string;
  name: string;
  size: number;
  type: string;
  mime_type: string;
  upload_date: string;
  status: string;
}

interface GenerationJob {
  job_id: string;
  document_name: string;
  num_datasets: number;
  status: string;
  progress: number;
  status_message: string;
  created_at: string;
  completed_at?: string;
  generated_datasets?: Array<{
    id: string;
    name: string;
    dataset_number: number;
    size: number;
    created_at: string;
  }>;
  error?: string;
}

interface SyntheticDataset {
  id: string;
  synthetic_name: string;
  original_name: string;
  dataset_number: number;
  size: number;
  created_at: string;
  job_id: string;
}

export default function SyntheticDataGenerator() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocument, setSelectedDocument] = useState("");
  const [numDatasets, setNumDatasets] = useState(1);
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentJob, setCurrentJob] = useState<GenerationJob | null>(null);
  const [generationJobs, setGenerationJobs] = useState<GenerationJob[]>([]);
  const [syntheticDatasets, setSyntheticDatasets] = useState<
    SyntheticDataset[]
  >([]);
  const [loading, setLoading] = useState(false);
  const [previewContent, setPreviewContent] = useState<string>("");
  const [previewDataset, setPreviewDataset] = useState<SyntheticDataset | null>(
    null
  );
  const { toast } = useToast();

  // Load initial data
  useEffect(() => {
    loadDocuments();
    loadGenerationJobs();
    loadSyntheticDatasets();
  }, []);

  // Poll for job updates when generating
  useEffect(() => {
    let interval: NodeJS.Timeout;

    if (isGenerating && currentJob) {
      interval = setInterval(async () => {
        try {
          const response = await syntheticDataApi.getGenerationStatus(
            currentJob.job_id
          );
          const updatedJob = response.data as GenerationJob;

          setCurrentJob(updatedJob);

          if (
            updatedJob.status === "completed" ||
            updatedJob.status === "failed"
          ) {
            setIsGenerating(false);
            loadGenerationJobs();
            loadSyntheticDatasets();

            if (updatedJob.status === "completed") {
              toast({
                title: "Generation Complete",
                description: `Successfully generated ${updatedJob.num_datasets} synthetic datasets`,
              });
            } else {
              toast({
                title: "Generation Failed",
                description:
                  updatedJob.error || "An error occurred during generation",
                variant: "destructive",
              });
            }
          }
        } catch (error) {
          console.error("Failed to poll job status:", error);
        }
      }, 2000); // Poll every 2 seconds
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isGenerating, currentJob, toast]);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      const response = await documentsApi.list();
      setDocuments(response.data.documents || []);
    } catch (error) {
      console.error("Failed to load documents:", error);
      toast({
        title: "Error",
        description: "Failed to load documents",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const loadGenerationJobs = async () => {
    try {
      const response = await syntheticDataApi.listJobs();
      setGenerationJobs(response.data.jobs || []);
    } catch (error) {
      console.error("Failed to load generation jobs:", error);
    }
  };

  const loadSyntheticDatasets = async () => {
    try {
      const response = await syntheticDataApi.listDatasets();
      setSyntheticDatasets(response.data.datasets || []);
    } catch (error) {
      console.error("Failed to load synthetic datasets:", error);
    }
  };

  const handleGenerateDatasets = async () => {
    if (!selectedDocument || numDatasets < 1 || numDatasets > 10) {
      toast({
        title: "Invalid Input",
        description: "Please select a document and choose 1-10 datasets",
        variant: "destructive",
      });
      return;
    }

    try {
      setIsGenerating(true);
      const response = await syntheticDataApi.startGeneration(
        selectedDocument,
        numDatasets
      );
      const responseData = response.data as {
        job_id: string;
        status: string;
        message: string;
      };

      setCurrentJob({
        job_id: responseData.job_id,
        document_name:
          documents.find((d) => d.id === selectedDocument)?.name || "",
        num_datasets: numDatasets,
        status: "started",
        progress: 0,
        status_message: "Initializing generation...",
        created_at: new Date().toISOString(),
      });

      toast({
        title: "Generation Started",
        description: `Started generating ${numDatasets} synthetic datasets`,
      });
    } catch (error: any) {
      setIsGenerating(false);
      toast({
        title: "Generation Failed",
        description: error.message || "Failed to start generation",
        variant: "destructive",
      });
    }
  };

  const handleDownloadDataset = async (dataset: SyntheticDataset) => {
    try {
      await syntheticDataApi.downloadDataset(
        dataset.id,
        dataset.synthetic_name
      );
      toast({
        title: "Download Started",
        description: `Downloading ${dataset.synthetic_name}`,
      });
    } catch (error: any) {
      toast({
        title: "Download Failed",
        description: error.message || "Failed to download dataset",
        variant: "destructive",
      });
    }
  };

  const handlePreviewDataset = async (dataset: SyntheticDataset) => {
    try {
      const response = await syntheticDataApi.previewDataset(dataset.id);
      setPreviewContent(response.data.content_preview);
      setPreviewDataset(dataset);
    } catch (error: any) {
      toast({
        title: "Preview Failed",
        description: error.message || "Failed to load preview",
        variant: "destructive",
      });
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-500" />;
      case "started":
      case "running":
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      default:
        return <Clock className="h-4 w-4 text-yellow-500" />;
    }
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case "completed":
        return "default";
      case "failed":
        return "destructive";
      case "started":
      case "running":
        return "secondary";
      default:
        return "outline";
    }
  };

  const getStatusDisplayText = (status: string) => {
    switch (status) {
      case "completed":
        return "Success";
      case "failed":
        return "Failed";
      case "started":
        return "In Progress";
      case "running":
        return "Running";
      default:
        return status;
    }
  };

  return (
    <div className="space-y-6">
      {/* Generation Form */}
      <Card className="neumorphic-card">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <FileText size={20} />
            <span>Generate Synthetic Data</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">
                Select Document
              </label>
              <Select
                value={selectedDocument}
                onValueChange={setSelectedDocument}
                disabled={isGenerating}
              >
                <SelectTrigger className="neumorphic-input">
                  <SelectValue placeholder="Choose a document" />
                </SelectTrigger>
                <SelectContent className="neumorphic-card">
                  {documents.map((doc) => (
                    <SelectItem key={doc.id} value={doc.id}>
                      {doc.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">
                Number of Datasets (1-10)
              </label>
              <Input
                type="number"
                min={1}
                max={10}
                value={numDatasets}
                onChange={(e) => setNumDatasets(parseInt(e.target.value) || 1)}
                className="neumorphic-input"
                disabled={isGenerating}
              />
            </div>
          </div>

          <Button
            onClick={handleGenerateDatasets}
            disabled={isGenerating || !selectedDocument}
            className="neumorphic-button w-full"
          >
            {isGenerating ? (
              <>
                <Loader2 size={16} className="mr-2 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Play size={16} className="mr-2" />
                Generate Synthetic Datasets
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Current Generation Progress */}
      {currentJob && isGenerating && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <Card className="neumorphic-card border-blue-200">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Loader2 size={20} className="animate-spin" />
                <span>Generation in Progress</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Document:</span>
                  <span className="font-medium">
                    {currentJob.document_name}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Datasets:</span>
                  <span className="font-medium">{currentJob.num_datasets}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Status:</span>
                  <span className="font-medium">
                    {currentJob.status_message}
                  </span>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Progress</span>
                  <span>{Math.round(currentJob.progress)}%</span>
                </div>
                <Progress value={currentJob.progress} className="w-full" />
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Generation History */}
      <Card className="neumorphic-card">
        <CardHeader>
          <CardTitle>Generation History</CardTitle>
        </CardHeader>
        <CardContent>
          {generationJobs.filter((job) => job.status === "completed").length ===
          0 ? (
            <div className="text-center py-8">
              <Clock size={48} className="mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">
                No completed generation jobs yet
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {generationJobs
                .filter((job) => job.status === "completed")
                .slice(0, 5)
                .map((job) => (
                  <motion.div
                    key={job.job_id}
                    className="neumorphic-pressed p-4 rounded-lg"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        {getStatusIcon(job.status)}
                        <div>
                          <p className="font-medium text-foreground">
                            {job.document_name}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {job.num_datasets} datasets generated •{" "}
                            {new Date(
                              job.completed_at || job.created_at
                            ).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Badge variant={getStatusBadgeVariant(job.status)}>
                          {getStatusDisplayText(job.status)}
                        </Badge>
                      </div>
                    </div>
                  </motion.div>
                ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Generated Datasets */}
      <Card className="neumorphic-card">
        <CardHeader>
          <CardTitle>Generated Datasets</CardTitle>
        </CardHeader>
        <CardContent>
          {syntheticDatasets.length === 0 ? (
            <div className="text-center py-8">
              <FileText
                size={48}
                className="mx-auto text-muted-foreground mb-4"
              />
              <p className="text-muted-foreground">
                No synthetic datasets generated yet
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {syntheticDatasets.map((dataset) => (
                <motion.div
                  key={dataset.id}
                  className="neumorphic-pressed p-4 rounded-lg"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <FileText size={20} className="text-primary" />
                      <div>
                        <p className="font-medium text-foreground">
                          {dataset.synthetic_name}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          From: {dataset.original_name} • Dataset #
                          {dataset.dataset_number}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {(dataset.size / 1024).toFixed(1)} KB •{" "}
                          {new Date(dataset.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Dialog>
                        <DialogTrigger asChild>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handlePreviewDataset(dataset)}
                            className="neumorphic-button"
                          >
                            <Eye size={16} className="mr-2" />
                            Preview
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-4xl max-h-[80vh]">
                          <DialogHeader>
                            <DialogTitle>
                              Preview: {previewDataset?.synthetic_name}
                            </DialogTitle>
                          </DialogHeader>
                          <ScrollArea className="h-96 w-full border rounded p-4">
                            <pre className="text-sm whitespace-pre-wrap">
                              {previewContent}
                            </pre>
                          </ScrollArea>
                        </DialogContent>
                      </Dialog>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDownloadDataset(dataset)}
                        className="neumorphic-button"
                      >
                        <Download size={16} className="mr-2" />
                        Download
                      </Button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
