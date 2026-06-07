const DEFAULT_API_BASE_URL = '/api';

function resolveApiBaseUrl(): string {
  const configuredBaseUrl = import.meta.env.VITE_API_URL?.trim();

  if (!configuredBaseUrl) {
    return DEFAULT_API_BASE_URL;
  }

  const normalizedBaseUrl = configuredBaseUrl.replace(/\/$/, '');
  return normalizedBaseUrl.endsWith('/api') ? normalizedBaseUrl : `${normalizedBaseUrl}/api`;
}

const API_BASE_URL = resolveApiBaseUrl();

async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`${API_BASE_URL}${path}`, {
    credentials: 'include',
    ...init,
    headers: {
      ...(init.headers || {}),
    },
  });
}

export interface Settings {
  id: number;
  dataset_name: 'liverag' | 'sapientia';
  llm_provider: string;
  llm_model: string;
  llm_temperature: number;
  retriever_k: number;
  pdf_language: string;
  pdf_strategy: string;
  chunk_max_characters: number;
  chunk_new_after_n_chars: number;
  chunk_overlap: number;
  rag_prompt_template: string;
  updated_at: string;
}

export interface SettingsUpdate {
  dataset_name: 'liverag' | 'sapientia';
  llm_provider: string;
  llm_model: string;
  llm_temperature: number;
  retriever_k: number;
  pdf_language: string;
  pdf_strategy: string;
  chunk_max_characters: number;
  chunk_new_after_n_chars: number;
  chunk_overlap: number;
  rag_prompt_template: string;
}

export interface ChatHistoryEntry {
  id: number;
  question: string;
  answer: string;
  dataset_name: 'liverag' | 'sapientia';
  model_used: string | null;
  response_time_ms: number | null;
  created_at: string;
}

export interface ChatHistoryResponse {
  items: ChatHistoryEntry[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface MessengerStatus {
  running: boolean;
  paused: boolean;
  message_count: number;
  last_message_timestamp: string | null;
  uptime_seconds: number;
  config_valid: boolean;
}

export interface MessengerActionResponse {
  status: string;
  message: string;
}

export type UserRole = 'admin' | 'operator';

export interface AuthStatusResponse {
  authenticated: boolean;
  expires_at: string | null;
  role: UserRole | null;
}

export const apiClient = {
  async getSettings(): Promise<Settings> {
    const response = await apiFetch('/settings');
    if (!response.ok) {
      throw new Error(`Failed to fetch settings: ${response.statusText}`);
    }
    return response.json();
  },

  async updateSettings(settings: SettingsUpdate): Promise<Settings> {
    const response = await apiFetch('/settings', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(settings),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `Failed to update settings: ${response.statusText}`);
    }
    return response.json();
  },

  async getChatHistory(page: number = 1, pageSize: number = 20, search?: string): Promise<ChatHistoryResponse> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    if (search) {
      params.append('search', search);
    }
    const response = await apiFetch(`/history?${params}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch chat history: ${response.statusText}`);
    }
    return response.json();
  },

  // Messenger Bot API
  async getMessengerStatus(): Promise<MessengerStatus> {
    const response = await apiFetch('/messenger/status');
    if (!response.ok) {
      throw new Error(`Failed to fetch messenger status: ${response.statusText}`);
    }
    return response.json();
  },

  async startMessenger(): Promise<MessengerActionResponse> {
    const response = await apiFetch('/messenger/start', {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `Failed to start messenger bot: ${response.statusText}`);
    }
    return response.json();
  },

  async stopMessenger(): Promise<MessengerActionResponse> {
    const response = await apiFetch('/messenger/stop', {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `Failed to stop messenger bot: ${response.statusText}`);
    }
    return response.json();
  },

  async pauseMessenger(): Promise<MessengerActionResponse> {
    const response = await apiFetch('/messenger/pause', {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `Failed to pause messenger bot: ${response.statusText}`);
    }
    return response.json();
  },

  async resumeMessenger(): Promise<MessengerActionResponse> {
    const response = await apiFetch('/messenger/resume', {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `Failed to resume messenger bot: ${response.statusText}`);
    }
    return response.json();
  },

  getMessengerLoginUrl(): string {
    return `${API_BASE_URL}/messenger/login-redirect`;
  },

  async getBackendAuthStatus(): Promise<AuthStatusResponse> {
    const response = await apiFetch('/auth/me');
    if (!response.ok) {
      return { authenticated: false, expires_at: null, role: null };
    }
    return response.json();
  },

  async loginBackend(token: string): Promise<AuthStatusResponse> {
    const response = await apiFetch('/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ token }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => null);
      throw new Error(error?.detail || `Failed to authenticate backend: ${response.statusText}`);
    }

    return response.json();
  },

  async logoutBackend(): Promise<AuthStatusResponse> {
    const response = await apiFetch('/auth/logout', {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error(`Failed to log out backend: ${response.statusText}`);
    }
    return response.json();
  },
};
