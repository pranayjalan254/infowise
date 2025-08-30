import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { FileText, Download, Shield, ChevronRight, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { documentsApi } from "@/lib/api";

interface DocumentData {
  id: string;
  name: string;
  size: number;
  type: string;
  mime_type: string;
  upload_date: string;
  status: string;
}

interface DocumentReviewProps {
  uploadedDocumentIds?: string[]; // Optional: filter to show only these documents
  onDetectPII: () => void;
}

export function DocumentReview({
  uploadedDocumentIds,
  onDetectPII,
}: DocumentReviewProps) {
  const [documents, setDocuments] = useState<DocumentData[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDocument, setSelectedDocument] = useState<string>("");

  const selectedFile = documents.find((doc) => doc.id === selectedDocument);

  useEffect(() => {
    const fetchDocuments = async () => {
      try {
        setLoading(true);
        const response = await documentsApi.list();
        let allDocuments = response.data?.documents || [];

        // Filter to show only uploaded documents if IDs are provided
        if (uploadedDocumentIds && uploadedDocumentIds.length > 0) {
          allDocuments = allDocuments.filter((doc) =>
            uploadedDocumentIds.includes(doc.id)
          );
        }

        setDocuments(allDocuments);

        // Auto-select the first document
        if (allDocuments.length > 0 && !selectedDocument) {
          setSelectedDocument(allDocuments[0].id);
        }
      } catch (error) {
        console.error("Failed to fetch documents:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchDocuments();
  }, [selectedDocument]);

  const handleDownload = async (documentId: string, fileName: string) => {
    try {
      await documentsApi.downloadDocument(documentId, fileName);
    } catch (error) {
      console.error("Download failed:", error);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="neumorphic-card p-6">
          <div className="flex items-center justify-center h-32">
            <div className="text-muted-foreground">Loading documents...</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        className="neumorphic-card p-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-foreground mb-2">
              Document Review
            </h2>
            <p className="text-muted-foreground">
              Review your uploaded documents before PII detection
            </p>
          </div>
          <Button onClick={onDetectPII} className="neumorphic-button" size="lg">
            <Shield size={20} className="mr-2" />
            Detect PII
            <ChevronRight size={16} className="ml-2" />
          </Button>
        </div>

        <div className="flex items-center space-x-4">
          <Badge variant="secondary" className="px-3 py-1">
            {documents.length} document
            {documents.length !== 1 ? "s" : ""} uploaded
          </Badge>
          <Badge variant="outline" className="px-3 py-1">
            Total size:{" "}
            {(
              documents.reduce((acc, doc) => acc + doc.size, 0) /
              1024 /
              1024
            ).toFixed(2)}{" "}
            MB
          </Badge>
        </div>
      </motion.div>

      {/* Main Content - Split Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Side - Document List */}
        <motion.div
          className="space-y-6"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          <Card className="neumorphic-card">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center">
                <FileText size={20} className="mr-2 text-primary" />
                Uploaded Documents
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {documents.map((doc) => (
                  <motion.div
                    key={doc.id}
                    className={`neumorphic-flat p-4 rounded-xl cursor-pointer transition-all duration-200 ${
                      selectedDocument === doc.id
                        ? "border-2 border-primary/50 bg-primary/5"
                        : "border border-transparent hover:border-muted-foreground/20"
                    }`}
                    onClick={() => setSelectedDocument(doc.id)}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 rounded-lg bg-primary/10">
                          <FileText className="w-5 h-5 text-primary" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="font-medium text-foreground text-sm truncate">
                            {doc.name}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {(doc.size / 1024 / 1024).toFixed(2)} MB •{" "}
                            {doc.type || "PDF"}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        {selectedDocument === doc.id && (
                          <Badge variant="default" className="text-xs">
                            <Eye size={12} className="mr-1" />
                            Viewing
                          </Badge>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDownload(doc.id, doc.name);
                          }}
                        >
                          <Download size={14} />
                        </Button>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Document Stats */}
          <Card className="neumorphic-card">
            <CardHeader className="pb-4">
              <CardTitle className="text-lg">Document Statistics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div className="neumorphic-flat p-3 rounded-xl text-center">
                  <div className="text-xl font-bold text-foreground mb-1">
                    {documents.length}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Total Files
                  </div>
                </div>

                <div className="neumorphic-flat p-3 rounded-xl text-center">
                  <div className="text-xl font-bold text-primary mb-1">
                    {
                      documents.filter(
                        (doc) =>
                          doc.mime_type?.includes("pdf") ||
                          doc.type?.includes("pdf")
                      ).length
                    }
                  </div>
                  <div className="text-xs text-muted-foreground">PDF Files</div>
                </div>

                <div className="neumorphic-flat p-3 rounded-xl text-center">
                  <div className="text-xl font-bold text-warning mb-1">0</div>
                  <div className="text-xs text-muted-foreground">
                    PII Detected
                  </div>
                </div>

                <div className="neumorphic-flat p-3 rounded-xl text-center">
                  <div className="text-xl font-bold text-success mb-1">
                    100%
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Upload Success
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Right Side - Document Preview */}
        <motion.div
          className="space-y-6"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
        >
          <Card className="neumorphic-card">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center">
                  <Eye size={20} className="mr-2 text-primary" />
                  Document Preview
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="neumorphic-button"
                  disabled={!selectedFile}
                  onClick={() =>
                    selectedFile &&
                    handleDownload(selectedFile.id, selectedFile.name)
                  }
                >
                  <Download size={16} className="mr-2" />
                  Download
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="neumorphic-inset rounded-xl overflow-hidden">
                {selectedFile ? (
                  <iframe
                    src={documentsApi.getViewUrl(selectedFile.id)}
                    className="w-full h-[600px] border-0"
                    title="Document Preview"
                  />
                ) : (
                  <div
                    className="w-full h-[600px] border-0 flex items-center justify-center"
                    style={{
                      background:
                        "linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)",
                    }}
                  >
                    <p className="text-muted-foreground">
                      Select a document to preview
                    </p>
                  </div>
                )}
              </div>
              <div className="mt-4 text-center">
                <p className="text-sm text-muted-foreground">
                  {selectedFile
                    ? selectedFile.name
                    : "Select a document to preview"}
                </p>
                {selectedFile && (
                  <p className="text-xs text-muted-foreground mt-1">
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB •
                    Uploaded:{" "}
                    {new Date(selectedFile.upload_date).toLocaleDateString()}
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
