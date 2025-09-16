import { motion } from "framer-motion";
import {
  ArrowRight,
  Shield,
  Zap,
  Users,
  FileText,
  Lock,
  Eye,
  Brain,
  CheckCircle,
  Star,
  Github,
  Mail,
  X,
  Search,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useNavigate } from "react-router-dom";

export default function LandingPage() {
  const navigate = useNavigate();

  const features = [
    {
      icon: <Shield className="h-8 w-8" />,
      title: "Layered Defense Pipeline",
      description:
        "Hybrid approach combining rule-based detection, ML models, and LLM agents for maximum accuracy in PII detection across all document types.",
    },
    {
      icon: <Eye className="h-8 w-8" />,
      title: "Visual & Biometric Detection",
      description:
        "Advanced OCR and object detection for visual PII including photographs, signatures, stamps, and complex document layouts.",
    },
    {
      icon: <Brain className="h-8 w-8" />,
      title: "Self-Correcting Quality Loop",
      description:
        "Reflection Agent audits masked output for errors and triggers re-processing, ensuring exceptional quality with human-in-the-loop validation.",
    },
    {
      icon: <FileText className="h-8 w-8" />,
      title: "Multi-Format Support",
      description:
        "Process structured data (CSV, JSON), unstructured databases, complex PDFs, scans, and financial documents with intelligent layout analysis.",
    },
    {
      icon: <Lock className="h-8 w-8" />,
      title: "Regulatory Compliance",
      description:
        "Built-in compliance for GDPR, HIPAA, DPDPA, GLBA with policy-driven redaction and region-specific identifier detection (Aadhaar, PAN).",
    },
    {
      icon: <Zap className="h-8 w-8" />,
      title: "Synthetic Data Generation",
      description:
        "High-fidelity synthetic datasets that maintain statistical patterns and relational integrity for safe AI model training and POC development.",
    },
  ];

  const workflowSteps = [
    {
      id: 1,
      title: "PII Detection",
      description:
        "Advanced AI-powered identification of sensitive information",
      icon: <Eye className="h-6 w-6" />,
    },
    {
      id: 2,
      title: "Masking",
      description: "Intelligent redaction while preserving data utility",
      icon: <Shield className="h-6 w-6" />,
    },
    {
      id: 3,
      title: "Quality Assurance",
      description: "Self-correcting validation and accuracy verification",
      icon: <CheckCircle className="h-6 w-6" />,
    },
    {
      id: 4,
      title: "Synthetic Data Generation",
      description: "High-fidelity artificial datasets for safe AI training",
      icon: <Zap className="h-6 w-6" />,
    },
    {
      id: 5,
      title: "RAG Querying",
      description: "Natural language interaction with protected datasets",
      icon: <Search className="h-6 w-6" />,
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <motion.nav
        className="neumorphic-card border-b border-border/50 px-6 py-4 sticky top-0 z-50"
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="neumorphic-raised p-2 rounded-lg">
              <Shield className="h-8 w-8 text-primary" />
            </div>
            <h1 className="text-2xl font-bold text-display text-foreground">
              Infowise
            </h1>
          </div>

          <div className="hidden md:flex items-center space-x-8">
            <a
              href="#features"
              className="text-foreground hover:text-primary transition-colors"
            >
              Features
            </a>
            <a
              href="#workflow"
              className="text-foreground hover:text-primary transition-colors"
            >
              Workflow
            </a>
            <a
              href="#about"
              className="text-foreground hover:text-primary transition-colors"
            >
              About
            </a>
          </div>

          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              onClick={() => navigate("/auth")}
              className="neumorphic-button text-foreground"
            >
              Sign In
            </Button>
            <Button
              onClick={() => navigate("/auth")}
              className="neumorphic-button bg-primary text-primary-foreground hover:bg-primary/90"
            >
              Get Started
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </div>
      </motion.nav>

      {/* Hero Section */}
      <section className="relative px-6 py-20 overflow-hidden">
        <div className="max-w-7xl mx-auto">
          <div className="text-center">
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6 }}
              className="mb-8"
            >
              <Badge className="neumorphic-raised bg-primary/10 text-primary border-primary/20 mb-4">
                Multi-Agent AI Sandbox
              </Badge>
              <h1 className="text-6xl md:text-7xl font-bold text-display text-foreground mb-6 leading-tight">
                Unlock AI Innovation
                <br />
                <span className="text-primary">Safely & Securely</span>
              </h1>
              <p className="text-xl text-muted-foreground max-w-3xl mx-auto mb-8">
                Break through the AI adoption bottleneck. Infowise transforms
                sensitive enterprise data into safe, high-fidelity datasets for
                AI development, bridging the gap between business innovation and
                IT security with our collaborative multi-agent sandbox.
              </p>
            </motion.div>

            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="flex flex-col sm:flex-row gap-4 justify-center mb-12"
            >
              <Button
                size="lg"
                onClick={() => navigate("/auth")}
                className="neumorphic-button bg-primary text-primary-foreground hover:bg-primary/90 px-8 py-4 text-lg"
              >
                Get Started
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="neumorphic-button px-8 py-4 text-lg"
              >
                View Demo
                <Eye className="ml-2 h-5 w-5" />
              </Button>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="px-6 py-20">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <Badge className="neumorphic-raised bg-accent/10 text-accent border-accent/20 mb-4">
              Enterprise Features
            </Badge>
            <h2 className="text-5xl font-bold text-display text-foreground mb-6">
              Multi-Agent Ensemble Innovation
            </h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              Discover the powerful capabilities that make Infowise the catalyst
              for safe AI adoption. From layered defense detection to synthetic
              data generation, we solve the POC bottleneck that's holding back
              enterprise AI innovation.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <motion.div
                key={index}
                initial={{ y: 20, opacity: 0 }}
                whileInView={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                viewport={{ once: true }}
              >
                <Card className="neumorphic-card h-full border-0 hover:shadow-lg transition-all duration-300">
                  <CardHeader>
                    <div className="neumorphic-raised p-3 rounded-lg w-fit mb-4 text-primary">
                      {feature.icon}
                    </div>
                    <CardTitle className="text-xl text-display">
                      {feature.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground">
                      {feature.description}
                    </p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Workflow Section - Multi-Agent Architecture */}
      <section id="workflow" className="px-6 py-20 bg-surface/50">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <Badge className="neumorphic-raised bg-success/10 text-success border-success/20 mb-4">
              Streamlined Pipeline
            </Badge>
            <h2 className="text-5xl font-bold text-display text-foreground mb-6">
              5-Step Privacy Protection
            </h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              Our streamlined workflow transforms sensitive data into safe,
              valuable assets through five essential steps. From detection to
              querying, experience seamless data protection that enables AI
              innovation.
            </p>
          </motion.div>

          <div className="relative">
            {/* Workflow Steps */}
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6">
              {workflowSteps.map((step, index) => (
                <motion.div
                  key={step.id}
                  initial={{ y: 20, opacity: 0 }}
                  whileInView={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: index * 0.1 }}
                  viewport={{ once: true }}
                  className="relative"
                >
                  <Card className="neumorphic-card border-0 h-full hover:shadow-lg transition-all duration-300">
                    <CardHeader className="text-center pb-4">
                      <div className="neumorphic-raised p-4 rounded-full w-fit mx-auto mb-4 text-primary bg-primary/10">
                        {step.icon}
                      </div>
                      <div className="neumorphic-pressed px-3 py-1 rounded-full w-fit mx-auto mb-3">
                        <span className="text-sm font-semibold text-primary">
                          Step {step.id}
                        </span>
                      </div>
                      <CardTitle className="text-xl text-display mb-2">
                        {step.title}
                      </CardTitle>
                      <p className="text-muted-foreground text-sm">
                        {step.description}
                      </p>
                    </CardHeader>
                  </Card>

                  {/* Connector Arrow */}
                  {index < workflowSteps.length - 1 && (
                    <div className="hidden lg:block absolute -right-4 top-1/2 transform -translate-y-1/2 z-10">
                      <ArrowRight className="h-6 w-6 text-primary" />
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Use Case Section */}
      <section className="px-6 py-20">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <Badge className="neumorphic-raised bg-warning/10 text-warning border-warning/20 mb-4">
              Real-World Impact
            </Badge>
            <h2 className="text-5xl font-bold text-display text-foreground mb-6">
              From Stalemate to Success
            </h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              See how organizations break through AI adoption barriers and turn
              compliance challenges into competitive advantages with Infowise.
            </p>
          </motion.div>

          <motion.div
            initial={{ y: 20, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            viewport={{ once: true }}
          >
            <Card className="neumorphic-card border-0 max-w-4xl mx-auto">
              <CardHeader className="text-center pb-6">
                <Badge className="neumorphic-raised bg-primary/10 text-primary border-primary/20 mb-4 w-fit mx-auto">
                  Case Study: Financial Services
                </Badge>
                <CardTitle className="text-3xl text-display mb-4">
                  The Nexus Financial Group Challenge
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-8">
                <div className="grid md:grid-cols-2 gap-8">
                  <div className="neumorphic-pressed p-6 rounded-xl">
                    <h4 className="text-xl font-semibold text-danger mb-4 flex items-center">
                      <X className="h-5 w-5 mr-2" />
                      The Problem
                    </h4>
                    <div className="space-y-3 text-muted-foreground">
                      <p>• High-impact AI project stalled for months</p>
                      <p>
                        • Business analyst Priya blocked from accessing customer
                        data
                      </p>
                      <p>
                        • IT security lead Raj enforcing strict DPDPA compliance
                      </p>
                      <p>• Manual de-identification taking months and unsafe</p>
                      <p>
                        • Promising AI initiatives shelved due to regulatory
                        fears
                      </p>
                    </div>
                  </div>

                  <div className="neumorphic-raised p-6 rounded-xl">
                    <h4 className="text-xl font-semibold text-success mb-4 flex items-center">
                      <CheckCircle className="h-5 w-5 mr-2" />
                      The Solution
                    </h4>
                    <div className="space-y-3 text-muted-foreground">
                      <p>• Instant data profiling and PII identification</p>
                      <p>• Policy-driven masking with compliance mapping</p>
                      <p>• Self-correcting quality assurance validation</p>
                      <p>• Fully de-identified + synthetic training datasets</p>
                      <p>• Collaborative workspace for business and IT teams</p>
                    </div>
                  </div>
                </div>

                <div className="text-center neumorphic-card p-8 bg-primary/5 rounded-xl">
                  <h4 className="text-2xl font-bold text-primary mb-4">
                    Transformative Results
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div>
                      <div className="text-3xl font-bold text-primary mb-2">
                        2 weeks
                      </div>
                      <div className="text-muted-foreground">
                        POC completion time
                      </div>
                    </div>
                    <div>
                      <div className="text-3xl font-bold text-primary mb-2">
                        100%
                      </div>
                      <div className="text-muted-foreground">
                        Compliance maintained
                      </div>
                    </div>
                    <div>
                      <div className="text-3xl font-bold text-primary mb-2">
                        Partnership
                      </div>
                      <div className="text-muted-foreground">
                        Business + IT collaboration
                      </div>
                    </div>
                  </div>
                  <p className="text-muted-foreground mt-6 italic">
                    "Infowise turned our biggest roadblock into our competitive
                    advantage. The relationship between business and IT became a
                    true partnership."
                  </p>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="px-6 py-12 border-t border-border/50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center">
            <div className="flex items-center justify-center space-x-3 mb-6">
              <div className="neumorphic-raised p-2 rounded-lg">
                <Shield className="h-6 w-6 text-primary" />
              </div>
              <h3 className="text-xl font-bold text-display text-foreground">
                Infowise
              </h3>
            </div>

            <p className="text-muted-foreground mb-6 max-w-2xl mx-auto">
              Protecting your sensitive data with intelligent multi-agent AI
              architecture. Enterprise-grade privacy protection made simple.
            </p>

            <div className="flex items-center justify-center space-x-6 mb-8">
              <Button
                variant="ghost"
                size="sm"
                className="neumorphic-button text-muted-foreground"
              >
                <Mail className="h-4 w-4 mr-2" />
                Contact
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="neumorphic-button text-muted-foreground"
              >
                <Github className="h-4 w-4 mr-2" />
                GitHub
              </Button>
            </div>

            <div className="text-sm text-muted-foreground">
              © 2025 Infowise. All rights reserved. | Privacy Policy | Terms of
              Service
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
