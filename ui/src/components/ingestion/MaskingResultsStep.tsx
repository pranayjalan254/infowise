import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  CheckCircle,
  Download,
  Eye,
  FileText,
  Shield,
  ArrowLeftRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { documentsApi, maskingApi } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

interface DocumentData {
  id: string;
  name: string;
  size: number;
  type: string;
  mime_type: string;
  upload_date: string;
  status: string;
}

interface MaskingResultsStepProps {
  onComplete: () => void;
  detectedPIIData?: any;
  documentId?: string;
}

export function MaskingResultsStep({
  onComplete,
  detectedPIIData,
  documentId,
}: MaskingResultsStepProps) {
  const [documents, setDocuments] = useState<DocumentData[]>([]);
  const [loading, setLoading] = useState(true);
  const [maskingStatus, setMaskingStatus] = useState<any>(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const [activeView, setActiveView] = useState<
    "comparison" | "original" | "masked"
  >("comparison");

  useEffect(() => {
    const fetchMaskingStatus = async () => {
      if (!documentId) {
        console.error("No document ID provided");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);

        // Get masking status for the specific document
        const statusResponse = await maskingApi.getMaskingStatus(documentId);
        if (statusResponse.status === "success") {
          setMaskingStatus(statusResponse.data);
        }
      } catch (error) {
        console.error("Failed to fetch masking status:", error);
        toast({
          title: "Error",
          description: "Failed to load masking results",
          variant: "destructive",
        });
      } finally {
        setLoading(false);
      }
    };

    fetchMaskingStatus();
  }, [documentId]);

  const handleDownload = async () => {
    if (!maskingStatus?.masked_document_id) return;

    setIsDownloading(true);
    try {
      await documentsApi.downloadDocument(
        maskingStatus.masked_document_id,
        maskingStatus.masked_filename || "masked_document.pdf"
      );

      toast({
        title: "Download Successful",
        description: "Masked document has been downloaded",
      });
    } catch (error) {
      console.error("Download failed:", error);
      toast({
        title: "Download Failed",
        description: "Failed to download masked document",
        variant: "destructive",
      });
    } finally {
      setIsDownloading(false);
    }
  };

  const handlePreview = async () => {
    if (!documents[0]) return;
    setActiveView("comparison");
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="neumorphic-card p-6">
          <div className="flex items-center justify-center h-32">
            <div className="text-muted-foreground">
              Loading masking results...
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Success Header */}
      <motion.div
        className="neumorphic-card p-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <div className="flex items-center space-x-4">
          <div className="w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
            <CheckCircle
              size={32}
              className="text-green-600 dark:text-green-400"
            />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-foreground">
              PII Masking Complete!
            </h2>
            <p className="text-muted-foreground">
              Your document has been successfully processed and masked
            </p>
          </div>
        </div>
      </motion.div>

      {/* Masking Results */}
      {maskingStatus && (
        <motion.div
          className="neumorphic-card p-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          <Card className="border-0 shadow-none bg-transparent">
            <CardHeader className="px-0 pb-4">
              <CardTitle className="flex items-center">
                <Shield size={20} className="mr-2 text-primary" />
                Masking Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="px-0">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Total Masked Items */}
                <div className="neumorphic-flat p-4 rounded-xl text-center">
                  <div className="text-3xl font-bold text-primary mb-2">
                    {maskingStatus.total_pii_masked}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    PII Items Masked
                  </div>
                </div>

                {/* Strategies Used */}
                <div className="neumorphic-flat p-4 rounded-xl">
                  <h4 className="text-sm font-medium mb-3">
                    Strategies Applied
                  </h4>
                  <div className="space-y-2">
                    {Object.entries(maskingStatus.strategies_used || {}).map(
                      ([strategy, count]) => (
                        <div
                          key={strategy}
                          className="flex justify-between items-center"
                        >
                          <Badge variant="outline" className="capitalize">
                            {strategy}
                          </Badge>
                          <span className="text-sm font-medium">
                            {count as number}
                          </span>
                        </div>
                      )
                    )}
                  </div>
                </div>

                {/* Processing Stats */}
                <div className="neumorphic-flat p-4 rounded-xl">
                  <h4 className="text-sm font-medium mb-3">
                    Processing Details
                  </h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">
                        Success Rate
                      </span>
                      <span className="font-medium text-green-600">
                        {maskingStatus.failed_maskings === 0
                          ? "100%"
                          : `${Math.round(
                              (maskingStatus.total_pii_masked /
                                (maskingStatus.total_pii_masked +
                                  maskingStatus.failed_maskings)) *
                                100
                            )}%`}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">
                        Processed Date
                      </span>
                      <span className="font-medium">
                        {new Date(
                          maskingStatus.masking_date
                        ).toLocaleDateString()}
                      </span>
                    </div>
                    {maskingStatus.failed_maskings > 0 && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">
                          Failed Items
                        </span>
                        <span className="font-medium text-orange-600">
                          {maskingStatus.failed_maskings}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Document Actions */}
      <motion.div
        className="neumorphic-card p-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.2 }}
      >
        <Card className="border-0 shadow-none bg-transparent">
          <CardHeader className="px-0 pb-4">
            <CardTitle className="flex items-center">
              <FileText size={20} className="mr-2 text-primary" />
              Masked Document
            </CardTitle>
          </CardHeader>
          <CardContent className="px-0">
            <div className="neumorphic-flat p-6 rounded-xl">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <h4 className="font-medium">
                    {maskingStatus?.masked_filename || "Masked Document"}
                  </h4>
                  <p className="text-sm text-muted-foreground">
                    Your document with PII safely masked using selected
                    strategies
                  </p>
                </div>
                <div className="flex space-x-3">
                  <Button
                    variant="outline"
                    onClick={handlePreview}
                    className="neumorphic-button"
                  >
                    <ArrowLeftRight size={16} className="mr-2" />
                    Compare Documents
                  </Button>
                  <Button
                    onClick={handleDownload}
                    disabled={isDownloading}
                    className="neumorphic-button"
                  >
                    {isDownloading ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Downloading...
                      </>
                    ) : (
                      <>
                        <Download size={16} className="mr-2" />
                        Download
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Document Comparison */}
      {activeView === "comparison" && documentId && (
        <motion.div
          className="neumorphic-card p-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.3 }}
        >
          <Card className="border-0 shadow-none bg-transparent">
            <CardHeader className="px-0 pb-4">
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center">
                  <ArrowLeftRight size={20} className="mr-2 text-primary" />
                  Document Comparison
                </div>
                <Tabs
                  value={activeView}
                  onValueChange={(value) => setActiveView(value as any)}
                >
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="comparison">Side by Side</TabsTrigger>
                    <TabsTrigger value="original">Original Only</TabsTrigger>
                    <TabsTrigger value="masked">Masked Only</TabsTrigger>
                  </TabsList>
                </Tabs>
              </CardTitle>
            </CardHeader>
            <CardContent className="px-0">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Original Document */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium text-sm">Original Document</h4>
                    <Badge variant="outline" className="text-xs">
                      Before Masking
                    </Badge>
                  </div>
                  <div className="neumorphic-flat rounded-xl overflow-hidden">
                    <iframe
                      src={documentsApi.getViewUrl(documentId)}
                      className="w-full h-96 border-0"
                      title="Original Document"
                    />
                  </div>
                </div>

                {/* Masked Document */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium text-sm">Masked Document</h4>
                    <Badge variant="default" className="text-xs">
                      After Masking
                    </Badge>
                  </div>
                  <div className="neumorphic-flat rounded-xl overflow-hidden">
                    <iframe
                      src={
                        maskingStatus?.masked_document_id
                          ? documentsApi.getViewUrl(
                              maskingStatus.masked_document_id
                            )
                          : "about:blank"
                      }
                      className="w-full h-96 border-0"
                      title="Masked Document"
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Single Document Views */}
      {activeView === "original" && documents[0] && (
        <motion.div
          className="neumorphic-card p-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.3 }}
        >
          <Card className="border-0 shadow-none bg-transparent">
            <CardHeader className="px-0 pb-4">
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center">
                  <FileText size={20} className="mr-2 text-primary" />
                  Original Document
                </div>
                <Tabs
                  value={activeView}
                  onValueChange={(value) => setActiveView(value as any)}
                >
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="comparison">Side by Side</TabsTrigger>
                    <TabsTrigger value="original">Original Only</TabsTrigger>
                    <TabsTrigger value="masked">Masked Only</TabsTrigger>
                  </TabsList>
                </Tabs>
              </CardTitle>
            </CardHeader>
            <CardContent className="px-0">
              <div className="neumorphic-flat rounded-xl overflow-hidden">
                <iframe
                  src={documentsApi.getViewUrl(documentId)}
                  className="w-full h-96 border-0"
                  title="Original Document"
                />
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {activeView === "masked" && documents[0] && (
        <motion.div
          className="neumorphic-card p-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.3 }}
        >
          <Card className="border-0 shadow-none bg-transparent">
            <CardHeader className="px-0 pb-4">
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center">
                  <Shield size={20} className="mr-2 text-primary" />
                  Masked Document
                </div>
                <Tabs
                  value={activeView}
                  onValueChange={(value) => setActiveView(value as any)}
                >
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="comparison">Side by Side</TabsTrigger>
                    <TabsTrigger value="original">Original Only</TabsTrigger>
                    <TabsTrigger value="masked">Masked Only</TabsTrigger>
                  </TabsList>
                </Tabs>
              </CardTitle>
            </CardHeader>
            <CardContent className="px-0">
              <div className="neumorphic-flat rounded-xl overflow-hidden">
                <iframe
                  src={
                    maskingStatus?.masked_document_id
                      ? documentsApi.getViewUrl(
                          maskingStatus.masked_document_id
                        )
                      : "about:blank"
                  }
                  className="w-full h-96 border-0"
                  title="Masked Document"
                />
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Complete Workflow */}
      <motion.div
        className="neumorphic-card p-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.4 }}
      >
        <div className="text-center space-y-4">
          <div>
            <h3 className="text-lg font-semibold mb-2">Workflow Complete</h3>
            <p className="text-muted-foreground">
              Your document has been successfully processed through the PII
              detection and masking workflow.
            </p>
          </div>
          <Button onClick={onComplete} className="neumorphic-button">
            <CheckCircle size={16} className="mr-2" />
            Finish & Return to Dashboard
          </Button>
        </div>
      </motion.div>
    </div>
  );
}
