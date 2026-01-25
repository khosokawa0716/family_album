const DEFAULT_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

class ApiError extends Error {
  public status: number;
  public statusText: string;

  constructor(message: string, status: number, statusText: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.statusText = statusText;
  }
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = DEFAULT_BASE) {
    this.baseUrl = baseUrl;
  }

  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const token = sessionStorage.getItem("access_token");
    const response = await globalThis.fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      ...options,
    });

    if (!response.ok) {
      if (response.status === 401) {
        // 未認証、トークンが無効または期限切れの場合、ログインページにリダイレクト
        window.location.href = "/login";
        return Promise.reject(new ApiError("Unauthorized", 401, "Unauthorized"));
      }
      throw new ApiError(
        `HTTP error! status: ${response.status}`,
        response.status,
        response.statusText,
      );
    }

    // 204 No Content の場合は空のレスポンスを返す
    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: "GET" });
  }

  async post<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: "DELETE" });
  }

  async patch<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: "PATCH",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async postFormData<T>(endpoint: string, formData: FormData): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const token = sessionStorage.getItem("access_token");

    const response = await globalThis.fetch(url, {
      method: "POST",
      headers: {
        // Content-Typeは設定しない（ブラウザが自動設定）
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: formData,
    });

    if (!response.ok) {
      if (response.status === 401) {
        window.location.href = "/login";
        return Promise.reject(new ApiError("Unauthorized", 401, "Unauthorized"));
      }
      throw new ApiError(
        `HTTP error! status: ${response.status}`,
        response.status,
        response.statusText,
      );
    }

    return response.json();
  }

  async downloadBlob(endpoint: string): Promise<Blob> {
    const url = `${this.baseUrl}${endpoint}`;
    const token = sessionStorage.getItem("access_token");

    const response = await globalThis.fetch(url, {
      method: "GET",
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        window.location.href = "/login";
        return Promise.reject(new ApiError("Unauthorized", 401, "Unauthorized"));
      }
      throw new ApiError(
        `HTTP error! status: ${response.status}`,
        response.status,
        response.statusText,
      );
    }

    return response.blob();
  }
}

export const apiClient = new ApiClient();
export { ApiError };
