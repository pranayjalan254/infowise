import { useState } from 'react';
import { motion } from 'framer-motion';
import { Save, User, Shield, Bell, Database, Key, Globe, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { mockMaskingOptions } from '@/data/mockData';

const teamMembers = [
  { id: '1', name: 'Sarah Johnson', email: 'sarah.j@company.com', role: 'Admin', status: 'active' },
  { id: '2', name: 'Michael Chen', email: 'michael.c@company.com', role: 'Analyst', status: 'active' },
  { id: '3', name: 'Emily Davis', email: 'emily.d@company.com', role: 'Reviewer', status: 'pending' },
  { id: '4', name: 'James Wilson', email: 'james.w@company.com', role: 'Analyst', status: 'active' }
];

export default function Settings() {
  const [notifications, setNotifications] = useState({
    emailAlerts: true,
    complianceUpdates: true,
    riskNotifications: true,
    weeklyReports: false
  });

  const [defaultMaskingStrategies, setDefaultMaskingStrategies] = useState({
    'Social Security Number': 'redaction',
    'Email Address': 'partial',
    'Phone Number': 'partial',
    'Credit Card Number': 'partial',
    'Date of Birth': 'substitution'
  });

  const handleNotificationChange = (key: string, value: boolean) => {
    setNotifications(prev => ({ ...prev, [key]: value }));
  };

  const handleMaskingStrategyChange = (piiType: string, strategy: string) => {
    setDefaultMaskingStrategies(prev => ({ ...prev, [piiType]: strategy }));
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
          Settings
        </h1>
        <p className="text-muted-foreground">
          Configure your privacy platform preferences and policies
        </p>
      </motion.div>

      {/* Settings Tabs */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <Tabs defaultValue="general" className="space-y-6">
          <TabsList className="neumorphic-card grid grid-cols-5 w-full">
            <TabsTrigger value="general" className="neumorphic-button">
              <User size={16} className="mr-2" />
              General
            </TabsTrigger>
            <TabsTrigger value="team" className="neumorphic-button">
              <User size={16} className="mr-2" />
              Team
            </TabsTrigger>
            <TabsTrigger value="policies" className="neumorphic-button">
              <Shield size={16} className="mr-2" />
              Policies
            </TabsTrigger>
            <TabsTrigger value="notifications" className="neumorphic-button">
              <Bell size={16} className="mr-2" />
              Notifications
            </TabsTrigger>
            <TabsTrigger value="integrations" className="neumorphic-button">
              <Globe size={16} className="mr-2" />
              Integrations
            </TabsTrigger>
          </TabsList>

          {/* General Settings */}
          <TabsContent value="general" className="space-y-6">
            <div className="neumorphic-card p-6">
              <h3 className="text-lg font-semibold text-foreground mb-4">
                Organization Settings
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="org-name">Organization Name</Label>
                    <Input 
                      id="org-name" 
                      defaultValue="Acme Corporation" 
                      className="neumorphic-input mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="industry">Industry</Label>
                    <Input 
                      id="industry" 
                      defaultValue="Financial Services" 
                      className="neumorphic-input mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="data-officer">Data Protection Officer</Label>
                    <Input 
                      id="data-officer" 
                      defaultValue="Jane Smith" 
                      className="neumorphic-input mt-1"
                    />
                  </div>
                </div>
                
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="primary-location">Primary Location</Label>
                    <Input 
                      id="primary-location" 
                      defaultValue="United States" 
                      className="neumorphic-input mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="retention-period">Data Retention Period</Label>
                    <Input 
                      id="retention-period" 
                      defaultValue="7 years" 
                      className="neumorphic-input mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="contact-email">Contact Email</Label>
                    <Input 
                      id="contact-email" 
                      defaultValue="privacy@acmecorp.com" 
                      className="neumorphic-input mt-1"
                    />
                  </div>
                </div>
              </div>
              
              <div className="flex justify-end mt-6">
                <Button className="neumorphic-button">
                  <Save size={16} className="mr-2" />
                  Save Changes
                </Button>
              </div>
            </div>
          </TabsContent>

          {/* Team Management */}
          <TabsContent value="team" className="space-y-6">
            <div className="neumorphic-card p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-foreground">
                  Team Members
                </h3>
                <Button className="neumorphic-button">
                  <User size={16} className="mr-2" />
                  Invite Member
                </Button>
              </div>
              
              <div className="space-y-3">
                {teamMembers.map((member, index) => (
                  <motion.div
                    key={member.id}
                    className="neumorphic-flat p-4 rounded-xl"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: index * 0.1 }}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 neumorphic-raised rounded-full flex items-center justify-center bg-primary">
                          <span className="text-primary-foreground font-medium text-sm">
                            {member.name.split(' ').map(n => n[0]).join('')}
                          </span>
                        </div>
                        <div>
                          <h4 className="font-medium text-foreground">{member.name}</h4>
                          <p className="text-sm text-muted-foreground">{member.email}</p>
                        </div>
                      </div>
                      
                      <div className="flex items-center space-x-3">
                        <Badge 
                          className={`${
                            member.status === 'active' ? 'status-success border' : 'status-warning border'
                          }`}
                        >
                          {member.status}
                        </Badge>
                        <Badge variant="outline" className="border-primary text-primary">
                          {member.role}
                        </Badge>
                        <Button 
                          size="sm" 
                          variant="ghost" 
                          className="neumorphic-button text-danger"
                        >
                          <Trash2 size={14} />
                        </Button>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </TabsContent>

          {/* Policy Configuration */}
          <TabsContent value="policies" className="space-y-6">
            <div className="neumorphic-card p-6">
              <h3 className="text-lg font-semibold text-foreground mb-4">
                Default Masking Strategies
              </h3>
              
              <div className="space-y-4">
                {Object.entries(defaultMaskingStrategies).map(([piiType, strategy], index) => (
                  <motion.div
                    key={piiType}
                    className="neumorphic-flat p-4 rounded-xl"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, delay: index * 0.1 }}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium text-foreground">{piiType}</h4>
                        <p className="text-sm text-muted-foreground">
                          Default masking method for {piiType.toLowerCase()}
                        </p>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        {mockMaskingOptions.map((option) => (
                          <Button
                            key={option.id}
                            size="sm"
                            variant={strategy === option.id ? "default" : "outline"}
                            onClick={() => handleMaskingStrategyChange(piiType, option.id)}
                            className={strategy === option.id ? "neumorphic-pressed" : "neumorphic-button"}
                          >
                            {option.name}
                          </Button>
                        ))}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>

            <div className="neumorphic-card p-6">
              <h3 className="text-lg font-semibold text-foreground mb-4">
                Compliance Frameworks
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  { name: 'GDPR', enabled: true, description: 'European Union General Data Protection Regulation' },
                  { name: 'HIPAA', enabled: true, description: 'Health Insurance Portability and Accountability Act' },
                  { name: 'DPDPA', enabled: false, description: 'Digital Personal Data Protection Act (India)' },
                  { name: 'GLBA', enabled: true, description: 'Gramm-Leach-Bliley Act' }
                ].map((framework, index) => (
                  <motion.div
                    key={framework.name}
                    className="neumorphic-flat p-4 rounded-xl"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.3, delay: index * 0.1 }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium text-foreground">{framework.name}</h4>
                      <Switch checked={framework.enabled} />
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {framework.description}
                    </p>
                  </motion.div>
                ))}
              </div>
            </div>
          </TabsContent>

          {/* Notifications */}
          <TabsContent value="notifications" className="space-y-6">
            <div className="neumorphic-card p-6">
              <h3 className="text-lg font-semibold text-foreground mb-4">
                Notification Preferences
              </h3>
              
              <div className="space-y-6">
                {[
                  { 
                    key: 'emailAlerts', 
                    title: 'Email Alerts', 
                    description: 'Receive email notifications for critical events'
                  },
                  { 
                    key: 'complianceUpdates', 
                    title: 'Compliance Updates', 
                    description: 'Get notified about regulation changes and updates'
                  },
                  { 
                    key: 'riskNotifications', 
                    title: 'Risk Notifications', 
                    description: 'Alerts for high-risk PII detections and compliance issues'
                  },
                  { 
                    key: 'weeklyReports', 
                    title: 'Weekly Reports', 
                    description: 'Automated weekly summary reports'
                  }
                ].map((setting, index) => (
                  <motion.div
                    key={setting.key}
                    className="neumorphic-flat p-4 rounded-xl"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: index * 0.1 }}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium text-foreground">{setting.title}</h4>
                        <p className="text-sm text-muted-foreground">{setting.description}</p>
                      </div>
                      <Switch 
                        checked={notifications[setting.key as keyof typeof notifications]}
                        onCheckedChange={(value) => handleNotificationChange(setting.key, value)}
                      />
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </TabsContent>

          {/* Integrations */}
          <TabsContent value="integrations" className="space-y-6">
            <div className="neumorphic-card p-6">
              <h3 className="text-lg font-semibold text-foreground mb-4">
                External Integrations
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  { name: 'Slack', icon: '💬', status: 'connected', description: 'Team notifications' },
                  { name: 'Microsoft Teams', icon: '👥', status: 'available', description: 'Team collaboration' },
                  { name: 'Jira', icon: '📋', status: 'connected', description: 'Issue tracking' },
                  { name: 'ServiceNow', icon: '🛠️', status: 'available', description: 'IT service management' },
                  { name: 'AWS S3', icon: '☁️', status: 'connected', description: 'Data storage' },
                  { name: 'Azure', icon: '🔗', status: 'available', description: 'Cloud platform' }
                ].map((integration, index) => (
                  <motion.div
                    key={integration.name}
                    className="neumorphic-card p-4 hover:neumorphic-raised transition-all duration-300"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.3, delay: index * 0.1 }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-3">
                        <span className="text-2xl">{integration.icon}</span>
                        <div>
                          <h4 className="font-medium text-foreground">{integration.name}</h4>
                          <p className="text-sm text-muted-foreground">{integration.description}</p>
                        </div>
                      </div>
                      <Badge 
                        className={`${
                          integration.status === 'connected' ? 'status-success border' : 'border-muted text-muted-foreground'
                        }`}
                      >
                        {integration.status}
                      </Badge>
                    </div>
                    
                    <Button 
                      size="sm" 
                      variant={integration.status === 'connected' ? "outline" : "default"}
                      className="neumorphic-button w-full mt-2"
                    >
                      {integration.status === 'connected' ? (
                        <>
                          <Key size={14} className="mr-2" />
                          Configure
                        </>
                      ) : (
                        <>
                          <Globe size={14} className="mr-2" />
                          Connect
                        </>
                      )}
                    </Button>
                  </motion.div>
                ))}
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </motion.div>
    </div>
  );
}