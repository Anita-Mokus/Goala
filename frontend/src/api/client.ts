const API_BASE_URL = '/api';

export interface Settings {
  id: number;
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

export const apiClient = {
  async getSettings(): Promise<Settings> {
    const response = await fetch(`${API_BASE_URL}/settings`);
    if (!response.ok) {
      throw new Error(`Failed to fetch settings: ${response.statusText}`);
    }
    return response.json();
  },

  async updateSettings(settings: SettingsUpdate): Promise<Settings> {
    const response = await fetch(`${API_BASE_URL}/settings`, {
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
    const response = await fetch(`${API_BASE_URL}/history?${params}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch chat history: ${response.statusText}`);
    }
    return response.json();
  },

  // Messenger Bot API
  async getMessengerStatus(): Promise<MessengerStatus> {
    const response = await fetch(`${API_BASE_URL}/messenger/status`);
    if (!response.ok) {
      throw new Error(`Failed to fetch messenger status: ${response.statusText}`);
    }
    return response.json();
  },

  async startMessenger(): Promise<MessengerActionResponse> {
    const response = await fetch(`${API_BASE_URL}/messenger/start`, {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `Failed to start messenger bot: ${response.statusText}`);
    }
    return response.json();
  },

  async stopMessenger(): Promise<MessengerActionResponse> {
    const response = await fetch(`${API_BASE_URL}/messenger/stop`, {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `Failed to stop messenger bot: ${response.statusText}`);
    }
    return response.json();
  },

  async pauseMessenger(): Promise<MessengerActionResponse> {
    const response = await fetch(`${API_BASE_URL}/messenger/pause`, {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `Failed to pause messenger bot: ${response.statusText}`);
    }
    return response.json();
  },

  async resumeMessenger(): Promise<MessengerActionResponse> {
    const response = await fetch(`${API_BASE_URL}/messenger/resume`, {
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
};
