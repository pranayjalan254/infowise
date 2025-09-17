import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Wand2,
  CheckSquare,
  Square,
  Download,
  Eye,
  EyeOff,
  CheckCircle,
  Users,
  FileText,
  Home,
  MapPin,
  CreditCard,
  Shield,
  Tag,
} from "lucide-react";
import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { simpleProcessingApi } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

interface PIIItem {
  id: string;
  type: string;
  text: string;
  confidence: number;
  location: string;
  severity: "low" | "medium" | "high";
  suggested_strategy: string;
  coordinates: any;
}

interface SimpleMaskingStepProps {
  detectedPIIData: {
    document_id: string;
    total_pii: number;
    config_data: PIIItem[];
  };
  onMaskingComplete: (results: any) => void;
}

const maskingStrategies = [
  {
    value: "redact",
    label: "Redact",
    description: "Complete blackout/removal",
  },
  { value: "mask", label: "Mask", description: "Replace with asterisks" },
  {
    value: "pseudo",
    label: "Pseudonymize",
    description: "Replace with fake data",
  },
];

// PII Category definitions
const PII_CATEGORIES = {
  person: {
    label: "Person",
    icon: Users,
    description: "Names and personal identifiers",
    types: ["PERSON"],
  },
  locationAddress: {
    label: "Location/Address",
    icon: MapPin,
    description: "Geographic and address information",
    types: ["ADDRESS", "LOC", "COORDINATES"],
  },
  codes: {
    label: "Codes",
    icon: Tag,
    description: "Various codes and technical identifiers",
    types: [
      "ZIP_CODE",
      "MAC_ADDRESS",
      "IP_ADDRESS",
      "VEHICLE_PLATE",
      "BARCODE",
      "VOLUNTEER_CODE",
      "RECEIPT_NUMBER",
      "TRACKING_NUMBER",
      "URL",
      "VACCINE_LOT",
    ],
  },
  identityCards: {
    label: "Identity Cards",
    icon: Shield,
    description: "Official identification documents",
    types: [
      "EMPLOYEE_ID",
      "STUDENT_ID",
      "PASSPORT",
      "DRIVER_LICENSE",
      "SSN",
      "PAN",
      "AADHAAR",
      "INSURANCE_ID",
      "MEDICAL_RECORD",
    ],
  },
  others: {
    label: "Others",
    icon: CreditCard,
    description: "Financial and miscellaneous information",
    types: [
      "DATE_OF_BIRTH",
      "PHONE",
      "EMAIL",
      "BANK_ACCOUNT",
      "ORG",
      "CREDIT_CARD",
      "ORGANISATIONS",
    ],
  },
};

const getCategoryForPIIType = (type: string): string => {
  for (const [categoryKey, category] of Object.entries(PII_CATEGORIES)) {
    if (category.types.includes(type)) {
      return categoryKey;
    }
  }
  return "others"; // Default fallback
};

