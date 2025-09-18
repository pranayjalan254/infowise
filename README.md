# InfoWise - Comprehensive PII Detection and Masking System

A sophisticated document processing platform that detects, analyzes, and masks Personally Identifiable Information (PII) in documents using multiple AI/ML approaches. Also has a Synthetic Dataset Generator module which lets you generate Synthetic data to train your AI models. Built with Python Flask backend and React and Typescript frontend.

## 🚀 System Architecture

### Backend (Flask API)

- **Framework**: Flask with modular blueprint architecture
- **Database**: MongoDB for document storage and metadata
- **AI/ML Stack**: BERT NER, Locally hosted LLM
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

- **PDF Documents**: Full coordinate-based detection and masking
- **Word Documents (.docx)**: Automatic conversion to PDF for processing
- **Text Files (.txt)**: Conversion to PDF with proper formatting

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
3. **Configuration**: Interactive review and strategy selection
4. **Masking**: Apply chosen strategies with coordinate precision
5. **Download**: Retrieve processed, privacy-compliant documents

## 🛠️ Technical Implementation

### Backend Services

#### Authentication Service (`services/auth.py`)

- User registration and login
- Google OAuth2 integration
- JWT token management
- Session handling

#### Document Management (`services/documents.py`)

- File upload/download using MongoDB GridFS
- Document metadata management
- Secure file serving

#### PII Detection (`services/pii_detection.py`)

- Enhanced multi-method PII detection
- Confidence scoring and verification
- Real-time streaming results

#### Simple Processing (`services/simple_processing.py`)

- Streamlined workflow for hackathon demo
- End-to-end document processing pipeline
- Configuration management

#### Core Components

- **Enhanced PII Detector** (`enhanced_pii_detector.py`): Multi-approach detection engine
- **Document Converter** (`document_converter.py`): Format conversion utilities
- **PII Masker** (`bert_pii_masker.py`): Coordinate-based masking system

### Frontend Components

#### Page Components

- **Landing Page**: Marketing and feature presentation
- **Authentication Pages**: Login/register with Google OAuth
- **Dashboard**: User analytics and system overview
- **Document Ingestion**: Multi-step processing workflow
- **Settings**: User preferences and configuration

#### UI Components

- **Document Upload**: Drag-and-drop file upload with progress
- **PII Detection Display**: Interactive detection results
- **Configuration Interface**: Strategy selection and editing
- **Document Viewer**: In-browser PDF preview
- **Progress Tracking**: Real-time workflow status

## 📋 API Endpoints

### Authentication

- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/logout` - User logout
- `GET /api/v1/auth/google` - Initiate Google OAuth
- `POST /api/v1/auth/google/callback` - Handle OAuth callback
- `GET /api/v1/auth/me` - Get current user info

### Document Management

- `POST /api/v1/documents/upload` - Upload documents
- `GET /api/v1/documents/list` - List user documents
- `GET /api/v1/documents/<doc_id>` - Get document details
- `DELETE /api/v1/documents/<doc_id>` - Delete document
- `GET /api/v1/documents/<doc_id>/view` - View document
- `GET /api/v1/documents/<doc_id>/download` - Download document

### PII Processing

- `POST /api/v1/pii/detect/<document_id>` - Detect PII in document
- `GET /api/v1/pii/results/<document_id>` - Get detection results
- `POST /api/v1/pii/save-config/<document_id>` - Save PII configuration
- `GET /api/v1/pii/detect-stream/<document_id>` - Streaming detection

### Simple Processing (Hackathon Demo)

- `POST /api/v1/simple/upload` - Upload document
- `POST /api/v1/simple/generate-config/<document_id>` - Generate PII config
- `GET /api/v1/simple/config/<document_id>` - Get configuration
- `PUT /api/v1/simple/config/<document_id>` - Update configuration
- `POST /api/v1/simple/apply-masking/<document_id>` - Apply masking
- `GET /api/v1/simple/download/<document_id>` - Download masked document

## 🚀 Installation & Setup

### Prerequisites

- Python 3.8+
- Node.js 16+
- MongoDB instance
- Google Cloud Project (for Gemini API)

### Backend Setup

1. **Clone the repository**

```bash
git clone <repository-url>
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
GOOGLE_API_KEY=your-gemini-api-key
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
VITE_API_URL=https://infowise-3mayd.ondigitalocean.app/api/v1
```

4. **Run development server**

```bash
npm run dev
```

## 🔧 Configuration

### PII Detection Configuration

The system supports configurable PII detection patterns in `enhanced_pii_detector.py`:

- Custom regex patterns for specific PII types
- Confidence thresholds for each detection method
- False positive patterns to exclude common false matches
- Severity levels for different PII categories

### Masking Strategies

Configure masking approaches in the PII configuration files:

- **Redact**: Complete removal of PII
- **Mask**: Partial character masking with patterns
- **Replace**: Substitution with generic placeholders
- **Custom**: User-defined masking strategies

### MongoDB Configuration

Documents and metadata are stored using MongoDB GridFS:

- File storage with automatic chunking
- Metadata indexing for fast retrieval
- User-based access control
- Automatic cleanup of expired sessions

## 🧪 Testing

### Backend Testing

```bash
cd api
python -m pytest tests/
```

### Frontend Testing

```bash
cd ui
npm run test
```

## 📊 Performance & Scalability

### Detection Performance

- **BERT Model**: ~2-3 seconds per page
- **Presidio**: ~1-2 seconds per page
- **Regex**: <1 second per page
- **LLM Verification**: ~3-5 seconds per batch

### Scalability Features

- **Asynchronous Processing**: Background task queues
- **Streaming Results**: Real-time progress updates
- **Batch Processing**: Multiple document handling
- **Caching**: Result caching for repeated operations

## 🔒 Security & Privacy

### Data Protection

- **Encryption at Rest**: MongoDB encrypted storage
- **Secure File Handling**: Temporary file cleanup
- **Access Control**: User-based document isolation
- **JWT Security**: Token-based authentication

### Compliance Features

- **Audit Logging**: Complete processing history
- **Data Retention**: Configurable cleanup policies
- **Privacy by Design**: Minimal data collection
- **Secure Deletion**: Permanent file removal

## 🎯 Future Enhancements

### Planned Features

- **Additional File Formats**: Excel, PowerPoint, CSV support
- **Batch Processing**: Multiple document workflows
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

## 🤝 Contributing

This project was developed for hackathon demonstration. The modular architecture supports easy extension and customization of detection methods, masking strategies, and UI components.

---

This comprehensive PII detection and masking system demonstrates enterprise-grade document processing capabilities with a user-friendly interface, making sensitive data protection accessible and efficient for organizations of all sizes.
