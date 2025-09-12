import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Wand2, CheckSquare, Square, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { mockMaskingOptions } from "@/data/mockData";
import { PIIDetection } from "@/types";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { documentsApi, piiApi, maskingApi } from "@/lib/api";
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

interface MaskingStepProps {
  onMaskPII: () => void;
  detectedPIIData?: any;
}

interface MaskingSelection {
  [key: string]: string;
}

// Helper function to group PII items by type
const groupPIIByType = (
  allPII: PIIDetection[]
): Record<string, PIIDetection[]> => {
  return allPII.reduce((groups, pii) => {
    const type = pii.type;
    if (!groups[type]) {
      groups[type] = [];
    }
    groups[type].push(pii);
    return groups;
  }, {} as Record<string, PIIDetection[]>);
};

export function MaskingStep({ onMaskPII, detectedPIIData }: MaskingStepProps) {
  const [documents, setDocuments] = useState<DocumentData[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedMaskingOptions, setSelectedMaskingOptions] =
    useState<MaskingSelection>({});
  const [selectedItems, setSelectedItems] = useState<{
    [piiType: string]: string[];
  }>({});
  const [activePIIType, setActivePIIType] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [configSaved, setConfigSaved] = useState(false);
  const [allPII, setAllPII] = useState<PIIDetection[]>([]);
  const [piiByType, setPiiByType] = useState<Record<string, PIIDetection[]>>(
    {}
  );

  useEffect(() => {
    const fetchDocuments = async () => {
      try {
        setLoading(true);
        const response = await documentsApi.list();
        const docs = response.data?.documents || [];
        setDocuments(docs);

        // Debug logging to understand the data structure
        console.log("Detected PII Data:", detectedPIIData);
        console.log("Documents:", docs);

        // Process PII data directly from detectedPIIData
        // This data should already contain PII for the processed document(s)
        let allPIIItems: PIIDetection[] = [];

        if (detectedPIIData?.pii_items) {
          // Convert the PII data to the expected format
          allPIIItems = detectedPIIData.pii_items.map((pii: any) => ({
            id: pii.id,
            type: pii.type,
            confidence: pii.confidence,
            location:
              pii.location || `Page ${(pii.coordinates?.page || 0) + 1}`,
            extractedValue: pii.text,
            severity: pii.severity || "medium",
          }));
        }

        console.log("Processed PII Items:", allPIIItems);
        console.log(
          "Unique PII IDs:",
          allPIIItems.map((pii) => pii.id)
        );

        setAllPII(allPIIItems);
        const groupedPII = groupPIIByType(allPIIItems);
        setPiiByType(groupedPII);

        console.log("Grouped PII by Type:", groupedPII);

        // Set active PII type to first one
        const firstType = Object.keys(groupedPII)[0];
        if (firstType) {
          setActivePIIType(firstType);
        }
      } catch (error) {
        console.error("Failed to fetch documents:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchDocuments();
  }, [detectedPIIData]);

  useEffect(() => {
    if (allPII.length > 0) {
      const defaultMaskingOptions: MaskingSelection = {};
      allPII.forEach((pii) => {
        defaultMaskingOptions[pii.id] = "redact";
      });
      setSelectedMaskingOptions(defaultMaskingOptions);
    }
  }, [allPII]);

  const handleMaskingOptionChange = (piiId: string, optionId: string) => {
    setSelectedMaskingOptions((prev) => ({
      ...prev,
      [piiId]: optionId,
    }));
  };

  const handleItemSelect = (piiType: string, piiId: string) => {
    setSelectedItems((prev) => ({
      ...prev,
      [piiType]: prev[piiType]?.includes(piiId)
        ? prev[piiType].filter((id) => id !== piiId)
        : [...(prev[piiType] || []), piiId],
    }));
  };
  const handleApplyMasking = async () => {
    setIsProcessing(true);
    try {
      const documentId = documents[0]?.id;
      if (!documentId) {
        throw new Error("No document found");
      }

      const configResponse = await piiApi.saveMaskingConfig(
        documentId,
        selectedMaskingOptions
      );

      if (configResponse.status === "success") {
        console.log("Masking configuration saved:", configResponse.data);
        setConfigSaved(true);

        // Now apply the actual masking
        const maskingResponse = await maskingApi.applyMasking(documentId);

        if (maskingResponse.status === "success") {
          console.log("Masking applied successfully:", maskingResponse.data);
          toast({
            title: "Masking Applied Successfully",
            description: `Masked ${maskingResponse.data?.total_pii_masked} PII items using various strategies`,
          });

          // Move to next step
          onMaskPII();
        }
      }
    } catch (error) {
      console.error("Failed to apply masking:", error);
      toast({
        title: "Masking Failed",
        description: "Failed to apply PII masking. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSelectAllForType = (piiType: string) => {
    const typeItems = piiByType[piiType] || [];
    const currentlySelected = selectedItems[piiType] || [];

    setSelectedItems((prev) => ({
      ...prev,
      [piiType]:
        currentlySelected.length === typeItems.length
          ? []
          : typeItems.map((item) => item.id),
    }));
  };

  const applyBatchMasking = (piiType: string, optionId: string) => {
    const selectedForType = selectedItems[piiType] || [];
    const updates: MaskingSelection = {};
    selectedForType.forEach((piiId) => {
      updates[piiId] = optionId;
    });
    setSelectedMaskingOptions((prev) => ({ ...prev, ...updates }));
  };

  return (
    <div className="space-y-6">
      {/* Document Tabs and PII List */}
      <motion.div
        className="neumorphic-card p-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
      >
        <Card className="border-0 shadow-none bg-transparent">
          <CardHeader className="px-0 pb-4">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center">
                <AlertTriangle size={20} className="mr-2 text-warning" />
                Detected PII by Type
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="px-0">
            <Tabs value={activePIIType} onValueChange={setActivePIIType}>
              <div className="w-full mb-6">
                <TabsList className="inline-flex h-10 items-center justify-start rounded-md bg-muted p-1 text-muted-foreground overflow-x-auto max-w-full">
                  {Object.entries(piiByType).map(([type, items]) => (
                    <TabsTrigger
                      key={type}
                      value={type}
                      className="inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm min-w-fit"
                    >
                      <AlertTriangle size={14} className="mr-1" />
                      <span className="truncate max-w-[120px]">{type}</span>
                      <Badge variant="secondary" className="text-xs ml-1">
                        {items.length}
                      </Badge>
                    </TabsTrigger>
                  ))}
                </TabsList>
              </div>

              {Object.entries(piiByType).map(([type, items]) => {
                const selectedForType = selectedItems[type] || [];

                return (
                  <TabsContent key={type} value={type} className="mt-0">
                    {/* Batch Actions */}
                    <div className="neumorphic-flat p-4 rounded-xl mb-6">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center space-x-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleSelectAllForType(type)}
                            className="neumorphic-button"
                          >
                            {selectedForType.length === items.length ? (
                              <CheckSquare size={16} className="mr-2" />
                            ) : (
                              <Square size={16} className="mr-2" />
                            )}
                            {selectedForType.length === items.length
                              ? "Deselect All"
                              : "Select All"}
                          </Button>
                          <span className="text-sm text-muted-foreground">
                            {selectedForType.length} of {items.length} selected
                          </span>
                        </div>
                      </div>

                      {selectedForType.length > 0 && (
                        <div className="flex items-center space-x-2">
                          <span className="text-sm font-medium">
                            Apply to selected:
                          </span>
                          <div className="flex space-x-1">
                            {mockMaskingOptions.map((option) => (
                              <Button
                                key={option.id}
                                variant="outline"
                                size="sm"
                                onClick={() =>
                                  applyBatchMasking(type, option.id)
                                }
                                className="neumorphic-button text-xs"
                              >
                                <Wand2 size={12} className="mr-1" />
                                {option.name}
                              </Button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* PII Items List */}
                    <div className="space-y-4 max-h-[600px] overflow-y-auto">
                      {items.map((detection) => {
                        const isSelected = selectedForType.includes(
                          detection.id
                        );
                        const maskingOption =
                          selectedMaskingOptions[detection.id] || "redact";

                        return (
                          <motion.div
                            key={detection.id}
                            className={`neumorphic-flat p-4 rounded-xl border transition-all duration-200 ${
                              isSelected
                                ? "border-primary/50 bg-primary/5"
                                : "border-transparent"
                            }`}
                            whileHover={{ scale: 1.01 }}
                          >
                            <div className="flex items-start space-x-4">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() =>
                                  handleItemSelect(type, detection.id)
                                }
                                className="p-1 h-auto mt-1"
                              >
                                {isSelected ? (
                                  <CheckSquare
                                    size={16}
                                    className="text-primary"
                                  />
                                ) : (
                                  <Square
                                    size={16}
                                    className="text-muted-foreground"
                                  />
                                )}
                              </Button>

                              <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between mb-3">
                                  <div className="flex items-center space-x-2">
                                    <Badge
                                      variant={
                                        detection.severity === "high"
                                          ? "destructive"
                                          : "secondary"
                                      }
                                    >
                                      {detection.type}
                                    </Badge>
                                    <Badge
                                      variant="outline"
                                      className="text-xs"
                                    >
                                      {Math.round(detection.confidence * 100)}%
                                      confidence
                                    </Badge>
                                  </div>
                                </div>

                                <div className="space-y-3">
                                  <div className="text-sm">
                                    <span className="text-muted-foreground">
                                      Detected Value:{" "}
                                    </span>
                                    <code className="bg-muted px-2 py-1 rounded text-foreground font-mono">
                                      {detection.extractedValue}
                                    </code>
                                  </div>
                                  <div className="text-xs text-muted-foreground">
                                    📍 {detection.location}
                                  </div>
                                </div>

                                <div className="mt-4">
                                  <label className="text-sm font-medium text-foreground mb-2 block">
                                    Masking Method:
                                  </label>
                                  <Select
                                    value={maskingOption}
                                    onValueChange={(value) =>
                                      handleMaskingOptionChange(
                                        detection.id,
                                        value
                                      )
                                    }
                                  >
                                    <SelectTrigger className="w-full">
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      {mockMaskingOptions.map((option) => (
                                        <SelectItem
                                          key={option.id}
                                          value={option.id}
                                        >
                                          <div className="flex items-center space-x-2">
                                            <span>{option.name}</span>
                                            <Badge
                                              variant="outline"
                                              className="text-xs"
                                            >
                                              {option.description}
                                            </Badge>
                                          </div>
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>

                                  {/* Show example of masking */}
                                  <div className="mt-2 text-xs text-muted-foreground">
                                    <span>Preview: </span>
                                    <code className="bg-muted/50 px-1 py-0.5 rounded">
                                      {mockMaskingOptions.find(
                                        (opt) => opt.id === maskingOption
                                      )?.example || "Example not available"}
                                    </code>
                                  </div>
                                </div>
                              </div>
                            </div>
                          </motion.div>
                        );
                      })}
                    </div>
                  </TabsContent>
                );
              })}
            </Tabs>
          </CardContent>
        </Card>
      </motion.div>

      {/* Apply Masking Section */}
      <motion.div
        className="neumorphic-card p-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.2 }}
      >
        <Card className="border-0 shadow-none bg-transparent">
          <CardHeader className="px-0 pb-4">
            <CardTitle className="flex items-center">
              <Wand2 size={20} className="mr-2 text-primary" />
              Apply PII Masking
            </CardTitle>
          </CardHeader>
          <CardContent className="px-0">
            <div className="space-y-4">
              <div className="neumorphic-flat p-4 rounded-xl">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="text-sm font-medium">
                      Ready to apply masking strategies
                    </p>
                    <p className="text-xs text-muted-foreground">
                      This will create a masked version of your document with
                      the selected strategies applied
                    </p>
                  </div>
                  <Button
                    onClick={handleApplyMasking}
                    disabled={isProcessing || allPII.length === 0}
                    className="neumorphic-button"
                  >
                    {isProcessing ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Processing...
                      </>
                    ) : (
                      <>
                        <Wand2 size={16} className="mr-2" />
                        Apply Masking
                      </>
                    )}
                  </Button>
                </div>
              </div>

              {/* Masking Summary */}
              {Object.keys(selectedMaskingOptions).length > 0 && (
                <div className="neumorphic-flat p-4 rounded-xl">
                  <h4 className="text-sm font-medium mb-3">Masking Summary</h4>
                  <div className="grid grid-cols-3 gap-4 text-xs">
                    {Object.entries(
                      Object.values(selectedMaskingOptions).reduce(
                        (acc, strategy) => {
                          acc[strategy] = (acc[strategy] || 0) + 1;
                          return acc;
                        },
                        {} as Record<string, number>
                      )
                    ).map(([strategy, count]) => (
                      <div key={strategy} className="text-center">
                        <div className="font-medium text-primary">{count}</div>
                        <div className="text-muted-foreground capitalize">
                          {strategy}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
