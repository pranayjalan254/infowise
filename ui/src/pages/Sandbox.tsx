import { useState } from 'react';
import { motion } from 'framer-motion';
import { Play, MessageSquare, Database, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

const mockDocuments = [
  { id: '1', name: 'Customer_Database_Q1.csv', status: 'Masked', records: '1,247', lastModified: '2024-03-15' },
  { id: '2', name: 'Employee_Records_2024.xlsx', status: 'Masked', records: '892', lastModified: '2024-03-14' },
  { id: '3', name: 'Financial_Report_March.pdf', status: 'Masked', records: '2,156', lastModified: '2024-03-13' },
  { id: '4', name: 'Medical_Claims_Data.json', status: 'Masked', records: '1,567', lastModified: '2024-03-12' },
  { id: '5', name: 'Survey_Responses_2024.csv', status: 'Masked', records: '634', lastModified: '2024-03-11' }
];

const mockSyntheticData = [
  { field: 'Name', original: 'John Doe', synthetic: 'Alex Johnson' },
  { field: 'Email', original: 'john.doe@email.com', synthetic: 'alex.johnson@email.com' },
  { field: 'Phone', original: '(555) 123-4567', synthetic: '(555) 987-6543' },
  { field: 'SSN', original: '***-**-****', synthetic: '***-**-****' },
];

export default function Sandbox() {
  const [selectedDocument, setSelectedDocument] = useState('');
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState([
    { type: 'assistant', message: 'Hello! I can help you query your selected dataset. What would you like to know?' }
  ]);

  const handleSendMessage = () => {
    if (!chatInput.trim()) return;
    
    setChatMessages(prev => [
      ...prev,
      { type: 'user', message: chatInput },
      { type: 'assistant', message: 'Based on your cleaned dataset, here are the insights...' }
    ]);
    setChatInput('');
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <h1 className="text-3xl font-bold text-display text-foreground mb-2">
          Sandbox
        </h1>
        <p className="text-muted-foreground">
          Explore insights, generate synthetic data, and query your cleaned datasets
        </p>
      </motion.div>

      {/* Sandbox Tabs */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <Tabs defaultValue="synthetic" className="space-y-6">
          <TabsList className="neumorphic-card grid grid-cols-2 w-full">
            <TabsTrigger value="synthetic" className="neumorphic-button">
              <Database size={16} className="mr-2" />
              Synthetic Generator
            </TabsTrigger>
            <TabsTrigger value="assistant" className="neumorphic-button">
              <MessageSquare size={16} className="mr-2" />
              AI Assistant
            </TabsTrigger>
          </TabsList>


          {/* Synthetic Data Generator */}
          <TabsContent value="synthetic" className="space-y-6">
            <div className="neumorphic-card p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-foreground">
                  Synthetic Data Generator
                </h3>
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-2">
                    <FileText size={16} className="text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">Select Document:</span>
                  </div>
                  <Select value={selectedDocument} onValueChange={setSelectedDocument}>
                    <SelectTrigger className="neumorphic-input w-64">
                      <SelectValue placeholder="Choose a masked document" />
                    </SelectTrigger>
                    <SelectContent className="neumorphic-card">
                      {mockDocuments.map((doc) => (
                        <SelectItem key={doc.id} value={doc.id}>
                          {doc.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              {selectedDocument && (
                <>
                  <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-medium text-foreground">Field</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-foreground">Original Pattern</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-foreground">Synthetic Example</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/50">
                      {mockSyntheticData.map((row, index) => (
                        <motion.tr
                          key={row.field}
                          className="hover:bg-muted/30 transition-colors"
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.2, delay: index * 0.1 }}
                        >
                          <td className="px-4 py-3 font-medium text-foreground">{row.field}</td>
                          <td className="px-4 py-3">
                            <code className="neumorphic-pressed px-2 py-1 rounded text-sm bg-muted">
                              {row.original}
                            </code>
                          </td>
                          <td className="px-4 py-3">
                            <code className="neumorphic-pressed px-2 py-1 rounded text-sm bg-muted">
                              {row.synthetic}
                            </code>
                          </td>
                        </motion.tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                
                <div className="flex justify-between items-center mt-6">
                  <div className="text-sm text-muted-foreground">
                    Generate realistic synthetic data while preserving statistical properties
                  </div>
                  <Button className="neumorphic-button">
                    <Play size={16} className="mr-2" />
                    Generate Full Dataset
                  </Button>
                </div>
                </>
              )}
              
              {!selectedDocument && (
                <div className="text-center py-12">
                  <Database size={48} className="mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">
                    Select a masked document to generate synthetic data
                  </p>
                </div>
              )}
            </div>
          </TabsContent>

          {/* AI Assistant */}
          <TabsContent value="assistant" className="space-y-6">
            <div className="neumorphic-card p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-foreground">
                  AI Assistant
                </h3>
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-2">
                    <FileText size={16} className="text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">Query Document:</span>
                  </div>
                  <Select value={selectedDocument} onValueChange={setSelectedDocument}>
                    <SelectTrigger className="neumorphic-input w-64">
                      <SelectValue placeholder="Choose a masked document" />
                    </SelectTrigger>
                    <SelectContent className="neumorphic-card">
                      {mockDocuments.map((doc) => (
                        <SelectItem key={doc.id} value={doc.id}>
                          {doc.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              {selectedDocument && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Chat Interface */}
                  <div className="space-y-4">
                    <div className="neumorphic-pressed h-80 p-4 rounded-xl overflow-y-auto space-y-3">
                      {chatMessages.map((msg, index) => (
                        <motion.div
                          key={index}
                          className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.3 }}
                        >
                          <div className={`max-w-[80%] p-3 rounded-xl ${
                            msg.type === 'user' 
                              ? 'neumorphic-raised bg-primary text-primary-foreground' 
                              : 'neumorphic-flat bg-surface'
                          }`}>
                            <p className="text-sm">{msg.message}</p>
                          </div>
                        </motion.div>
                      ))}
                    </div>
                    
                    <div className="flex space-x-2">
                      <Input
                        placeholder="Ask questions about your data..."
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                        className="neumorphic-input flex-1"
                        disabled={!selectedDocument}
                      />
                      <Button 
                        onClick={handleSendMessage} 
                        className="neumorphic-button"
                        disabled={!selectedDocument}
                      >
                        <MessageSquare size={16} />
                      </Button>
                    </div>
                  </div>

                  {/* Query Examples */}
                  <div className="space-y-4">
                    <h4 className="font-medium text-foreground">Example Queries</h4>
                    {[
                      "How many records contain sensitive data?",
                      "Show me the distribution of masked PII types",
                      "What's the data quality score for this document?",
                      "Generate a summary of masked fields",
                      "Compare original vs masked data patterns"
                    ].map((query, index) => (
                      <motion.button
                        key={index}
                        className="neumorphic-button w-full p-3 rounded-xl text-left text-sm text-muted-foreground hover:text-foreground"
                        onClick={() => setChatInput(query)}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.3, delay: index * 0.1 }}
                      >
                        {query}
                      </motion.button>
                    ))}
                  </div>
                </div>
              )}
              
              {!selectedDocument && (
                <div className="text-center py-12">
                  <MessageSquare size={48} className="mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">
                    Select a masked document to start querying your data
                  </p>
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </motion.div>
    </div>
  );
}