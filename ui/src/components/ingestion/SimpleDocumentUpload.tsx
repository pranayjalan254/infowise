import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Upload, Eye, Download } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FileText } from "lucide-react";
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
  onStartDetection?: () => void;
  uploadedFiles?: UploadedFile[];
}

export function SimpleDocumentUpload({
  onUploadComplete,
  onStartDetection,
  uploadedFiles: externalUploadedFiles,
}: SimpleDocumentUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const { toast } = useToast();

  // Use external uploaded files if provided, otherwise use internal state
  const currentUploadedFiles = externalUploadedFiles || uploadedFiles;
  const hasUploadedFiles = currentUploadedFiles.length > 0;

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

      // Create initial file objects for UI feedback
      const newFiles: UploadedFile[] = filesArray.map((file) => ({
        id: Math.random().toString(36).substr(2, 9),
        name: file.name,
        size: file.size,
        type: file.type,
        progress: 0,
        status: "uploading",
      }));

      setUploadedFiles(newFiles);

      // Check supported file types for all files
      const supportedTypes = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
      ];

      const invalidFiles = filesArray.filter(
        (file) => !supportedTypes.includes(file.type)
      );

      if (invalidFiles.length > 0) {
        toast({
          title: "Invalid file types",
          description: `${invalidFiles.length} file(s) are not supported. Only PDF, Word (.docx), and text (.txt) files are supported.`,
          variant: "destructive",
        });
        setIsUploading(false);
        return;
      }

      // Simulate progress for UI feedback
      const progressInterval = setInterval(() => {
        setUploadedFiles((prev) =>
          prev.map((f) => ({
            ...f,
            progress:
              f.status === "uploading"
                ? Math.min(f.progress + 10, 90)
                : f.progress,
          }))
        );
      }, 200);

      try {
        let response;
        if (filesArray.length === 1) {
          // Single file upload (backward compatibility)
          response = await simpleProcessingApi.uploadDocument(filesArray[0]);
        } else {
          // Multiple file upload
          response = await simpleProcessingApi.uploadMultipleDocuments(
            filesArray
          );
        }

        clearInterval(progressInterval);

        if (response.status === "success" && response.data) {
          let completedFiles: UploadedFile[];

          if (response.data.uploaded_documents) {
            // Bulk upload response
            completedFiles = response.data.uploaded_documents.map(
              (doc: any) => ({
                id: doc.document_id,
                name: doc.filename,
                size: doc.size,
                type:
                  filesArray.find((f) => f.name === doc.filename)?.type ||
                  "application/octet-stream",
                progress: 100,
                status: "completed" as const,
              })
            );

            // Show results
            const successCount = response.data.successful_uploads;
            const failCount = response.data.failed_count;

            if (failCount > 0) {
              toast({
                title: "Partial upload success",
                description: `${successCount} files uploaded successfully, ${failCount} files failed.`,
                variant: "default",
              });
            } else {
              toast({
                title: "Upload successful",
                description: `All ${successCount} files have been uploaded successfully.`,
              });
            }
          } else {
            // Single file upload response
            completedFiles = [
              {
                id: response.data.document_id,
                name: response.data.filename,
                size: response.data.size,
                type: filesArray[0].type,
                progress: 100,
                status: "completed",
              },
            ];

            toast({
              title: "Upload successful",
              description: `${filesArray[0].name} has been uploaded successfully.`,
            });
          }

          setUploadedFiles(completedFiles);

          // Notify parent component
          onUploadComplete(completedFiles);
        } else {
          throw new Error(response.error?.message || "Upload failed");
        }
      } catch (uploadError) {
        clearInterval(progressInterval);
        throw uploadError;
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
        <h2 className="text-2xl font-semibold">Upload Documents</h2>
        <p className="text-muted-foreground max-w-md mx-auto">
          Upload one or more documents to begin PII detection and masking.
          Supports PDF, Word (.docx), and text (.txt) files.
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
              Drop your documents here, or{" "}
              <button className="text-blue-600 hover:underline">
                browse files
              </button>
            </p>
            <p className="text-sm text-muted-foreground">
              Supports: PDF, Word (.docx), Text (.txt) - max 50MB each
            </p>
          </div>
          <input
            type="file"
            className="absolute inset-0 opacity-0 cursor-pointer"
            accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
            onChange={handleFileInput}
            disabled={isUploading}
            multiple
          />
        </div>
      </motion.div>

      {/* Uploaded Files Display */}
      {hasUploadedFiles && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="space-y-6"
        >
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium">Uploaded Files</h3>
            <Badge variant="secondary">
              {currentUploadedFiles.length} files
            </Badge>
          </div>

          {/* File Tabs for Preview */}
          {currentUploadedFiles.length > 1 ? (
            <Tabs defaultValue={currentUploadedFiles[0]?.id} className="w-full">
              <TabsList
                className="grid w-full"
                style={{
                  gridTemplateColumns: `repeat(${currentUploadedFiles.length}, 1fr)`,
                }}
              >
                {currentUploadedFiles.map((file) => (
                  <TabsTrigger
                    key={file.id}
                    value={file.id}
                    className="flex items-center space-x-2"
                  >
                    <FileText className="w-4 h-4" />
                    <span className="truncate max-w-[120px]">{file.name}</span>
                  </TabsTrigger>
                ))}
              </TabsList>

              {currentUploadedFiles.map((file) => (
                <TabsContent
                  key={file.id}
                  value={file.id}
                  className="space-y-4"
                >
                  {renderFilePreview(file)}
                </TabsContent>
              ))}
            </Tabs>
          ) : (
            // Single file - no tabs needed
            currentUploadedFiles.length === 1 &&
            renderFilePreview(currentUploadedFiles[0])
          )}

          {/* Start Detection Button */}
          {onStartDetection && (
            <div className="flex justify-center pt-4">
              <Button
                onClick={onStartDetection}
                size="lg"
                className="px-8"
                disabled={
                  !currentUploadedFiles.every(
                    (file) => file.status === "completed"
                  )
                }
              >
                <Eye className="w-5 h-5 mr-2" />
                Start PII Detection for All Files
              </Button>
            </div>
          )}
        </motion.div>
      )}

      {/* Original Simple Files List (fallback) */}
      {!externalUploadedFiles && uploadedFiles.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="space-y-4"
        >
          <h3 className="text-lg font-medium">Uploaded Files</h3>
          <div className="space-y-2">
            {uploadedFiles.map((file) => (
              <div
                key={file.id}
                className="flex items-center justify-between p-4 border rounded-lg bg-card"
              >
                <div className="flex items-center space-x-3">
                  <div
                    className={cn(
                      "w-3 h-3 rounded-full",
                      file.status === "completed" && "bg-green-500",
                      file.status === "uploading" &&
                        "bg-blue-500 animate-pulse",
                      file.status === "error" && "bg-red-500"
                    )}
                  />
                  <div>
                    <p className="font-medium">{file.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {file.status === "uploading" && (
                    <div className="text-sm text-muted-foreground">
                      {file.progress}%
                    </div>
                  )}
                  <div
                    className={cn(
                      "text-sm font-medium",
                      file.status === "completed" && "text-green-600",
                      file.status === "uploading" && "text-blue-600",
                      file.status === "error" && "text-red-600"
                    )}
                  >
                    {file.status === "completed" && "Uploaded"}
                    {file.status === "uploading" && "Uploading..."}
                    {file.status === "error" && "Failed"}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );

  // Helper function to render file preview
  function renderFilePreview(file: UploadedFile) {
    return (
      <div className="space-y-4">
        {/* File Info */}
        <div className="flex items-center justify-between p-4 border rounded-lg bg-card">
          <div className="flex items-center space-x-3">
            <div
              className={cn(
                "w-3 h-3 rounded-full",
                file.status === "completed" && "bg-green-500",
                file.status === "uploading" && "bg-blue-500 animate-pulse",
                file.status === "error" && "bg-red-500"
              )}
            />
            <div>
              <p className="font-medium">{file.name}</p>
              <p className="text-sm text-muted-foreground">
                {(file.size / 1024 / 1024).toFixed(2)} MB •{" "}
                {file.status === "completed"
                  ? "Ready for PII detection"
                  : file.status}
              </p>
            </div>
          </div>
          <Badge
            variant={file.status === "completed" ? "secondary" : "outline"}
          >
            {file.status === "completed" ? "Uploaded" : file.status}
          </Badge>
        </div>

        {/* Document Preview - Only for PDFs */}
        {file.type === "application/pdf" && file.status === "completed" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="font-medium flex items-center">
                <Eye className="w-5 h-5 mr-2" />
                Document Preview
              </h4>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  window.open(
                    simpleProcessingApi.getPreviewUrl(file.id),
                    "_blank"
                  );
                }}
              >
                <Download className="w-4 h-4 mr-2" />
                Open PDF
              </Button>
            </div>
            <Card>
              <CardContent className="p-4">
                <div className="rounded-lg overflow-hidden bg-white">
                  <iframe
                    src={simpleProcessingApi.getPreviewUrl(file.id)}
                    className="w-full h-[500px] border-0"
                    title="Document Preview"
                  />
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Non-PDF Document Info */}
        {file.type !== "application/pdf" && file.status === "completed" && (
          <Card>
            <CardContent className="p-8 text-center">
              <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h4 className="text-lg font-medium mb-2">
                {file.type.includes("word") ? "Word Document" : "Text Document"}
              </h4>
              <p className="text-muted-foreground mb-4">
                Preview not available for this file type. The document is ready
                for PII detection.
              </p>
              <Button
                variant="outline"
                onClick={() => {
                  window.open(
                    simpleProcessingApi.getPreviewUrl(file.id),
                    "_blank"
                  );
                }}
              >
                <Download className="w-4 h-4 mr-2" />
                Download to View
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    );
  }
}
