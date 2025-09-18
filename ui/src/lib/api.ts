import { QueryClient } from "@tanstack/react-query";

// API Configuration
const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:5000/api/v1";

// Request/Response types
interface ApiResponse<T = any> {
  status: "success" | "error";
  data: T | null;
  error: {
    code: string;
    message: string;
  } | null;
  meta?: any;
}

interface AuthTokens {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

interface AuthResponse {
  user: User;
  tokens: AuthTokens;
}

interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  created_at: string;
}

interface LoginRequest {
  email: string;
  password: string;
}

interface RegisterRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
}

interface FileUploadResponse {
  file_id: string;
  filename: string;
  size: number;
  upload_url?: string;
}

// Auth utilities
export const getAuthToken = (): string | null => {
  return localStorage.getItem("auth_token");
};

export const setAuthToken = (token: string): void => {
  localStorage.setItem("auth_token", token);
};

export const removeAuthToken = (): void => {
  localStorage.removeItem("auth_token");
};

export const isAuthenticated = (): boolean => {
  return !!getAuthToken();
};

// Base API client
class ApiClient {
  private baseURL: string;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;
    const token = getAuthToken();

    const config: RequestInit = {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "X-Request-ID": crypto.randomUUID(),
        ...options.headers,
        ...(token && { Authorization: `Bearer ${token}` }),
      },
    };

    try {
      const response = await fetch(url, config);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error?.message || "Request failed");
      }

      return data;
    } catch (error) {
      console.error("API request failed:", error);
      throw error;
    }
  }

  async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: "GET" });
  }

  async post<T>(
    endpoint: string,
    data?: any,
    customHeaders?: Record<string, string>
  ): Promise<ApiResponse<T>> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...customHeaders,
    };

    // Don't set Content-Type for FormData
    if (data instanceof FormData) {
      delete headers["Content-Type"];
    }

    return this.request<T>(endpoint, {
      method: "POST",
      body:
        data instanceof FormData
          ? data
          : data
          ? JSON.stringify(data)
          : undefined,
      headers,
    });
  }

  async put<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: "DELETE" });
  }

  async uploadFiles<T>(
    endpoint: string,
    files: FileList
  ): Promise<ApiResponse<T>> {
    const formData = new FormData();
    Array.from(files).forEach((file) => {
      formData.append("files", file);
    });

    const token = getAuthToken();
    const config: RequestInit = {
      method: "POST",
      headers: {
        ...(token && { Authorization: `Bearer ${token}` }),
        "X-Request-ID": crypto.randomUUID(),
        // Don't set Content-Type for FormData - browser will set it with boundary
      },
      body: formData,
    };

    const url = `${this.baseURL}${endpoint}`;
    const response = await fetch(url, config);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error?.message || "Upload failed");
    }

    return data;
  }

  async uploadFile(
    endpoint: string,
    file: File
  ): Promise<ApiResponse<FileUploadResponse>> {
    const formData = new FormData();
    formData.append("file", file);

    const token = getAuthToken();
    const config: RequestInit = {
      method: "POST",
      headers: {
        ...(token && { Authorization: `Bearer ${token}` }),
        "X-Request-ID": crypto.randomUUID(),
      },
      body: formData,
    };

    const response = await fetch(`${this.baseURL}${endpoint}`, config);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error?.message || "Upload failed");
    }

    return data;
  }
}

const apiClient = new ApiClient(API_BASE_URL);

// API endpoints
export const authApi = {
  login: (credentials: LoginRequest) =>
    apiClient.post<AuthResponse>("/auth/login", credentials),

  register: (userData: RegisterRequest) =>
    apiClient.post<AuthResponse>("/auth/register", userData),

  logout: () => apiClient.post("/auth/logout"),

  refreshToken: () => apiClient.post<AuthTokens>("/auth/refresh"),

  getCurrentUser: () => apiClient.get<User>("/auth/me"),

  // Google OAuth methods
  getGoogleAuthUrl: () =>
    apiClient.get<{ authorization_url: string; state: string }>("/auth/google"),

  verifyGoogleToken: (idToken: string) =>
    apiClient.post<AuthResponse>("/auth/google/verify", { id_token: idToken }),
};

