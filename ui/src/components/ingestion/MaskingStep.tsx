import { useState } from 'react';
import { motion } from 'framer-motion';
import { Eye, EyeOff, Download, Wand2, CheckSquare, Square } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { mockPIIDetections, mockMaskingOptions } from '@/data/mockData';
import { PIIDetection, MaskingOption } from '@/types';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface MaskingSelection {
  [key: string]: string;
}

export function MaskingStep() {
  const [selectedMaskingOptions, setSelectedMaskingOptions] = useState<MaskingSelection>({});
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [previewMode, setPreviewMode] = useState<'before' | 'after'>('before');

  const handleMaskingOptionChange = (piiId: string, optionId: string) => {
    setSelectedMaskingOptions(prev => ({
      ...prev,
      [piiId]: optionId
    }));
  };

  const handleItemSelect = (piiId: string) => {
    setSelectedItems(prev => 
      prev.includes(piiId) 
        ? prev.filter(id => id !== piiId)
        : [...prev, piiId]
    );
  };

  const handleSelectAll = () => {
    if (selectedItems.length === mockPIIDetections.length) {
      setSelectedItems([]);
    } else {
      setSelectedItems(mockPIIDetections.map(item => item.id));
    }
  };

  const applyBatchMasking = (optionId: string) => {
    const updates: MaskingSelection = {};
    selectedItems.forEach(itemId => {
      updates[itemId] = optionId;
    });
    setSelectedMaskingOptions(prev => ({ ...prev, ...updates }));
  };

  const getMaskedValue = (detection: PIIDetection, optionId?: string) => {
    if (!optionId) return detection.extractedValue;
    
    switch (optionId) {
      case 'substitution':
        if (detection.type === 'Email Address') return 'jane.smith@email.com';
        if (detection.type === 'Phone Number') return '(555) 987-6543';
        if (detection.type === 'Social Security Number') return '***-**-5678';
        if (detection.type === 'Credit Card Number') return '****-****-****-5678';
        if (detection.type === 'Date of Birth') return '03/22/1990';
        return 'SUBSTITUTED_VALUE';
      case 'redaction':
        return '[REDACTED]';
      case 'partial':
        if (detection.type === 'Email Address') return 'j***.***@email.com';
        if (detection.type === 'Phone Number') return '(***) ***-4567';
        if (detection.type === 'Social Security Number') return '***-**-****';
        if (detection.type === 'Credit Card Number') return '****-****-****-1234';
        return detection.extractedValue.slice(0, 2) + '*'.repeat(detection.extractedValue.length - 4) + detection.extractedValue.slice(-2);
      default:
        return detection.extractedValue;
    }
  };

  return (
    <motion.div
      className="space-y-6"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Header */}
      <div className="neumorphic-card p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-xl font-semibold text-foreground">
              Data Masking & Protection
            </h3>
            <p className="text-muted-foreground">
              AI Agent 3 applies intelligent masking strategies to protect sensitive data
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPreviewMode(previewMode === 'before' ? 'after' : 'before')}
              className="neumorphic-button"
            >
              {previewMode === 'before' ? <Eye size={16} /> : <EyeOff size={16} />}
              <span className="ml-2">
                {previewMode === 'before' ? 'Show Masked' : 'Show Original'}
              </span>
            </Button>
            <Button className="neumorphic-button">
              <Download size={16} className="mr-2" />
              Export Preview
            </Button>
          </div>
        </div>

        {/* Batch Actions */}
        <div className="flex items-center justify-between p-4 neumorphic-flat rounded-xl">
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleSelectAll}
              className="neumorphic-button"
            >
              {selectedItems.length === mockPIIDetections.length ? (
                <CheckSquare size={16} />
              ) : (
                <Square size={16} />
              )}
              <span className="ml-2">
                {selectedItems.length === mockPIIDetections.length ? 'Deselect All' : 'Select All'}
              </span>
            </Button>
            <span className="text-sm text-muted-foreground">
              {selectedItems.length} of {mockPIIDetections.length} items selected
            </span>
          </div>
          
          {selectedItems.length > 0 && (
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-foreground">Batch Apply:</span>
              {mockMaskingOptions.map((option) => (
                <Button
                  key={option.id}
                  variant="outline"
                  size="sm"
                  onClick={() => applyBatchMasking(option.id)}
                  className="neumorphic-button text-xs"
                >
                  <Wand2 size={12} className="mr-1" />
                  {option.name}
                </Button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Masking Table */}
      <div className="neumorphic-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-6 py-4 text-left">
                  <input
                    type="checkbox"
                    checked={selectedItems.length === mockPIIDetections.length}
                    onChange={handleSelectAll}
                    className="rounded"
                  />
                </th>
                <th className="px-6 py-4 text-left text-sm font-medium text-foreground">
                  PII Type
                </th>
                <th className="px-6 py-4 text-left text-sm font-medium text-foreground">
                  {previewMode === 'before' ? 'Original Value' : 'Masked Value'}
                </th>
                <th className="px-6 py-4 text-left text-sm font-medium text-foreground">
                  Masking Method
                </th>
                <th className="px-6 py-4 text-left text-sm font-medium text-foreground">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {mockPIIDetections.map((detection, index) => (
                <motion.tr
                  key={detection.id}
                  className="hover:bg-muted/30 transition-colors"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2, delay: index * 0.05 }}
                >
                  <td className="px-6 py-4">
                    <input
                      type="checkbox"
                      checked={selectedItems.includes(detection.id)}
                      onChange={() => handleItemSelect(detection.id)}
                      className="rounded"
                    />
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center space-x-2">
                      <Badge variant="outline" className="text-xs">
                        {detection.type}
                      </Badge>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <code className="neumorphic-pressed px-3 py-1 rounded-lg text-sm bg-muted">
                      {previewMode === 'before' 
                        ? detection.extractedValue 
                        : getMaskedValue(detection, selectedMaskingOptions[detection.id])
                      }
                    </code>
                  </td>
                  <td className="px-6 py-4">
                    <Select
                      value={selectedMaskingOptions[detection.id] || ''}
                      onValueChange={(value) => handleMaskingOptionChange(detection.id, value)}
                    >
                      <SelectTrigger className="neumorphic-input w-48">
                        <SelectValue placeholder="Choose method" />
                      </SelectTrigger>
                      <SelectContent className="neumorphic-card border-0">
                        {mockMaskingOptions.map((option) => (
                          <SelectItem key={option.id} value={option.id}>
                            <div>
                              <div className="font-medium">{option.name}</div>
                              <div className="text-xs text-muted-foreground">
                                {option.description}
                              </div>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </td>
                  <td className="px-6 py-4">
                    <Badge 
                      className={
                        selectedMaskingOptions[detection.id] 
                          ? 'status-success border'
                          : 'status-warning border'
                      }
                    >
                      {selectedMaskingOptions[detection.id] ? 'Ready' : 'Pending'}
                    </Badge>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Masking Options Reference */}
      <div className="neumorphic-card p-6">
        <h4 className="text-lg font-semibold text-foreground mb-4">
          Masking Methods Reference
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {mockMaskingOptions.map((option) => (
            <div key={option.id} className="neumorphic-flat p-4 rounded-xl">
              <h5 className="font-medium text-foreground mb-2">{option.name}</h5>
              <p className="text-sm text-muted-foreground mb-3">{option.description}</p>
              <div className="neumorphic-pressed p-2 rounded-lg">
                <code className="text-xs text-muted-foreground">{option.example}</code>
              </div>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}