export function SimpleMaskingStep({
  detectedPIIData,
  onMaskingComplete,
}: SimpleMaskingStepProps) {
  const [configData, setConfigData] = useState<PIIItem[]>([]);
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [isApplyingMasking, setIsApplyingMasking] = useState(false);
  const [maskingProgress, setMaskingProgress] = useState(0);
  const [maskingResults, setMaskingResults] = useState<any>(null);
  const [showPreview, setShowPreview] = useState(true);
  const [activeTab, setActiveTab] = useState("person");
  const [cleanupCompleted, setCleanupCompleted] = useState(false);
  const { toast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  // Group PII items by category
  const categorizedPII = React.useMemo(() => {
    const grouped: { [key: string]: PIIItem[] } = {};

    // Initialize all categories
    Object.keys(PII_CATEGORIES).forEach((category) => {
      grouped[category] = [];
    });

    // Group items by category
    configData.forEach((item) => {
      const category = getCategoryForPIIType(item.type);
      grouped[category].push(item);
    });

    return grouped;
  }, [configData]);

  // Get counts for each category
  const categoryCounts = React.useMemo(() => {
    const counts: { [key: string]: number } = {};
    Object.keys(PII_CATEGORIES).forEach((category) => {
      counts[category] = categorizedPII[category]?.length || 0;
    });
    return counts;
  }, [categorizedPII]);

  useEffect(() => {
    if (detectedPIIData?.config_data) {
      setConfigData([...detectedPIIData.config_data]);
      // Select all items by default
      setSelectedItems(
        new Set(detectedPIIData.config_data.map((item) => item.id))
      );

      // Set the active tab to the first category that has items
      const firstCategoryWithItems = Object.keys(PII_CATEGORIES).find(
        (categoryKey) => {
          return detectedPIIData.config_data.some(
            (item) => getCategoryForPIIType(item.type) === categoryKey
          );
        }
      );

      if (firstCategoryWithItems) {
        setActiveTab(firstCategoryWithItems);
      }
    }
  }, [detectedPIIData]);

  // Cleanup effect - ensures input data is removed when user navigates away
  useEffect(() => {
    const performCleanup = async () => {
      if (cleanupCompleted || !detectedPIIData?.document_id) return;
      setCleanupCompleted(true);

      try {
        console.log("Performing cleanup on component unmount/navigation");
        await simpleProcessingApi.cleanupProcessingData(
          detectedPIIData.document_id
        );
        console.log("Cleanup completed successfully");
      } catch (error) {
        console.error("Cleanup error during navigation:", error);
      }
    };

    // Handle browser navigation/refresh
    const handleBeforeUnload = () => {
      performCleanup();
    };

    // Handle browser back/forward buttons
    const handlePopState = () => {
      performCleanup();
    };

    // Add event listeners
    window.addEventListener("beforeunload", handleBeforeUnload);
    window.addEventListener("popstate", handlePopState);

    // Cleanup function for component unmount
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
      window.removeEventListener("popstate", handlePopState);
      performCleanup();
    };
  }, [detectedPIIData?.document_id, cleanupCompleted]);

  const handleStrategyChange = (itemId: string, strategy: string) => {
    setConfigData((prev) =>
      prev.map((item) =>
        item.id === itemId ? { ...item, suggested_strategy: strategy } : item
      )
    );
  };

  const handleSelectItem = (itemId: string, selected: boolean) => {
    setSelectedItems((prev) => {
      const newSet = new Set(prev);
      if (selected) {
        newSet.add(itemId);
      } else {
        newSet.delete(itemId);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    if (selectedItems.size === configData.length) {
      setSelectedItems(new Set());
    } else {
      setSelectedItems(new Set(configData.map((item) => item.id)));
    }
  };

  const handleSelectCategory = (category: string) => {
    const categoryItems = categorizedPII[category] || [];
    const categoryIds = new Set(categoryItems.map((item) => item.id));

    // Check if all items in category are selected
    const allSelected = categoryItems.every((item) =>
      selectedItems.has(item.id)
    );

    setSelectedItems((prev) => {
      const newSet = new Set(prev);
      if (allSelected) {
        // Deselect all items in category
        categoryIds.forEach((id) => newSet.delete(id));
      } else {
        // Select all items in category
        categoryIds.forEach((id) => newSet.add(id));
      }
      return newSet;
    });
  };

  const getCategorySelectionState = (category: string) => {
    const categoryItems = categorizedPII[category] || [];
    if (categoryItems.length === 0) return "none";

    const selectedInCategory = categoryItems.filter((item) =>
      selectedItems.has(item.id)
    ).length;

    if (selectedInCategory === 0) return "none";
    if (selectedInCategory === categoryItems.length) return "all";
    return "partial";
  };

  const renderPIIItems = (items: PIIItem[]) => {
    if (items.length === 0) {
      return (
        <div className="text-center py-8 text-muted-foreground">
          <p>No PII items found in this category.</p>
        </div>
      );
    }

    return (
      <div className="space-y-2">
        {items.map((item) => (
          <div
            key={item.id}
            className={`p-4 border rounded-lg transition-colors ${
              selectedItems.has(item.id)
                ? "bg-blue-50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-800"
                : "hover:bg-gray-50 dark:hover:bg-gray-800"
            }`}
          >
            <div className="flex items-start space-x-4">
              <input
                type="checkbox"
                checked={selectedItems.has(item.id)}
                onChange={(e) => handleSelectItem(item.id, e.target.checked)}
                className="mt-1"
              />
              <div className="flex-1 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="font-medium">
                      {getTypeDisplayName(item.type)}
                    </span>
                    <Badge
                      variant={getSeverityColor(item.severity) as any}
                      className="text-xs"
                    >
                      {item.severity}
                    </Badge>
                  </div>
                  <span className="text-sm text-muted-foreground">
                    {item.location}
                  </span>
                </div>
                <p className="text-sm font-mono bg-gray-100 dark:bg-gray-800 p-2 rounded">
                  {item.text}
                </p>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-muted-foreground">
                    Strategy:
                  </span>
                  <Select
                    value={item.suggested_strategy}
                    onValueChange={(value) =>
                      handleStrategyChange(item.id, value)
                    }
                    disabled={!selectedItems.has(item.id)}
                  >
                    <SelectTrigger className="w-40">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {maskingStrategies.map((strategy) => (
                        <SelectItem key={strategy.value} value={strategy.value}>
                          <div>
                            <div className="font-medium">{strategy.label}</div>
                            <div className="text-xs text-muted-foreground">
                              {strategy.description}
                            </div>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  const handleApplyMasking = async () => {
    if (selectedItems.size === 0) {
      toast({
        title: "No items selected",
        description: "Please select at least one PII item to mask.",
        variant: "destructive",
      });
      return;
    }

    setIsApplyingMasking(true);
    setMaskingProgress(0);

    try {
      // Filter only selected items and prepare config data
      const selectedConfigData = configData.filter((item) =>
        selectedItems.has(item.id)
      );

      // Update configuration on server
      await simpleProcessingApi.updateConfig(
        detectedPIIData.document_id,
        selectedConfigData
      );

      // Simulate progress for better UX
      const progressInterval = setInterval(() => {
        setMaskingProgress((prev) => Math.min(prev + 3, 90));
      }, 200);

      // Apply masking
      console.log(
        "Applying PII masking for document:",
        detectedPIIData.document_id
      );
      const response = await simpleProcessingApi.applyMasking(
        detectedPIIData.document_id
      );

      clearInterval(progressInterval);
      setMaskingProgress(100);

      if (response.status === "success" && response.data) {
        console.log("PII masking completed:", response.data);

        setMaskingResults({
          ...response.data,
          masked_items: selectedConfigData.length,
          original_document_id: detectedPIIData.document_id,
        });

        toast({
          title: "Masking Complete",
          description: `Successfully masked ${selectedConfigData.length} PII items.`,
        });

        // Notify parent component
        onMaskingComplete(response.data);
      } else {
        throw new Error(response.error?.message || "Masking failed");
      }
    } catch (error) {
      console.error("Masking error:", error);
      setMaskingProgress(100);

      toast({
        title: "Masking Failed",
        description:
          error instanceof Error
            ? error.message
            : "An error occurred during PII masking.",
        variant: "destructive",
      });
    } finally {
      setIsApplyingMasking(false);
    }
  };

  const handleDownload = async () => {
    if (!maskingResults) return;

    try {
      // Try downloading from local storage first, then fallback to MongoDB
      let blob;
      try {
        blob = await simpleProcessingApi.downloadMaskedDocument(
          maskingResults.masked_document_id || maskingResults.document_id
        );
      } catch (localError) {
        console.log("Local download failed, trying MongoDB:", localError);
        // Fallback to MongoDB download
        blob = await simpleProcessingApi.downloadFromMongo(
          maskingResults.document_id,
          "masked"
        );
      }

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = maskingResults.output_filename || "masked_document.pdf";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast({
        title: "Download Started",
        description: "Your masked document is being downloaded.",
      });
    } catch (error) {
      console.error("Download error:", error);
      toast({
        title: "Download Failed",
        description: "Failed to download the masked document.",
        variant: "destructive",
      });
    }
  };

  const handleReturnToDashboard = async () => {
    // Check if cleanup already completed
    if (cleanupCompleted) {
      navigate("/dashboard");
      return;
    }

    try {
      // Mark cleanup as completed to prevent duplicate calls
      setCleanupCompleted(true);

      // Call cleanup endpoint to remove input data and config files
      const cleanupResponse = await simpleProcessingApi.cleanupProcessingData(
        detectedPIIData.document_id
      );

      console.log("Cleanup completed:", cleanupResponse);

      // Show success message
      toast({
        title: "Processing Complete",
        description:
          "Input data has been securely removed. Only masked data is retained.",
      });
    } catch (error) {
      console.error("Cleanup error:", error);
      // Still navigate but show warning
      toast({
        title: "Warning",
        description:
          "There was an issue cleaning up temporary files. Please contact support if this persists.",
        variant: "destructive",
      });
    } finally {
      // Always navigate to dashboard regardless of cleanup result
      navigate("/dashboard");
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "high":
        return "destructive";
      case "medium":
        return "secondary";
      default:
        return "outline";
    }
  };

  const getTypeDisplayName = (type: string): string => {
    const typeMap: { [key: string]: string } = {
      PERSON: "Person Name",
      ORG: "Organization",
      LOC: "Location",
      EMAIL: "Email Address",
      PHONE: "Phone Number",
      SSN: "Social Security Number",
      CREDIT_CARD: "Credit Card",
      DATE_OF_BIRTH: "Date of Birth",
      ADDRESS: "Address",
      PASSPORT: "Passport Number",
      DRIVER_LICENSE: "Driver License",
      BANK_ACCOUNT: "Bank Account",
    };
    return typeMap[type] || type;
  };

  if (!detectedPIIData || configData.length === 0) {
    return (
      <div className="text-center space-y-4">
        <p className="text-muted-foreground">
          No PII data available for masking.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {isApplyingMasking && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center space-y-4"
        >
          <div className="mx-auto w-16 h-16 bg-purple-100 dark:bg-purple-900/20 rounded-full flex items-center justify-center">
            <Wand2 className="w-8 h-8 text-purple-600 dark:text-purple-400" />
          </div>
          <h2 className="text-2xl font-semibold">Configure PII Masking</h2>
          <p className="text-muted-foreground max-w-md mx-auto">
            Review and configure how each PII item should be masked. You can
            select different strategies for different types of data.
          </p>
        </motion.div>
      )}

      {/* Masking Progress */}
      {isApplyingMasking && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          <div className="text-center">
            <p className="font-medium">Applying PII masking...</p>
            <p className="text-sm text-muted-foreground">
              Processing {selectedItems.size} PII items
            </p>
          </div>
          <Progress value={maskingProgress} className="w-full" />
        </motion.div>
      )}

      {/* Masking Results */}
      {maskingResults && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Success Header */}
          <Card className="border-green-200 dark:border-green-800">
            <CardHeader>
              <div className="flex items-center space-x-4">
                <div className="w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                  <CheckCircle
                    size={32}
                    className="text-green-600 dark:text-green-400"
                  />
                </div>
                <div className="flex-1">
                  <CardTitle className="text-xl text-green-700 dark:text-green-400">
                    PII Masking Complete!
                  </CardTitle>
                  <p className="text-sm text-muted-foreground mt-1">
                    Your document has been successfully processed and all
                    selected PII has been masked.
                  </p>
                </div>
                <Button
                  onClick={handleDownload}
                  size="lg"
                  className="bg-green-600 hover:bg-green-700"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Download Masked PDF
                </Button>
              </div>
            </CardHeader>
          </Card>

          {/* Processing Stats */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <FileText className="w-5 h-5 mr-2" />
                Processing Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                    {maskingResults.masked_items || selectedItems.size}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    PII Items Masked
                  </div>
                </div>
                <div className="text-center p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                    {maskingResults.file_size
                      ? Math.round(maskingResults.file_size / 1024)
                      : "Unknown"}{" "}
                    KB
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Processed File Size
                  </div>
                </div>
                <div className="text-center p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                  <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                    100%
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Success Rate
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Document Comparison */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Eye className="w-5 h-5 mr-2" />
                Document Comparison
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                Compare your original document with the masked version side by
                side.
              </p>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Original Document */}
                <div className="space-y-3">
                  <h4 className="font-semibold text-center">
                    Original Document
                  </h4>
                  <div className="border rounded-lg p-2 bg-gray-50 dark:bg-gray-800">
                    <iframe
                      src={simpleProcessingApi.getPreviewUrl(
                        detectedPIIData.document_id
                      )}
                      className="w-full h-96 border rounded"
                      title="Original Document Preview"
                    />
                  </div>
                </div>

                {/* Masked Document */}
                <div className="space-y-3">
                  <h4 className="font-semibold text-center">Masked Document</h4>
                  <div className="border rounded-lg p-2 bg-gray-50 dark:bg-gray-800">
                    <iframe
                      src={simpleProcessingApi.getMaskedPreviewUrl(
                        detectedPIIData.document_id
                      )}
                      className="w-full h-96 border rounded"
                      title="Masked Document Preview"
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Processing Complete - Return to Dashboard */}
          <Card className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20">
            <CardContent className="text-center py-8">
              <div className="space-y-4">
                <div className="w-20 h-20 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center mx-auto">
                  <CheckCircle
                    size={40}
                    className="text-blue-600 dark:text-blue-400"
                  />
                </div>
                <div>
                  <h3 className="text-xl font-semibold mb-2">
                    Processing Complete!
                  </h3>
                  <p className="text-muted-foreground mb-6">
                    Your document has been successfully processed and all PII
                    has been masked according to your specifications.
                  </p>
                </div>
                <div className="flex items-center justify-center space-x-4">
                  <Button onClick={handleDownload} variant="outline" size="lg">
                    <Download className="w-4 h-4 mr-2" />
                    Download Again
                  </Button>
                  <Button
                    onClick={handleReturnToDashboard}
                    size="lg"
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    <Home className="w-4 h-4 mr-2" />
                    Return to Dashboard
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* PII Configuration with Tabs */}
      {showPreview && !maskingResults && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="space-y-4"
        >
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">PII Items Configuration</h3>
            <Button variant="outline" size="sm" onClick={handleSelectAll}>
              {selectedItems.size === configData.length ? (
                <>
                  <Square className="w-4 h-4 mr-2" />
                  Deselect All
                </>
              ) : (
                <>
                  <CheckSquare className="w-4 h-4 mr-2" />
                  Select All
                </>
              )}
            </Button>
          </div>

          <Card>
            <CardContent className="p-6">
              <Tabs
                value={activeTab}
                onValueChange={setActiveTab}
                className="w-full"
              >
                <TabsList className="grid w-full grid-cols-5">
                  {Object.entries(PII_CATEGORIES).map(
                    ([categoryKey, category]) => {
                      const Icon = category.icon;
                      const count = categoryCounts[categoryKey];
                      const selectionState =
                        getCategorySelectionState(categoryKey);

                      return (
                        <TabsTrigger
                          key={categoryKey}
                          value={categoryKey}
                          className="flex items-center space-x-2 relative"
                        >
                          <Icon className="w-4 h-4" />
                          <span className="hidden sm:inline">
                            {category.label}
                          </span>
                          <Badge
                            variant="secondary"
                            className={`text-xs ${
                              selectionState === "all"
                                ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                                : selectionState === "partial"
                                ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300"
                                : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                            }`}
                          >
                            {count}
                          </Badge>
                        </TabsTrigger>
                      );
                    }
                  )}
                </TabsList>

                {Object.entries(PII_CATEGORIES).map(
                  ([categoryKey, category]) => (
                    <TabsContent
                      key={categoryKey}
                      value={categoryKey}
                      className="space-y-4 mt-6"
                    >
                      <div className="flex items-center justify-between">
                        <div className="space-y-1">
                          <h4 className="text-lg font-semibold flex items-center">
                            <category.icon className="w-5 h-5 mr-2" />
                            {category.label}
                          </h4>
                          <p className="text-sm text-muted-foreground">
                            {category.description}
                          </p>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Badge variant="outline" className="text-sm">
                            {categoryCounts[categoryKey]} items
                          </Badge>
                          {categoryCounts[categoryKey] > 0 && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleSelectCategory(categoryKey)}
                            >
                              {getCategorySelectionState(categoryKey) ===
                              "all" ? (
                                <>
                                  <Square className="w-4 h-4 mr-2" />
                                  Deselect All
                                </>
                              ) : (
                                <>
                                  <CheckSquare className="w-4 h-4 mr-2" />
                                  Select All
                                </>
                              )}
                            </Button>
                          )}
                        </div>
                      </div>

                      <div className="border rounded-lg">
                        <div className="p-4">
                          {renderPIIItems(categorizedPII[categoryKey] || [])}
                        </div>
                      </div>
                    </TabsContent>
                  )
                )}
              </Tabs>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Action Button */}
      {!maskingResults && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="flex justify-center pt-4"
        >
          <Button
            onClick={handleApplyMasking}
            disabled={isApplyingMasking || selectedItems.size === 0}
            className="px-8"
            size="lg"
          >
            <Wand2 className="w-4 h-4 mr-2" />
            Apply Masking ({selectedItems.size} items)
          </Button>
        </motion.div>
      )}
    </div>
  );
}
