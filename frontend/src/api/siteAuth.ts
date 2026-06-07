import type { UserRole } from './client';

export interface AccessAuthStatus {
  authenticated: boolean;
  role: UserRole | null;
}

const AUTH_BASE_URL = '/api/auth';

async function requestAuth(path: string, init?: RequestInit): Promise<Response> {
  return fetch(`${AUTH_BASE_URL}${path}`, {
    credentials: 'include',
    ...init,
    headers: {
      ...(init?.headers || {}),
    },
  });
}

export const siteAuthClient = {
  async getStatus(): Promise<AccessAuthStatus> {
    const response = await requestAuth('/me');
    if (!response.ok) {
      return { authenticated: false, role: null };
    }
    return response.json();
  },

  async login(token: string): Promise<AccessAuthStatus> {
    const response = await requestAuth('/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ token }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => null);
      throw new Error(error?.detail || 'Failed to authenticate');
    }

    return response.json();
  },

  async logout(): Promise<AccessAuthStatus> {
    const response = await requestAuth('/logout', { method: 'POST' });
    if (!response.ok) {
      throw new Error('Failed to log out');
    }
    return response.json();
  },
};