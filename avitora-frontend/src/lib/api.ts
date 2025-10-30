import axios, { AxiosError } from 'axios';
import type {
  LoginRequest,
  SignupRequest,
  AuthResponse,
  User,
  AnalysisFormValue,
  GameEvaluation,
  Rakeback,
  UsageResponse,
  TodaysGamesResponse,
} from '@/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8100';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<any>) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      if (typeof window !== 'undefined') {
        window.location.href = '/auth/login';
      }
    }

    if (error.response?.status === 403) {
      const errorData = error.response.data;
      if (typeof errorData === 'object' && errorData.code === 'USAGE_LIMIT_EXCEEDED') {
        if (typeof window !== 'undefined') {
          window.dispatchEvent(
            new CustomEvent('usage-limit-exceeded', { detail: errorData })
          );
        }
      }
    }

    if (error.response?.status === 403) {
      const errorData = error.response.data;
      if (typeof errorData === 'object' && errorData.code === 'USER_BANNED') {
        if (typeof window !== 'undefined') {
          window.dispatchEvent(
            new CustomEvent('user-banned', { detail: errorData })
          );
        }
      }
    }

    return Promise.reject(error);
  }
);

export const authApi = {
  login: async (data: LoginRequest): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/auth/login', data);
    return response.data;
  },

  signup: async (data: SignupRequest): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/auth/signup', data);
    return response.data;
  },

  logout: async (): Promise<void> => {
    await apiClient.post('/auth/logout');
  },

  getMe: async (): Promise<User> => {
    const response = await apiClient.get<User>('/users/me');
    return response.data;
  },
};

export const analysisApi = {
  analyze: async (data: AnalysisFormValue): Promise<GameEvaluation[]> => {
    const response = await apiClient.post<GameEvaluation[]>('/analyze_paste', {
      paste_text: data.paste_text,
      sport_hint: data.sport_hint,
    });
    return response.data;
  },
};

export const settingsApi = {
  getRakeback: async (): Promise<Rakeback> => {
    const response = await apiClient.get<Rakeback>('/user/settings/rakeback');
    return response.data;
  },

  updateRakeback: async (data: Rakeback): Promise<Rakeback> => {
    const response = await apiClient.post<Rakeback>('/user/settings/rakeback', data);
    return response.data;
  },
};

export const usageApi = {
  getUsage: async (): Promise<UsageResponse> => {
    const response = await apiClient.get<UsageResponse>('/user/usage');
    return response.data;
  },
};

export const gamesApi = {
  getToday: async (): Promise<TodaysGamesResponse> => {
    const response = await apiClient.get<TodaysGamesResponse>('/games/today');
    return response.data;
  },
};

export default apiClient;
