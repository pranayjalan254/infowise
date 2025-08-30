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
import {
  FileText,
  Upload,
  MoreVertical,
  Eye,
  Download,
  Trash2,
  Search,
  Filter,
  CheckCircle,
} from "lucide-react";
import { MetricCard } from "@/components/ui/metric-card";
import { WorkflowTracker } from "@/components/ui/workflow-tracker";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  mockDashboardMetrics,
  mockWorkflowSteps,
  chartData,
} from "@/data/mockData";
import { documentsApi } from "@/lib/api";
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

interface DocumentStats {
  total_documents: number;
  total_size_bytes: number;
  total_size_mb: number;
  file_types: Record<string, { count: number; size: number }>;
}

export default function Dashboard() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [stats, setStats] = useState<DocumentStats | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();
  const navigate = useNavigate();

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const [docsResponse, statsResponse] = await Promise.all([
        documentsApi.list(),
        documentsApi.getStats(),
      ]);

      if (docsResponse.status === "success" && docsResponse.data) {
        setDocuments(docsResponse.data.documents);
      }

      if (statsResponse.status === "success" && statsResponse.data) {
        setStats(statsResponse.data);
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case "uploaded":
        return "bg-green-100 text-green-800";
      case "processing":
        return "bg-yellow-100 text-yellow-800";
      case "error":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const filteredDocuments = documents.filter((doc) =>
    doc.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const recentDocuments = filteredDocuments.slice(0, 6); // Show only 6 recent documents
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

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        {/* Dynamic Documents Metric */}
        {stats && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
          >
            <MetricCard
              metric={{
                id: "documents",
                title: "Total Documents",
                value: stats.total_documents,
                change: 12.5,
                trend: "up",
                unit: "",
                icon: "FileText",
              }}
              index={0}
            />
          </motion.div>
        )}

        {/* Dynamic Storage Metric */}
        {stats && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.15 }}
          >
            <MetricCard
              metric={{
                id: "storage",
                title: "Storage Used",
                value: stats.total_size_mb.toFixed(1),
                change: 8.2,
                trend: "up",
                unit: "MB",
                icon: "HardDrive",
              }}
              index={1}
            />
          </motion.div>
        )}

        {/* Static Metrics */}
        {mockDashboardMetrics.slice(0, 3).map((metric, index) => (
          <motion.div
            key={metric.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.2 + index * 0.05 }}
          >
            <MetricCard metric={metric} index={index + 2} />
          </motion.div>
        ))}
      </div>

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
                  Recent Documents
                </CardTitle>
                <p className="text-sm text-muted-foreground mt-1">
                  {stats
                    ? `${
                        stats.total_documents
                      } total documents (${stats.total_size_mb.toFixed(1)} MB)`
                    : "Loading..."}
                </p>
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
            {loading ? (
              <div className="flex items-center justify-center h-32">
                <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
              </div>
            ) : recentDocuments.length === 0 ? (
              <div className="text-center py-12">
                <FileText className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium text-foreground mb-2">
                  {documents.length === 0
                    ? "No documents uploaded"
                    : "No documents found"}
                </h3>
                <p className="text-muted-foreground mb-4">
                  {documents.length === 0
                    ? "Upload your first document to get started"
                    : "Try adjusting your search criteria"}
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
                          <Badge
                            className={`${getStatusColor(
                              document.status
                            )} text-xs`}
                          >
                            {document.status}
                          </Badge>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0"
                          >
                            <MoreVertical className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem>
                            <Eye className="w-4 h-4 mr-2" />
                            View Details
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <Download className="w-4 h-4 mr-2" />
                            Download
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="text-red-600"
                            onClick={() =>
                              handleDelete(document.id, document.name)
                            }
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
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