// Document API
export const documentsApi = {
  upload: (files: FileList) => {
    return apiClient.uploadFiles<{
      uploaded_documents: Array<{
        id: string;
        name: string;
        size: number;
        type: string;
        upload_date: string;
      }>;
      total_uploaded: number;
      errors?: string[];
    }>("/documents/upload", files);
  },

  list: () =>
    apiClient.get<{
      documents: Array<{
        id: string;
        name: string;
        size: number;
        type: string;
        mime_type: string;
        upload_date: string;
        status: string;
      }>;
      total_count: number;
    }>("/documents/list"),

  get: (documentId: string) =>
    apiClient.get<{
      id: string;
      name: string;
      size: number;
      type: string;
      mime_type: string;
      upload_date: string;
      status: string;
      metadata: any;
    }>(`/documents/${documentId}`),

  delete: (documentId: string) => apiClient.delete(`/documents/${documentId}`),

  getStats: () =>
    apiClient.get<{
      total_documents: number;
      total_size_bytes: number;
      total_size_mb: number;
      file_types: Record<string, { count: number; size: number }>;
    }>("/documents/stats"),

  getViewUrl: (documentId: string) => {
    const token = getAuthToken();
    return `${API_BASE_URL}/documents/${documentId}/view?token=${token}`;
  },

  getDownloadUrl: (documentId: string) => {
    const token = getAuthToken();
    return `${API_BASE_URL}/documents/${documentId}/download?token=${token}`;
  },

  downloadDocument: async (documentId: string, fileName: string) => {
    const token = getAuthToken();
    const response = await fetch(
      `${API_BASE_URL}/documents/${documentId}/download`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    if (!response.ok) {
      throw new Error("Download failed");
    }

    // Create blob and trigger download
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  },
};

// File upload API
export const fileApi = {
  upload: (files: FileList) => {
    return apiClient.uploadFiles<{
      uploaded_documents: Array<{
        id: string;
        name: string;
        size: number;
        type: string;
        upload_date: string;
      }>;
      total_uploaded: number;
      errors?: string[];
    }>("/files/upload", files);
  },

  getUploadHistory: () => apiClient.get("/files/history"),

  deleteFile: (fileId: string) => apiClient.delete(`/files/${fileId}`),
};

export const piiApi = {
  detectPII: (documentId: string) =>
    apiClient.post<{
      document_id: string;
      document_name: string;
      total_pii_detected: number;
      pii_items: Array<{
        id: string;
        type: string;
        text: string;
        confidence: number;
        location: string;
        severity: "low" | "medium" | "high";
        suggested_strategy: string;
        coordinates: {
          page: number;
          x0: number;
          y0: number;
          x1: number;
          y1: number;
        };
      }>;
      detection_date: string;
    }>(`/pii/detect/${documentId}`, {}),

  saveMaskingConfig: (
    documentId: string,
    maskingStrategies: Record<string, string>
  ) =>
    apiClient.post<{
      document_id: string;
      config_content: string;
      total_items: number;
    }>(`/pii/save-config/${documentId}`, {
      masking_strategies: maskingStrategies,
    }),

  getDetectionResults: (documentId: string) =>
    apiClient.get<{
      document_id: string;
      document_name: string;
      detection_status: string;
      total_pii_detected: number;
      pii_items: Array<{
        id: string;
        type: string;
        text: string;
        confidence: number;
        location: string;
        severity: "low" | "medium" | "high";
        suggested_strategy: string;
        coordinates: {
          page: number;
          x0: number;
          y0: number;
          x1: number;
          y1: number;
        };
      }>;
      detection_date: string;
    }>(`/pii/results/${documentId}`),

  batchDetectPII: (documentIds: string[]) =>
    apiClient.post<{
      results: Array<{
        document_id: string;
        document_name: string;
        total_pii_detected: number;
        pii_items: Array<any>;
        detection_date: string;
      }>;
      total_processed: number;
      total_requested: number;
      errors?: string[];
    }>("/pii/batch-detect", { document_ids: documentIds }),

  // Streaming PII detection functions
  detectPIIStream: (
    documentId: string,
    onMessage: (event: any) => void,
    onError?: (error: Error) => void
  ) => {
    const token = getAuthToken();
    if (!token) {
      throw new Error("No authentication token");
    }

    const eventSource = new EventSource(
      `${API_BASE_URL}/pii/detect-stream/${documentId}?token=${token}`
    );

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);

        // Close connection on completion or error
        if (data.type === "complete" || data.type === "error") {
          eventSource.close();
        }
      } catch (error) {
        console.error("Error parsing SSE data:", error);
        onError?.(error as Error);
        eventSource.close();
      }
    };

    eventSource.onerror = (error) => {
      console.error("SSE error:", error);
      onError?.(new Error("Connection error"));
      eventSource.close();
    };

    return eventSource;
  },

  batchDetectPIIStream: (
    documentIds: string[],
    onMessage: (event: any) => void,
    onError?: (error: Error) => void
  ) => {
    const token = getAuthToken();
    if (!token) {
      throw new Error("No authentication token");
    }

    // For batch streaming, we need to use fetch with streaming response
    const controller = new AbortController();

    fetch(`${API_BASE_URL}/pii/batch-detect-stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        Accept: "text/event-stream",
      },
      body: JSON.stringify({ document_ids: documentIds }),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error("No response body");
        }

        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n");

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.slice(6));
                onMessage(data);
              } catch (error) {
                console.error("Error parsing SSE data:", error);
              }
            }
          }
        }
      })
      .catch((error) => {
        if (error.name !== "AbortError") {
          onError?.(error);
        }
      });

    return {
      close: () => controller.abort(),
    };
  },
};

export const complianceApi = {
  checkCompliance: (fileId: string, frameworks: string[]) =>
    apiClient.post("/compliance/check", { file_id: fileId, frameworks }),

  getComplianceReport: (fileId: string) =>
    apiClient.get(`/compliance/report/${fileId}`),
};

export const maskingApi = {
  getMaskingOptions: () => apiClient.get("/masking/options"),

  applyMasking: (documentId: string) =>
    apiClient.post<{
      original_document_id: string;
      masked_document_id: string;
      masked_filename: string;
      masking_stats: any;
      total_pii_masked: number;
      strategies_used: Record<string, number>;
      masking_date: string;
    }>(`/masking/apply/${documentId}`, {}),

  getMaskedFile: (documentId: string) =>
    apiClient.get(`/masking/download/${documentId}`),

  previewMaskedFile: (documentId: string) =>
    apiClient.get(`/masking/preview/${documentId}`),

  previewOriginalFile: (documentId: string) =>
    apiClient.get(`/masking/preview-original/${documentId}`),
  getMaskingStatus: (documentId: string) =>
    apiClient.get<{
      document_id: string;
      status: string;
      masked_document_id?: string;
      masked_filename?: string;
      masking_date?: string;
      total_pii_masked: number;
      strategies_used: Record<string, number>;
      failed_maskings: number;
      stats: any;
    }>(`/masking/status/${documentId}`),

  debugMaskingConfig: (documentId: string) =>
    apiClient.get(`/masking/debug/${documentId}`),
};

export const qaApi = {
  submitForQA: (fileId: string) =>
    apiClient.post("/qa/submit", { file_id: fileId }),

  getQAResults: (fileId: string) => apiClient.get(`/qa/results/${fileId}`),

  approveQA: (qaId: string) => apiClient.post(`/qa/${qaId}/approve`),

  rejectQA: (qaId: string, reason: string) =>
    apiClient.post(`/qa/${qaId}/reject`, { reason }),
};

export const dashboardApi = {
  getMetrics: () => apiClient.get("/dashboard/metrics"),

  getChartData: (chartType: string) =>
    apiClient.get(`/dashboard/charts/${chartType}`),
};

export const reportsApi = {
  getReports: () => apiClient.get("/reports"),

  generateReport: (config: any) => apiClient.post("/reports/generate", config),

  downloadReport: (reportId: string) =>
    apiClient.get(`/reports/${reportId}/download`),
};

export const sandboxApi = {
  chat: (message: string, context?: any) =>
    apiClient.post("/sandbox/chat", { message, context }),

  getChatHistory: () => apiClient.get("/sandbox/history"),
};

export const syntheticDataApi = {
  startGeneration: (documentId: string, numDatasets: number) =>
    apiClient.post("/synthetic/generate", {
      document_id: documentId,
      num_datasets: numDatasets,
    }),

  getGenerationStatus: (jobId: string) =>
    apiClient.get(`/synthetic/status/${jobId}`),

  listDatasets: () =>
    apiClient.get<{
      datasets: Array<{
        id: string;
        synthetic_name: string;
        original_name: string;
        dataset_number: number;
        size: number;
        created_at: string;
        job_id: string;
      }>;
      total_count: number;
    }>("/synthetic/datasets"),

  downloadDataset: async (datasetId: string, fileName: string) => {
    const token = getAuthToken();
    const response = await fetch(
      `${API_BASE_URL}/synthetic/datasets/${datasetId}/download`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    if (!response.ok) {
      throw new Error("Download failed");
    }

    // Create blob and trigger download
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  },

  previewDataset: (datasetId: string) =>
    apiClient.get<{
      id: string;
      name: string;
      original_name: string;
      size: number;
      content_preview: string;
      created_at: string;
    }>(`/synthetic/datasets/${datasetId}/preview`),

  listJobs: () =>
    apiClient.get<{
      jobs: Array<{
        job_id: string;
        document_name: string;
        num_datasets: number;
        status: string;
        progress: number;
        status_message: string;
        created_at: string;
        completed_at?: string;
        generated_datasets?: Array<{
          id: string;
          name: string;
          dataset_number: number;
          size: number;
          created_at: string;
        }>;
        error?: string;
      }>;
      total_count: number;
    }>("/synthetic/jobs"),
};

// Simple Processing API for Hackathon Prototype (no JWT required)
export const simpleProcessingApi = {
  uploadDocument: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);

    return fetch(`${API_BASE_URL}/simple/upload`, {
      method: "POST",
      body: formData,
    }).then(async (response) => {
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error?.message || "Upload failed");
      }
      return data;
    });
  },

  uploadMultipleDocuments: (files: FileList | File[]) => {
    const formData = new FormData();
    Array.from(files).forEach((file) => {
      formData.append("files", file);
    });

    return fetch(`${API_BASE_URL}/simple/upload`, {
      method: "POST",
      body: formData,
    }).then(async (response) => {
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error?.message || "Upload failed");
      }
      return data;
    });
  },

  generateConfig: (documentId: string) =>
    fetch(`${API_BASE_URL}/simple/generate-config`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ document_ids: [documentId] }),
    }).then(async (response) => {
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error?.message || "Config generation failed");
      }
      return data;
    }),

  generateConfigBulk: (documentIds: string[]) =>
    fetch(`${API_BASE_URL}/simple/generate-config`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ document_ids: documentIds }),
    }).then(async (response) => {
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error?.message || "Bulk config generation failed");
      }
      return data;
    }),

  getConfig: (documentId: string) =>
    fetch(`${API_BASE_URL}/simple/config/${documentId}`).then(
      async (response) => {
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.error?.message || "Failed to get config");
        }
        return data;
      }
    ),

  updateConfig: (documentId: string, configData: any[]) =>
    fetch(`${API_BASE_URL}/simple/config/${documentId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ config_data: configData }),
    }).then(async (response) => {
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error?.message || "Failed to update config");
      }
      return data;
    }),

  applyMasking: (documentId: string) =>
    fetch(`${API_BASE_URL}/simple/apply-masking`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ document_ids: [documentId] }),
    }).then(async (response) => {
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error?.message || "Masking failed");
      }
      return data;
    }),

  applyMaskingBulk: (documentIds: string[]) =>
    fetch(`${API_BASE_URL}/simple/apply-masking`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ document_ids: documentIds }),
    }).then(async (response) => {
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error?.message || "Bulk masking failed");
      }
      return data;
    }),

  downloadMaskedDocument: (documentId: string) =>
    fetch(`${API_BASE_URL}/simple/download/${documentId}`).then((response) => {
      if (!response.ok) {
        throw new Error("Download failed");
      }
      return response.blob();
    }),

  getDocumentStatus: (documentId: string) =>
    fetch(`${API_BASE_URL}/simple/status/${documentId}`).then(
      async (response) => {
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.error?.message || "Failed to get status");
        }
        return data;
      }
    ),

  getPreviewUrl: (documentId: string) =>
    `${API_BASE_URL}/simple/preview/${documentId}`,

  getMaskedPreviewUrl: (documentId: string) =>
    `${API_BASE_URL}/simple/preview-masked/${documentId}`,

  // New MongoDB-based download endpoints
  downloadFromMongo: (
    documentId: string,
    status: "uploaded" | "masked" = "masked"
  ) =>
    fetch(
      `${API_BASE_URL}/simple/download-from-mongo/${documentId}?status=${status}`
    ).then((response) => {
      if (!response.ok) {
        throw new Error("MongoDB download failed");
      }
      return response.blob();
    }),

  getMongoInfo: (documentId: string, status?: string) => {
    const url = status
      ? `${API_BASE_URL}/simple/mongo-info/${documentId}?status=${status}`
      : `${API_BASE_URL}/simple/mongo-info/${documentId}`;

    return fetch(url).then(async (response) => {
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error?.message || "Failed to get MongoDB info");
      }
      return data;
    });
  },

  // Cleanup endpoints
  cleanupProcessingData: (documentId: string) =>
    fetch(`${API_BASE_URL}/simple/cleanup/${documentId}`, {
      method: "POST",
    }).then(async (response) => {
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error?.message || "Cleanup failed");
      }
      return data;
    }),

  forceCleanupAllData: (documentId: string) =>
    fetch(`${API_BASE_URL}/simple/cleanup/${documentId}/force`, {
      method: "POST",
    }).then(async (response) => {
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error?.message || "Force cleanup failed");
      }
      return data;
    }),
};

// Query client for React Query
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

export default apiClient;
