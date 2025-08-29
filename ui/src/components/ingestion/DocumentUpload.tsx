import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Upload, FileText, CheckCircle, X, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';

interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  progress: number;
  status: 'uploading' | 'completed' | 'error';
}

interface DocumentUploadProps {
  onUploadComplete: (files: UploadedFile[]) => void;
}

export function DocumentUpload({ onUploadComplete }: DocumentUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);

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

  const simulateUpload = (file: File): UploadedFile => {
    return {
      id: Math.random().toString(36).substr(2, 9),
      name: file.name,
      size: file.size,
      type: file.type,
      progress: 0,
      status: 'uploading'
    };
  };

  const processFiles = async (files: FileList | File[]) => {
    setIsUploading(true);
    const newFiles = Array.from(files).map(simulateUpload);
    setUploadedFiles(newFiles);

    // Simulate upload progress
    for (let i = 0; i < newFiles.length; i++) {
      const file = newFiles[i];
      for (let progress = 0; progress <= 100; progress += 10) {
        await new Promise(resolve => setTimeout(resolve, 100));
        setUploadedFiles(prev => 
          prev.map(f => 
            f.id === file.id 
              ? { ...f, progress }
              : f
          )
        );
      }
      
      setUploadedFiles(prev => 
        prev.map(f => 
          f.id === file.id 
            ? { ...f, status: 'completed' }
            : f
        )
      );
    }

    setIsUploading(false);
    setTimeout(() => {
      onUploadComplete(newFiles.map(f => ({ ...f, status: 'completed' })));
    }, 500);
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

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      processFiles(files);
    }
  };

  const removeFile = (fileId: string) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusIcon = (status: UploadedFile['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle size={16} className="text-success" />;
      case 'error':
        return <AlertCircle size={16} className="text-danger" />;
      default:
        return <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Upload Area */}
      <motion.div
        className={cn(
          "neumorphic-card border-2 border-dashed transition-all duration-300 cursor-pointer",
          isDragOver ? "border-primary bg-primary/5" : "border-border",
          uploadedFiles.length > 0 ? "p-4" : "p-12"
        )}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        {uploadedFiles.length === 0 ? (
          <div className="text-center">
            <motion.div
              className="neumorphic-raised w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Upload size={24} className="text-primary" />
            </motion.div>
            
            <h3 className="text-xl font-semibold text-foreground mb-2">
              Upload Documents for Processing
            </h3>
            <p className="text-muted-foreground mb-6">
              Drag and drop your files here, or click to select files
            </p>
            
            <div className="space-y-3">
              <Button 
                className="neumorphic-button"
                onClick={() => document.getElementById('file-input')?.click()}
              >
                <Upload size={16} className="mr-2" />
                Choose Files
              </Button>
              
              <p className="text-xs text-muted-foreground">
                Supports PDF, DOC, DOCX, TXT, CSV files up to 50MB each
              </p>
            </div>
            
            <input
              id="file-input"
              type="file"
              multiple
              accept=".pdf,.doc,.docx,.txt,.csv"
              onChange={handleFileSelect}
              className="hidden"
            />
          </div>
        ) : (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-medium text-foreground">
                Uploaded Documents ({uploadedFiles.length})
              </h4>
              {!isUploading && (
                <Button 
                  size="sm"
                  variant="outline"
                  className="neumorphic-button"
                  onClick={() => document.getElementById('file-input')?.click()}
                >
                  <Upload size={14} className="mr-2" />
                  Add More
                </Button>
              )}
            </div>
            
            <div className="space-y-3">
              {uploadedFiles.map((file, index) => (
                <motion.div
                  key={file.id}
                  className="neumorphic-flat p-4 rounded-xl"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: index * 0.1 }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-3">
                      <FileText size={16} className="text-primary" />
                      <div>
                        <p className="font-medium text-foreground text-sm">{file.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatFileSize(file.size)}
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(file.status)}
                      {file.status === 'completed' && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => removeFile(file.id)}
                          className="neumorphic-button p-1 h-6 w-6"
                        >
                          <X size={12} />
                        </Button>
                      )}
                    </div>
                  </div>
                  
                  {file.status === 'uploading' && (
                    <div className="space-y-1">
                      <Progress value={file.progress} className="h-1" />
                      <p className="text-xs text-muted-foreground">
                        Uploading... {file.progress}%
                      </p>
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
            
            <input
              id="file-input"
              type="file"
              multiple
              accept=".pdf,.doc,.docx,.txt,.csv"
              onChange={handleFileSelect}
              className="hidden"
            />
          </div>
        )}
      </motion.div>

      {/* Processing Notice */}
      {uploadedFiles.length > 0 && !isUploading && (
        <motion.div
          className="neumorphic-card p-6 text-center"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, delay: 0.2 }}
        >
          <CheckCircle size={24} className="mx-auto mb-3 text-success" />
          <h4 className="font-semibold text-foreground mb-2">
            Documents Successfully Uploaded
          </h4>
          <p className="text-muted-foreground mb-4">
            Your documents are ready for AI-powered privacy analysis and processing
          </p>
          <Button 
            className="neumorphic-button"
            onClick={() => onUploadComplete(uploadedFiles)}
          >
            Start Processing
          </Button>
        </motion.div>
      )}
    </div>
  );
}