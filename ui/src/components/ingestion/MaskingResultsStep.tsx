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
  documentId,
}: MaskingResultsStepProps) {
  const [loading, setLoading] = useState(true);
  const [maskingStatus, setMaskingStatus] = useState<any>(null);
  const [isDownloading, setIsDownloading] = useState(false);

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
          {/* Header with Download Button */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-lg bg-primary/10">
                <Shield size={20} className="text-primary" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-foreground">
                  Masking Complete
                </h3>
                <p className="text-sm text-muted-foreground">
                  {maskingStatus?.masked_filename ||
                    "Document successfully processed"}
                </p>
              </div>
            </div>
            <Button
              onClick={handleDownload}
              disabled={isDownloading}
              className="neumorphic-button bg-primary text-primary-foreground hover:bg-primary/90"
              size="lg"
            >
              {isDownloading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Downloading...
                </>
              ) : (
                <>
                  <Download size={18} className="mr-2" />
                  Download Masked PDF
                </>
              )}
            </Button>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Total Masked Items */}
            <div className="neumorphic-flat p-6 rounded-xl text-center group hover:shadow-lg transition-all duration-300">
              <div className="text-4xl font-bold text-primary mb-2 group-hover:scale-110 transition-transform">
                {maskingStatus.total_pii_masked}
              </div>
              <div className="text-sm font-medium text-muted-foreground">
                Items Protected
              </div>
            </div>

            {/* Strategies Used */}
            <div className="neumorphic-flat p-6 rounded-xl">
              <h4 className="text-sm font-semibold mb-3 text-foreground">
                Protection Methods
              </h4>
              <div className="space-y-2">
                {Object.entries(maskingStatus.strategies_used || {}).length >
                0 ? (
                  Object.entries(maskingStatus.strategies_used || {}).map(
                    ([strategy, count]) => (
                      <div
                        key={strategy}
                        className="flex justify-between items-center py-1"
                      >
                        <Badge
                          variant="secondary"
                          className="capitalize text-xs bg-primary/10 text-primary hover:bg-primary/20"
                        >
                          {strategy}
                        </Badge>
                        <span className="text-sm font-semibold text-foreground">
                          {count as number}
                        </span>
                      </div>
                    )
                  )
                ) : (
                  <div className="text-sm text-muted-foreground text-center py-2">
                    No strategies applied
                  </div>
                )}
              </div>
            </div>

            {/* Success Rate */}
            <div className="neumorphic-flat p-6 rounded-xl">
              <h4 className="text-sm font-semibold mb-3 text-foreground">
                Success Rate
              </h4>
              <div className="text-center">
                <div
                  className={`text-3xl font-bold mb-2 ${
                    maskingStatus.failed_maskings === 0
                      ? "text-green-500"
                      : maskingStatus.total_pii_masked >
                        maskingStatus.failed_maskings
                      ? "text-yellow-500"
                      : "text-red-500"
                  }`}
                >
                  {maskingStatus.failed_maskings === 0
                    ? "100%"
                    : `${Math.round(
                        (maskingStatus.total_pii_masked /
                          (maskingStatus.total_pii_masked +
                            maskingStatus.failed_maskings)) *
                          100
                      )}%`}
                </div>
                <div className="text-xs text-muted-foreground">
                  {maskingStatus.failed_maskings > 0 ? (
                    <span className="text-orange-600">
                      {maskingStatus.failed_maskings} failed
                    </span>
                  ) : (
                    "All items processed"
                  )}
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Document Comparison */}
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
            </CardTitle>
          </CardHeader>
          <CardContent className="px-0">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Original Document */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium text-sm">Original Document</h4>
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
