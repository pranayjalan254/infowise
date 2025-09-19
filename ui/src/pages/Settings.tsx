import { useState } from "react";
import { motion } from "framer-motion";
import { Save, User, Bell, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

export default function Settings() {
  const [settings, setSettings] = useState({
    emailNotifications: true,
    complianceAlerts: true,
    dataRetentionEnabled: false,
    auditLogging: true,
  });

  const handleSettingChange = (key: string, value: boolean) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
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
          Configure your privacy platform preferences
        </p>
      </motion.div>

      {/* Organization Settings */}
      <motion.div
        className="neumorphic-card p-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
      >
        <div className="flex items-center space-x-2 mb-4">
          <User size={20} className="text-primary" />
          <h3 className="text-lg font-semibold text-foreground">
            Organization Settings
          </h3>
        </div>

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
              <Label htmlFor="contact-email">Contact Email</Label>
              <Input
                id="contact-email"
                defaultValue="privacy@acmecorp.com"
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
          </div>
        </div>
      </motion.div>

      {/* System Preferences */}
      <motion.div
        className="neumorphic-card p-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
      >
        <div className="flex items-center space-x-2 mb-4">
          <Shield size={20} className="text-primary" />
          <h3 className="text-lg font-semibold text-foreground">
            System Preferences
          </h3>
        </div>

        <div className="space-y-4">
          {[
            {
              key: "emailNotifications",
              title: "Email Notifications",
              description: "Receive email alerts for important events",
            },
            {
              key: "complianceAlerts",
              title: "Compliance Alerts",
              description:
                "Get notified about regulation changes and compliance issues",
            },
            {
              key: "dataRetentionEnabled",
              title: "Automatic Data Retention",
              description:
                "Automatically delete data based on retention policies",
            },
            {
              key: "auditLogging",
              title: "Audit Logging",
              description: "Track all user activities and data access",
            },
          ].map((setting, index) => (
            <motion.div
              key={setting.key}
              className="neumorphic-flat p-4 rounded-xl"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
            >
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-foreground">
                    {setting.title}
                  </h4>
                  <p className="text-sm text-muted-foreground">
                    {setting.description}
                  </p>
                </div>
                <Switch
                  checked={settings[setting.key as keyof typeof settings]}
                  onCheckedChange={(value) =>
                    handleSettingChange(setting.key, value)
                  }
                />
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Notification Settings */}
      <motion.div
        className="neumorphic-card p-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.3 }}
      >
        <div className="flex items-center space-x-2 mb-4">
          <Bell size={20} className="text-primary" />
          <h3 className="text-lg font-semibold text-foreground">
            Notification Channels
          </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            {
              name: "Email",
              enabled: true,
              description: "Send notifications via email",
            },
            {
              name: "Slack",
              enabled: false,
              description: "Integration with Slack workspace",
            },
            {
              name: "Webhook",
              enabled: true,
              description: "Custom webhook notifications",
            },
          ].map((channel, index) => (
            <motion.div
              key={channel.name}
              className="neumorphic-flat p-4 rounded-xl text-center"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
            >
              <h4 className="font-medium text-foreground mb-2">
                {channel.name}
              </h4>
              <p className="text-sm text-muted-foreground mb-3">
                {channel.description}
              </p>
              <Switch checked={channel.enabled} />
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Save Button */}
      <motion.div
        className="flex justify-end"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.4 }}
      >
        <Button className="neumorphic-button">
          <Save size={16} className="mr-2" />
          Save All Changes
        </Button>
      </motion.div>
    </div>
  );
}
