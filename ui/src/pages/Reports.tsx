import { motion } from "framer-motion";
import {
  Download,
  FileText,
  ExternalLink,
  Shield,
  Calendar,
  Building,
  Globe,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const complianceFrameworks = [
  {
    id: "hipaa",
    name: "HIPAA",
    fullName: "Health Insurance Portability and Accountability Act",
    description:
      "U.S. federal law that provides data privacy and security provisions for safeguarding medical information.",
    website: "https://www.hhs.gov/hipaa/index.html",
    region: "United States",
    icon: <Shield className="text-blue-600" size={24} />,
    status: "compliant",
    lastAudit: "2 days ago",
    piiTypes: [
      "Patient names and demographic information",
      "Social Security Numbers",
      "Medical record numbers",
      "Health plan beneficiary numbers",
      "Account numbers",
      "Certificate/license numbers",
      "Device identifiers",
      "IP addresses (when linked to PHI)",
      "Biometric identifiers",
      "Full face photographs",
      "Birth dates",
      "Admission/discharge dates",
      "Date of death",
      "Ages over 89",
      "Geographic subdivisions smaller than state",
      "Email addresses",
      "URLs and telephone numbers",
    ],
    reportDescription:
      "HIPAA compliance reports focus on Protected Health Information (PHI) and ensure all medical data handling meets federal requirements for privacy and security.",
    keyRequirements: [
      "PHI encryption in transit and at rest",
      "Access controls and audit logs",
      "Risk assessments and breach notifications",
      "Business associate agreements",
    ],
  },
  {
    id: "gdpr",
    name: "GDPR",
    fullName: "General Data Protection Regulation",
    description:
      "European Union regulation on data protection and privacy for individuals within the EU and European Economic Area.",
    website: "https://gdpr.eu/",
    region: "European Union",
    icon: <Globe className="text-blue-500" size={24} />,
    status: "compliant",
    lastAudit: "1 week ago",
    piiTypes: [
      "Names and surnames",
      "Home addresses and email addresses",
      "Identification card numbers",
      "Location data",
      "IP addresses",
      "Cookie identifiers",
      "Advertising identifiers",
      "Biometric data",
      "Genetic data",
      "Mental or physical health information",
      "Sexual orientation",
      "Political opinions",
      "Religious beliefs",
      "Trade union membership",
      "Criminal convictions",
      "Racial or ethnic origin",
      "Photographs and video recordings",
    ],
    reportDescription:
      "GDPR compliance reports ensure personal data processing meets EU standards with emphasis on consent, data minimization, and individual rights.",
    keyRequirements: [
      "Lawful basis for data processing",
      "Data subject consent management",
      "Right to erasure implementation",
      "Data portability mechanisms",
    ],
  },
  {
    id: "dpdpa",
    name: "DPDPA",
    fullName: "Digital Personal Data Protection Act",
    description:
      "India's comprehensive data protection law governing the processing of digital personal data.",
    website:
      "https://www.meity.gov.in/digital-personal-data-protection-act-2023",
    region: "India",
    icon: <Building className="text-orange-500" size={24} />,
    status: "at-risk",
    lastAudit: "3 days ago",
    piiTypes: [
      "Names and contact information",
      "Aadhaar numbers",
      "PAN numbers",
      "Passport numbers",
      "Driver's license numbers",
      "Bank account details",
      "Credit card information",
      "Biometric information",
      "Location data",
      "IP addresses",
      "Device identifiers",
      "Financial information",
      "Health records",
      "Educational records",
      "Employment information",
      "Photographs and videos",
      "Voice recordings",
    ],
    reportDescription:
      "DPDPA compliance reports focus on digital personal data processing within India, emphasizing user consent and data fiduciary obligations.",
    keyRequirements: [
      "Data fiduciary registration",
      "Consent management mechanisms",
      "Data breach notification procedures",
      "Cross-border data transfer protocols",
    ],
  },
  {
    id: "glba",
    name: "GLBA",
    fullName: "Gramm-Leach-Bliley Act",
    description:
      "U.S. federal law that requires financial institutions to explain how they share and protect customers' private information.",
    website:
      "https://www.ftc.gov/business-guidance/privacy-security/gramm-leach-bliley-act",
    region: "United States",
    icon: <Building className="text-green-600" size={24} />,
    status: "compliant",
    lastAudit: "5 days ago",
    piiTypes: [
      "Social Security Numbers",
      "Account numbers and balances",
      "Payment history",
      "Credit scores and reports",
      "Income information",
      "Names and addresses",
      "Phone numbers",
      "Email addresses",
      "Transaction records",
      "Loan information",
      "Investment portfolio data",
      "Insurance policy details",
      "Employment information",
      "Financial statements",
      "Tax identification numbers",
      "Driver's license numbers",
      "Passport numbers",
    ],
    reportDescription:
      "GLBA compliance reports ensure financial institutions properly handle and protect non-public personal information (NPI) of consumers.",
    keyRequirements: [
      "Privacy notices to customers",
      "Safeguarding customer information",
      "Information sharing limitations",
      "Pretexting protection measures",
    ],
  },
];

export default function Reports() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <h1 className="text-3xl font-bold text-display text-foreground mb-2">
          Compliance Reports
        </h1>
      </motion.div>

      {/* Compliance Frameworks */}
      <motion.div
        className="space-y-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
      >
        <h3 className="text-xl font-semibold text-foreground">
          Regulatory Compliance Frameworks
        </h3>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {complianceFrameworks.map((framework, index) => (
            <motion.div
              key={framework.id}
              className="neumorphic-card p-6 hover:neumorphic-raised transition-all duration-300"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
            >
              {/* Framework Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-3">
                  {framework.icon}
                  <div>
                    <h4 className="text-lg font-semibold text-foreground">
                      {framework.name}
                    </h4>
                    <p className="text-sm text-muted-foreground">
                      {framework.fullName}
                    </p>
                  </div>
                </div>
                <Badge
                  className={`${
                    framework.status === "compliant"
                      ? "status-success border"
                      : "status-warning border"
                  }`}
                >
                  {framework.status === "compliant" ? "Compliant" : "At Risk"}
                </Badge>
              </div>

              {/* Framework Info */}
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  {framework.description}
                </p>

                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Region:</span>
                  <span className="text-foreground font-medium">
                    {framework.region}
                  </span>
                </div>

                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Last Audit:</span>
                  <span className="text-foreground font-medium">
                    {framework.lastAudit}
                  </span>
                </div>

                {/* Report Description */}
                <div className="neumorphic-flat p-4 rounded-lg">
                  <h5 className="font-medium text-foreground mb-2">
                    Report Focus
                  </h5>
                  <p className="text-sm text-muted-foreground">
                    {framework.reportDescription}
                  </p>
                </div>

                {/* Key Requirements */}
                <div className="neumorphic-flat p-4 rounded-lg">
                  <h5 className="font-medium text-foreground mb-2">
                    Key Requirements
                  </h5>
                  <ul className="space-y-1">
                    {framework.keyRequirements.map((requirement, idx) => (
                      <li
                        key={idx}
                        className="text-sm text-muted-foreground flex items-start"
                      >
                        <span className="text-primary mr-2">•</span>
                        {requirement}
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Actions */}
                <div className="flex items-center space-x-2">
                  <Button size="sm" className="neumorphic-button flex-1">
                    <FileText size={12} className="mr-1" />
                    Generate Report
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="neumorphic-button"
                    onClick={() => window.open(framework.website, "_blank")}
                  >
                    <ExternalLink size={12} className="mr-1" />
                    Learn More
                  </Button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* PII Classification Details */}
      <motion.div
        className="space-y-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.4 }}
      >
        <h3 className="text-xl font-semibold text-foreground">
          PII Classification by Framework
        </h3>
        <p className="text-muted-foreground">
          Understanding what each regulatory framework considers as Personally
          Identifiable Information (PII)
        </p>

        <div className="space-y-8">
          {complianceFrameworks.map((framework, index) => (
            <motion.div
              key={`${framework.id}-pii`}
              className="neumorphic-card p-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
            >
              <div className="flex items-center space-x-3 mb-4">
                {framework.icon}
                <h4 className="text-lg font-semibold text-foreground">
                  {framework.name} - PII Definition
                </h4>
              </div>

              <p className="text-sm text-muted-foreground mb-4">
                {framework.name === "HIPAA" &&
                  "Under HIPAA, Protected Health Information (PHI) includes any individually identifiable health information that is transmitted or maintained by covered entities:"}
                {framework.name === "GDPR" &&
                  "GDPR defines personal data as any information relating to an identified or identifiable natural person ('data subject'):"}
                {framework.name === "DPDPA" &&
                  "The Digital Personal Data Protection Act defines personal data as data about or relating to an individual who is directly or indirectly identifiable:"}
                {framework.name === "GLBA" &&
                  "The Gramm-Leach-Bliley Act defines nonpublic personal information (NPI) as personally identifiable financial information:"}
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                {framework.piiTypes.map((piiType, idx) => (
                  <motion.div
                    key={idx}
                    className="neumorphic-flat px-3 py-2 rounded-lg"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.2, delay: idx * 0.02 }}
                  >
                    <span className="text-sm text-foreground">{piiType}</span>
                  </motion.div>
                ))}
              </div>

              <div className="mt-4 pt-4 border-t border-border">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">
                    Total PII Categories: {framework.piiTypes.length}
                  </span>
                  <Button
                    size="sm"
                    variant="outline"
                    className="neumorphic-button"
                    onClick={() => window.open(framework.website, "_blank")}
                  >
                    <ExternalLink size={12} className="mr-1" />
                    Official Guidelines
                  </Button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
