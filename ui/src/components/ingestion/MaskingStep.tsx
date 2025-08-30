import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Wand2,
  CheckSquare,
  Square,
  FileText,
  AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { mockPIIDetections, mockMaskingOptions } from "@/data/mockData";
import { PIIDetection } from "@/types";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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

interface MaskingStepProps {
  onMaskPII: () => void;
}

interface MaskingSelection {
  [key: string]: string;
}

const generateMockPIIForDocument = (
  documentId: string,
  documentName: string
): PIIDetection[] => {
  return mockPIIDetections.map((detection, index) => ({
    ...detection,
    id: `${documentId}-${detection.id}`,
    location: `${documentName}, Page ${
      Math.floor(Math.random() * 3) + 1
    }, Line ${Math.floor(Math.random() * 20) + 1}`,
  }));
};

export function MaskingStep({ onMaskPII }: MaskingStepProps) {
  const [documents, setDocuments] = useState<DocumentData[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedMaskingOptions, setSelectedMaskingOptions] =
    useState<MaskingSelection>({});
  const [selectedItems, setSelectedItems] = useState<{
    [documentId: string]: string[];
  }>({});
  const [activeDocument, setActiveDocument] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    const fetchDocuments = async () => {
      try {
        setLoading(true);
        const response = await documentsApi.list();
        const docs = response.data?.documents || [];
        setDocuments(docs);

        // Set active document to first one
        if (docs.length > 0) {
          setActiveDocument(docs[0].id);
        }
      } catch (error) {
        console.error("Failed to fetch documents:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchDocuments();
  }, []);

  useEffect(() => {
    if (documents.length > 0) {
      const defaultMaskingOptions: MaskingSelection = {};
      documents.forEach((doc) => {
        const documentPII = generateMockPIIForDocument(doc.id, doc.name);
        documentPII.forEach((pii) => {
          defaultMaskingOptions[pii.id] = "redact";
        });
      });
      setSelectedMaskingOptions(defaultMaskingOptions);

      if (!activeDocument && documents[0]) {
        setActiveDocument(documents[0].id);
      }
    }
  }, [documents, activeDocument]);

  const handleMaskingOptionChange = (piiId: string, optionId: string) => {
    setSelectedMaskingOptions((prev) => ({
      ...prev,
      [piiId]: optionId,
    }));
  };

  const handleItemSelect = (documentId: string, piiId: string) => {
    setSelectedItems((prev) => ({
      ...prev,
      [documentId]: prev[documentId]?.includes(piiId)
        ? prev[documentId].filter((id) => id !== piiId)
        : [...(prev[documentId] || []), piiId],
    }));
  };

  const handleSelectAllForDocument = (documentId: string) => {
    const documentPII = generateMockPIIForDocument(
      documentId,
      documents.find((doc) => doc.id === documentId)?.name || ""
    );
    const currentlySelected = selectedItems[documentId] || [];

    setSelectedItems((prev) => ({
      ...prev,
      [documentId]:
        currentlySelected.length === documentPII.length
          ? []
          : documentPII.map((item) => item.id),
    }));
  };

  const applyBatchMasking = (documentId: string, optionId: string) => {
    const selectedForDoc = selectedItems[documentId] || [];
    const updates: MaskingSelection = {};
    selectedForDoc.forEach((itemId) => {
      updates[itemId] = optionId;
    });
    setSelectedMaskingOptions((prev) => ({ ...prev, ...updates }));
  };

  const handleBulkMask = async () => {
    setIsProcessing(true);
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 2000));
    setIsProcessing(false);
    onMaskPII();
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
      {/* Document Tabs and PII List */}
      <motion.div
        className="neumorphic-card p-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
      >
        <Card className="border-0 shadow-none bg-transparent">
          <CardHeader className="px-0 pb-4">
            <CardTitle className="flex items-center">
              <AlertTriangle size={20} className="mr-2 text-warning" />
              Detected PII by Document
            </CardTitle>
          </CardHeader>
          <CardContent className="px-0">
            <Tabs value={activeDocument} onValueChange={setActiveDocument}>
              <TabsList
                className={`grid w-full mb-6 ${
                  documents.length <= 2
                    ? "grid-cols-2"
                    : documents.length <= 3
                    ? "grid-cols-3"
                    : "grid-cols-4"
                }`}
              >
                {documents.slice(0, 4).map((doc) => {
                  const documentPII = generateMockPIIForDocument(
                    doc.id,
                    doc.name
                  );
                  return (
                    <TabsTrigger
                      key={doc.id}
                      value={doc.id}
                      className="flex items-center space-x-2 text-xs"
                    >
                      <FileText size={14} />
                      <span className="truncate max-w-[100px]">
                        {doc.name.length > 15
                          ? `${doc.name.substring(0, 15)}...`
                          : doc.name}
                      </span>
                      <Badge variant="secondary" className="text-xs">
                        {documentPII.length}
                      </Badge>
                    </TabsTrigger>
                  );
                })}
              </TabsList>

              {documents.map((doc) => {
                const documentPII = generateMockPIIForDocument(
                  doc.id,
                  doc.name
                );
                const selectedForDoc = selectedItems[doc.id] || [];

                return (
                  <TabsContent key={doc.id} value={doc.id} className="mt-0">
                    {/* Batch Actions */}
                    <div className="neumorphic-flat p-4 rounded-xl mb-6">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center space-x-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleSelectAllForDocument(doc.id)}
                            className="neumorphic-button"
                          >
                            {selectedForDoc.length === documentPII.length ? (
                              <CheckSquare size={16} className="mr-2" />
                            ) : (
                              <Square size={16} className="mr-2" />
                            )}
                            {selectedForDoc.length === documentPII.length
                              ? "Deselect All"
                              : "Select All"}
                          </Button>
                          <span className="text-sm text-muted-foreground">
                            {selectedForDoc.length} of {documentPII.length}{" "}
                            selected
                          </span>
                        </div>
                      </div>

                      {selectedForDoc.length > 0 && (
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
                                  applyBatchMasking(doc.id, option.id)
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
                      {documentPII.map((detection) => {
                        const isSelected = selectedForDoc.includes(
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
                                  handleItemSelect(doc.id, detection.id)
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
    </div>
  );
}
