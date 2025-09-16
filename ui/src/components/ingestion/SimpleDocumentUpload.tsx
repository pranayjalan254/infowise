import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Upload } from "lucide-react";
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

interface SimpleDocumentUploadProps {
  onUploadComplete: (files: UploadedFile[]) => void;
}

export function SimpleDocumentUpload({
  onUploadComplete,
}: SimpleDocumentUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const { toast } = useToast();

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const processFiles = async (files: FileList | File[]) => {
    setIsUploading(true);

    try {
      const filesArray = Array.from(files);

      // Only support single document for simple processing
      if (filesArray.length > 1) {
        toast({
          title: "Single file only",
          description: "Please upload one document at a time.",
          variant: "destructive",
        });
        setIsUploading(false);
        return;
      }

      const file = filesArray[0];

      // Check supported file types
      const supportedTypes = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
      ];

      if (!supportedTypes.includes(file.type)) {
        toast({
          title: "Invalid file type",
          description:
            "Only PDF, Word (.docx), and text (.txt) files are supported.",
          variant: "destructive",
        });
        setIsUploading(false);
        return;
      }

      // Create initial file object for UI feedback
      const newFile: UploadedFile = {
        id: Math.random().toString(36).substr(2, 9),
        name: file.name,
        size: file.size,
        type: file.type,
        progress: 0,
        status: "uploading",
      };

      setUploadedFiles([newFile]);

      // Simulate progress for UI feedback
      const progressInterval = setInterval(() => {
        setUploadedFiles((prev) =>
          prev.map((f) => ({
            ...f,
            progress: Math.min(f.progress + 10, 90),
          }))
        );
      }, 200);

      // Upload using simple processing API
      const response = await simpleProcessingApi.uploadDocument(file);

      clearInterval(progressInterval);

      if (response.status === "success" && response.data) {
        // Update file with completed status and real document ID
        const completedFile: UploadedFile = {
          id: response.data.document_id,
          name: response.data.filename,
          size: response.data.size,
          type: file.type,
          progress: 100,
          status: "completed",
        };

        setUploadedFiles([completedFile]);

        toast({
          title: "Upload successful",
          description: `${file.name} has been uploaded successfully.`,
        });

        // Notify parent component
        onUploadComplete([completedFile]);
      } else {
        throw new Error(response.error?.message || "Upload failed");
      }
    } catch (error) {
      console.error("Upload error:", error);

      // Update file status to error
      setUploadedFiles((prev) =>
        prev.map((f) => ({
          ...f,
          progress: 100,
          status: "error" as const,
        }))
      );

      toast({
        title: "Upload failed",
        description:
          error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      processFiles(files);
    }
  }, []);

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        processFiles(files);
      }
    },
    []
  );

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center space-y-4"
      >
        <h2 className="text-2xl font-semibold">Upload Document</h2>
        <p className="text-muted-foreground max-w-md mx-auto">
          Upload your document to begin PII detection and masking. Supports PDF,
          Word (.docx), and text (.txt) files.
        </p>
      </motion.div>
      {/* Upload Area */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className={cn(
          "relative border-2 border-dashed rounded-lg p-8 transition-colors",
          isDragOver
            ? "border-blue-400 bg-blue-50 dark:bg-blue-900/10"
            : "border-gray-300 hover:border-gray-400 dark:border-gray-600",
          isUploading && "pointer-events-none opacity-50"
        )}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <div className="text-center space-y-4">
          <div className="mx-auto w-12 h-12 bg-blue-100 dark:bg-blue-900/20 rounded-lg flex items-center justify-center">
            <Upload className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <p className="text-lg font-medium">
              Drop your document here, or{" "}
              <button className="text-blue-600 hover:underline">
                browse files
              </button>
            </p>
            <p className="text-sm text-muted-foreground">
              Supports: PDF, Word (.docx), Text (.txt) - max 50MB
            </p>
          </div>
          <input
            type="file"
            className="absolute inset-0 opacity-0 cursor-pointer"
            accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
            onChange={handleFileInput}
            disabled={isUploading}
          />
        </div>
      </motion.div>
    </div>
  );
}
