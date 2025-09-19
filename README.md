# InfoWise - Comprehensive PII Detection and Masking System

A sophisticated document processing platform that detects, analyzes, and masks Personally Identifiable Information (PII) in documents using multiple AI/ML approaches. Also has a Synthetic Data Generator module which lets you generate Synthetic data to test your AI models. Built with Python Flask backend and React and Typescript frontend.

## 🚀 System Architecture

### Backend (Flask API)

- **Framework**: Flask with modular blueprint architecture
- **Database**: MongoDB for document storage and metadata
- **AI/ML Stack**: BERT NER, Locally hosted LLM (Ollama)
- **Document Processing**: PyMuPDF for PDF handling, python-docx for Word documents
- **Authentication**: JWT with Google OAuth2 support

### Frontend (React + TypeScript)

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite for fast development and building
- **UI Components**: Radix UI with shadcn/ui component library
- **Styling**: Tailwind CSS for responsive design
- **State Management**: TanStack Query for API state management
- **Routing**: React Router v6 for client-side routing

## ✨ Key Features

### 🔍 Advanced PII Detection

- **Multi-Method Detection**: Combines multiple different approaches for maximum accuracy
  - BERT Named Entity Recognition (NER)
  - Custom regex patterns for specific PII types
  - LLM verification to reduce false positives

### 📄 Document Format Support

- **PDF Documents**: Takes both Text and Scanned based.
- **Word Documents (.docx)**: Automatic conversion to PDF for processing
- **Text Files (.txt)**: Conversion to PDF with proper formatting
- **CSV Files (.csv)**: Specialised AI Agent that masks multiple csvs together and preserves context.

### 🎯 PII Types Detected

- **Personal Identifiers**: Social Security Numbers, Phone Numbers, Email Addresses
- **Financial Data**: Credit Card Numbers, Bank Account Numbers
- **Government IDs**: Aadhaar Numbers, PAN Numbers, Voter IDs
- **Geographic Data**: Addresses, ZIP Codes
- **Personal Data**: Names, Dates of Birth
- **Custom Patterns**: Extensible regex-based detection

### 🛡️ Masking Strategies

- **Redaction**: Complete removal of PII text
- **Masking**: Partial character replacement (e.g., **\*-**-1234)
- **Pseudoanonymization**: Substitution with dummy data.

### 👤 User Management

- **Email/Password Authentication**: Traditional login system
- **Google OAuth2**: Seamless social login integration
- **JWT Tokens**: Secure session management
- **User Profiles**: Personal dashboard and settings

### 🔄 Processing Workflow

1. **Document Upload**: Secure file upload with validation
2. **PII Detection**: Multi-method analysis with confidence scoring
3. **Review**: Human in the loop to review the detected PII.
4. **Masking**: Apply chosen strategies with coordinate precision
5. **Comparison & Download**: Retrieve processed, privacy-compliant documents

## 🌐 External API

InfoWise provides a powerful REST API for programmatic document processing, enabling seamless integration into existing workflows and applications.

### API Endpoint

```bash
POST https://infowise-3mayd.ondigitalocean.app/api/v1/simple/process-documents
```

### Key Features

- **Bulk Document Processing**: Handle single or multiple documents in one request with parallel processing
- **25+ PII Types Detected**: Comprehensive coverage including financial, medical, technical, and personal data
- **Hybrid AI/ML Approach**: Combines LLM, BERT NER, and regex patterns for maximum accuracy
- **Context-Aware Masking**: Intelligent masking strategies that preserve document utility
- **Multi-Format Support**: PDF, DOCX, TXT, CSV, and image files
- **Automatic Cleanup**: Memory optimization and temporary file management

### Comprehensive PII Detection Coverage

**Personal Identifiers**: Names, SSN, Passport, Driver License, Organizations  
**Contact Information**: Email, Phone, Address, ZIP Codes  
**Financial Data**: Credit Cards, Bank Accounts, PAN, Aadhaar  
**Medical & IDs**: Employee ID, Student ID, Medical Records, Insurance ID, Date of Birth  
**Technical Data**: IP Address, MAC Address, URLs, GPS Coordinates, Vehicle Plates  
**Tracking Codes**: Tracking Numbers, Barcodes, Vaccine Lots, Receipt Numbers

## 🚀 Installation & Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- MongoDB instance
- Ollama, Tesseract OCR and other BERT Based models

### Backend Setup

1. **Clone the repository**

```bash
git clone https://github.com/pranayjalan254/infowise.git
cd infowise/api
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. **Install Python dependencies**

```bash
pip install -r requirements.txt
```

4. **Download spaCy models**

```bash
python -m spacy download en_core_web_sm
python -m spacy download en_core_web_lg
```

5. **Environment Configuration**
   Create `.env` file:

```env
FLASK_ENV=development
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=your-google-redirect-uri
MONGODB_CONNECTION_STRING=mongodb://localhost:27017/infowise
CORS_ORIGINS=http://localhost:8080
FRONTEND_URL=http://localhost:8080
```

6. **Run the Flask application**

```bash
python app.py
```

### Frontend Setup

1. **Navigate to UI directory**

```bash
cd ../ui
```

2. **Install dependencies**

```bash
npm install
```

3. **Environment Configuration**
   Create `.env` file:

```env
VITE_API_URL=http://localhost:5000/api/v1
```

4. **Run development server**

```bash
npm run dev
```

### Masking Strategies

Configure masking approaches in the PII configuration files:

- **Redact**: Complete removal of PII
- **Mask**: Partial character masking with patterns
- **Replace**: Substitution with dummy data
- **Custom**: User-defined masking strategies

## 🎯 Future Enhancements

### Planned Features

- **API Rate Limiting**: Request throttling and quotas
- **Advanced Analytics**: PII trend analysis and reporting
- **Custom Model Training**: User-specific PII detection
- **Compliance Frameworks**: GDPR, CCPA, HIPAA templates

### Technical Improvements

- **Redis Caching**: Performance optimization
- **Docker Deployment**: Containerized setup
- **Load Balancing**: Multi-instance scaling
- **Database Migrations**: Schema versioning
- **Monitoring & Alerting**: System health tracking
