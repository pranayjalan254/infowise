import { motion } from "framer-motion";
import { useState, useEffect } from "react";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";
import { FileText, Upload, Download, Trash2, Search } from "lucide-react";
import { WorkflowTracker } from "@/components/ui/workflow-tracker";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { mockWorkflowSteps, chartData } from "@/data/mockData";
import { documentsApi, simpleProcessingApi } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { useNavigate } from "react-router-dom";

interface Document {
  id: string;
  name: string;
  size: number;
  type: string;
  mime_type: string;
  upload_date: string;
  status: string;
}

export default function Dashboard() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();
  const navigate = useNavigate();

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const [docsResponse] = await Promise.all([documentsApi.list()]);

      if (docsResponse.status === "success" && docsResponse.data) {
        setDocuments(docsResponse.data.documents);
      }
    } catch (error) {
      console.error("Failed to fetch documents:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleDelete = async (documentId: string, documentName: string) => {
    try {
      const response = await documentsApi.delete(documentId);
      if (response.status === "success") {
        setDocuments((prev) => prev.filter((doc) => doc.id !== documentId));
        toast({
          title: "Document deleted",
          description: `${documentName} has been deleted successfully`,
        });
        fetchDocuments(); // Refresh stats
      }
    } catch (error) {
      console.error("Delete error:", error);
      toast({
        title: "Delete failed",
        description: "Failed to delete document",
        variant: "destructive",
      });
    }
  };

  const handleDownload = async (
    documentId: string,
    documentName: string,
    downloadType: "masked"
  ) => {
    try {
      let blob;

      try {
        console.log("Trying MongoDB download for masked file...");
        blob = await simpleProcessingApi.downloadFromMongo(
          documentId,
          "masked"
        );
        console.log("MongoDB masked download successful");
      } catch (mongoError) {
        console.log("MongoDB masked download failed:", mongoError);

        // Approach 2: Try local masked file download
        try {
          console.log("Trying local masked file download...");
          blob = await simpleProcessingApi.downloadMaskedDocument(documentId);
          console.log("Local masked download successful");
        } catch (localError) {
          console.log("Local masked download failed:", localError);
          throw new Error(
            "No masked version available. Please ensure the document has been processed through the PII masking workflow."
          );
        }
      }

      // Create download link if we have a blob
      if (blob) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download =
          downloadType === "masked"
            ? `${documentName}_masked.pdf`
            : documentName;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        toast({
          title: "Download Started",
          description: `${
            downloadType === "masked" ? "Masked" : "Original"
          } document is being downloaded.`,
        });
      }
    } catch (error) {
      console.error("Download error:", error);
      toast({
        title: "Download Failed",
        description: `Failed to download ${downloadType} document: ${
          error instanceof Error ? error.message : "Unknown error"
        }`,
        variant: "destructive",
      });
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const filteredDocuments = documents.filter((doc) => {
    const matchesSearch = doc.name
      .toLowerCase()
      .includes(searchTerm.toLowerCase());
    const matchesTab = doc.status.toLowerCase() === "masked";
    return matchesSearch && matchesTab;
  });

  const recentDocuments = filteredDocuments.slice(0, 6);
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <h1 className="text-3xl font-bold text-display text-foreground mb-2">
          Dashboard
        </h1>
        <p className="text-muted-foreground">
          Overview of your data privacy and compliance operations
        </p>
      </motion.div>

      {/* Recent Documents Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.35 }}
      >
        <Card className="neumorphic-card">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-xl font-semibold text-foreground">
                  Masked Documents
                </CardTitle>
              </div>
              <div className="flex items-center space-x-2">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
                  <Input
                    placeholder="Search documents..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10 w-64"
                  />
                </div>
                <Button
                  onClick={() => navigate("/ingestion")}
                  className="neumorphic-button"
                >
                  <Upload className="w-4 h-4 mr-2" />
                  Upload New
                </Button>
              </div>
            </div>
          </CardHeader>

          <CardContent>
            <div className="w-full">
              <div className="mt-0">
                {loading ? (
                  <div className="flex items-center justify-center h-32">
                    <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
                  </div>
                ) : recentDocuments.length === 0 ? (
                  <div className="text-center py-12">
                    <FileText className="w-12 h-12 text-muted-foreground mx-auto mb-4" />

                    <p className="text-muted-foreground mb-4">
                      Upload your first document to get started
                    </p>
                    {documents.length === 0 && (
                      <Button
                        onClick={() => navigate("/ingestion")}
                        className="neumorphic-button"
                      >
                        <Upload className="w-4 h-4 mr-2" />
                        Upload Documents
                      </Button>
                    )}
                  </div>
                ) : (
                  <div className="space-y-3">
                    {recentDocuments.map((document, index) => (
                      <motion.div
                        key={document.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.3, delay: index * 0.05 }}
                        className="flex items-center justify-between p-4 neumorphic-flat rounded-lg hover:neumorphic-hover transition-all duration-200"
                      >
                        <div className="flex items-center space-x-4 flex-1">
                          <div className="flex-shrink-0">
                            <div className="w-10 h-10 neumorphic-flat rounded-lg flex items-center justify-center">
                              <FileText className="w-5 h-5 text-blue-500" />
                            </div>
                          </div>

                          <div className="flex-1 min-w-0">
                            <h4 className="text-sm font-medium text-foreground truncate">
                              {document.name}
                            </h4>
                            <div className="flex items-center space-x-4 mt-1">
                              <span className="text-xs text-muted-foreground">
                                {formatFileSize(document.size)}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {formatDate(document.upload_date)}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center space-x-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() =>
                              handleDownload(
                                document.id,
                                document.name,
                                "masked"
                              )
                            }
                            className="h-10 w-12 bg-blue-50 "
                          >
                            <Download className="w-4 h-4" />
                          </Button>
                          <Button
                            className=""
                            onClick={() =>
                              handleDelete(document.id, document.name)
                            }
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </motion.div>
                    ))}

                    {filteredDocuments.length > 6 && (
                      <div className="text-center pt-4">
                        <Button
                          variant="outline"
                          onClick={() => navigate("/ingestion")}
                          className="neumorphic-button"
                        >
                          View All {filteredDocuments.length} Documents
                        </Button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Charts and Workflow */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Workflow Tracker */}
        <div className="lg:col-span-1">
          <WorkflowTracker steps={mockWorkflowSteps} />
        </div>

        {/* Sensitivity Analysis Chart */}
        <motion.div
          className="chart-container"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, delay: 0.2 }}
        >
          <h3 className="text-lg font-semibold text-foreground mb-4">
            PII Sensitivity Analysis
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={chartData.sensitivityAnalysis}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                dataKey="value"
              >
                {chartData.sensitivityAnalysis.map((entry, index) => (
                  <Cell key={index} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-center space-x-4 mt-4">
            {chartData.sensitivityAnalysis.map((item) => (
              <div key={item.name} className="flex items-center space-x-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-sm text-muted-foreground">
                  {item.name} ({item.value})
                </span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Compliance Scores */}
        <motion.div
          className="chart-container"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, delay: 0.3 }}
        >
          <h3 className="text-lg font-semibold text-foreground mb-4">
            Compliance Scores
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData.complianceScores}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis
                dataKey="framework"
                fontSize={12}
                tick={{ fill: "hsl(var(--muted-foreground))" }}
              />
              <YAxis
                fontSize={12}
                tick={{ fill: "hsl(var(--muted-foreground))" }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--popover))",
                  border: "none",
                  borderRadius: "12px",
                  boxShadow: "var(--shadow-light), var(--shadow-dark)",
                }}
              />
              <Bar
                dataKey="score"
                fill="hsl(var(--primary))"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </motion.div>
      </div>

      {/* Monthly Trends */}
      <motion.div
        className="chart-container"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.4 }}
      >
        <h3 className="text-lg font-semibold text-foreground mb-4">
          Monthly Trends
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData.monthlyTrends}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis
              dataKey="month"
              fontSize={12}
              tick={{ fill: "hsl(var(--muted-foreground))" }}
            />
            <YAxis
              fontSize={12}
              tick={{ fill: "hsl(var(--muted-foreground))" }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--popover))",
                border: "none",
                borderRadius: "12px",
                boxShadow: "var(--shadow-light), var(--shadow-dark)",
              }}
            />
            <Line
              type="monotone"
              dataKey="documents"
              stroke="hsl(var(--primary))"
              strokeWidth={3}
              dot={{ fill: "hsl(var(--primary))", strokeWidth: 2, r: 4 }}
              name="Documents"
            />
            <Line
              type="monotone"
              dataKey="piiDetected"
              stroke="hsl(var(--accent))"
              strokeWidth={3}
              dot={{ fill: "hsl(var(--accent))", strokeWidth: 2, r: 4 }}
              name="PII Detected"
            />
            <Line
              type="monotone"
              dataKey="masked"
              stroke="hsl(var(--success))"
              strokeWidth={3}
              dot={{ fill: "hsl(var(--success))", strokeWidth: 2, r: 4 }}
              name="Masked"
            />
          </LineChart>
        </ResponsiveContainer>
      </motion.div>
    </div>
  );
}
