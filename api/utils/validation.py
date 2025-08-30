"""
Pydantic models for request/response validation.
All API input/output schemas are defined here.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum


# Enums
class PIISeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    AT_RISK = "at-risk"
    NON_COMPLIANT = "non-compliant"


class QAStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# Base models
class BaseResponse(BaseModel):
    status: str = Field(..., description="Response status")
    data: Optional[Any] = Field(None, description="Response data")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details")
    meta: Optional[Dict[str, Any]] = Field(None, description="Metadata")


# Auth models
class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=6, description="User password")


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=5, description="User password")
    first_name: str = Field(..., min_length=1, max_length=50, description="First name")
    last_name: str = Field(..., min_length=1, max_length=50, description="Last name")
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class UserResponse(BaseModel):
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    role: str = Field(default="user", description="User role")
    created_at: str = Field(..., description="Creation timestamp")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    expires_in: int = Field(..., description="Token expiration in seconds")


# File models
class FileUploadResponse(BaseModel):
    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME type")
    upload_url: Optional[str] = Field(None, description="Upload URL if needed")
    created_at: str = Field(..., description="Upload timestamp")


class FileMetadata(BaseModel):
    file_id: str = Field(..., description="File ID")
    filename: str = Field(..., description="Filename")
    size: int = Field(..., description="File size")
    content_type: str = Field(..., description="Content type")
    status: str = Field(..., description="Processing status")
    created_at: str = Field(..., description="Created timestamp")


# PII Detection models
class PIIItem(BaseModel):
    type: str = Field(..., description="PII type (e.g., SSN, email)")
    value: str = Field(..., description="Detected value (may be masked)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    location: str = Field(..., description="Location in document")
    severity: PIISeverity = Field(..., description="Severity level")


class PIIDetectionRequest(BaseModel):
    file_id: str = Field(..., description="File to analyze")
    detection_types: Optional[List[str]] = Field(None, description="Specific PII types to detect")
    confidence_threshold: float = Field(0.8, ge=0.0, le=1.0, description="Minimum confidence")


class PIIDetectionResult(BaseModel):
    detection_id: str = Field(..., description="Detection job ID")
    file_id: str = Field(..., description="Source file ID")
    pii_items: List[PIIItem] = Field(..., description="Detected PII items")
    status: WorkflowStatus = Field(..., description="Detection status")
    total_items: int = Field(..., description="Total PII items found")
    high_severity_count: int = Field(..., description="High severity items")
    created_at: str = Field(..., description="Detection timestamp")


# Compliance models
class ComplianceRequirement(BaseModel):
    id: str = Field(..., description="Requirement ID")
    name: str = Field(..., description="Requirement name")
    status: ComplianceStatus = Field(..., description="Compliance status")
    description: str = Field(..., description="Requirement description")


class ComplianceFramework(BaseModel):
    id: str = Field(..., description="Framework ID")
    name: str = Field(..., description="Framework name")
    status: ComplianceStatus = Field(..., description="Overall status")
    score: float = Field(..., ge=0.0, le=100.0, description="Compliance score")
    requirements: List[ComplianceRequirement] = Field(..., description="Requirements")


class ComplianceCheckRequest(BaseModel):
    file_id: str = Field(..., description="File to check")
    frameworks: List[str] = Field(..., description="Frameworks to check against")


class ComplianceReport(BaseModel):
    report_id: str = Field(..., description="Report ID")
    file_id: str = Field(..., description="Source file")
    frameworks: List[ComplianceFramework] = Field(..., description="Framework results")
    overall_score: float = Field(..., description="Overall compliance score")
    recommendations: List[str] = Field(..., description="Improvement recommendations")
    created_at: str = Field(..., description="Report timestamp")


# Masking models
class MaskingOption(BaseModel):
    id: str = Field(..., description="Masking option ID")
    name: str = Field(..., description="Option name")
    description: str = Field(..., description="Option description")
    example: str = Field(..., description="Example output")


class MaskingConfig(BaseModel):
    pii_type: str = Field(..., description="PII type to mask")
    masking_method: str = Field(..., description="Masking method")
    preserve_format: bool = Field(True, description="Preserve original format")
    custom_pattern: Optional[str] = Field(None, description="Custom masking pattern")


class MaskingRequest(BaseModel):
    file_id: str = Field(..., description="File to mask")
    config: List[MaskingConfig] = Field(..., description="Masking configuration")


class MaskingResult(BaseModel):
    masking_id: str = Field(..., description="Masking job ID")
    file_id: str = Field(..., description="Source file")
    masked_file_id: str = Field(..., description="Masked file ID")
    status: WorkflowStatus = Field(..., description="Masking status")
    items_masked: int = Field(..., description="Number of items masked")
    created_at: str = Field(..., description="Masking timestamp")


# QA models
class QAIssue(BaseModel):
    id: str = Field(..., description="Issue ID")
    type: str = Field(..., description="Issue type")
    description: str = Field(..., description="Issue description")
    severity: PIISeverity = Field(..., description="Issue severity")
    status: QAStatus = Field(..., description="Resolution status")


class QARequest(BaseModel):
    file_id: str = Field(..., description="File for QA")


class QAResult(BaseModel):
    qa_id: str = Field(..., description="QA job ID")
    file_id: str = Field(..., description="Source file")
    issues: List[QAIssue] = Field(..., description="Identified issues")
    overall_status: QAStatus = Field(..., description="Overall QA status")
    score: float = Field(..., ge=0.0, le=100.0, description="Quality score")
    created_at: str = Field(..., description="QA timestamp")


# Dashboard models
class DashboardMetric(BaseModel):
    id: str = Field(..., description="Metric ID")
    title: str = Field(..., description="Metric title")
    value: Union[str, int, float] = Field(..., description="Metric value")
    change: Optional[float] = Field(None, description="Change percentage")
    trend: Optional[str] = Field(None, description="Trend direction")
    unit: Optional[str] = Field(None, description="Value unit")


class ChartDataPoint(BaseModel):
    label: str = Field(..., description="Data point label")
    value: float = Field(..., description="Data point value")
    color: Optional[str] = Field(None, description="Display color")


class DashboardData(BaseModel):
    metrics: List[DashboardMetric] = Field(..., description="Key metrics")
    charts: Dict[str, List[ChartDataPoint]] = Field(..., description="Chart data")
    last_updated: str = Field(..., description="Last update timestamp")


# Report models
class ReportConfig(BaseModel):
    file_ids: List[str] = Field(..., description="Files to include")
    report_type: str = Field(..., description="Report type")
    include_pii: bool = Field(True, description="Include PII analysis")
    include_compliance: bool = Field(True, description="Include compliance check")
    include_masking: bool = Field(False, description="Include masking results")
    format: str = Field("pdf", description="Output format")


class ReportSummary(BaseModel):
    report_id: str = Field(..., description="Report ID")
    title: str = Field(..., description="Report title")
    status: str = Field(..., description="Generation status")
    file_count: int = Field(..., description="Number of files analyzed")
    download_url: Optional[str] = Field(None, description="Download URL")
    created_at: str = Field(..., description="Creation timestamp")


# Sandbox models
class ChatMessage(BaseModel):
    message: str = Field(..., description="Chat message")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class ChatResponse(BaseModel):
    response: str = Field(..., description="Chat response")
    suggestions: Optional[List[str]] = Field(None, description="Follow-up suggestions")
    timestamp: str = Field(..., description="Response timestamp")
