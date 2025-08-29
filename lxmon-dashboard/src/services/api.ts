import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface Server {
  id: number;
  name: string;
  hostname: string;
  ip_address?: string;
  status: string;
  last_heartbeat?: string;
  created_at: string;
}

export interface Metric {
  id: number;
  server_id: number;
  metric_type: string;
  metric_name: string;
  value: number;
  unit?: string;
  collected_at: string;
}

export interface Command {
  id: number;
  server_id: number;
  command: string;
  status: string;
  exit_code?: number;
  stdout?: string;
  stderr?: string;
  executed_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface AlertRule {
  id: number;
  name: string;
  description?: string;
  metric_type: string;
  metric_name: string;
  condition: string;
  threshold: number;
  severity: string;
  enabled: boolean;
  created_at: string;
}

export interface SystemInfo {
  timestamp: string;
  system: {
    platform: string;
    platform_version: string;
    architecture: string;
    python_version: string;
    hostname: string;
  };
  resources: {
    cpu: {
      count: number;
      count_logical: number;
      usage_percent: number;
    };
    memory: {
      total: number;
      available: number;
      used: number;
      usage_percent: number;
    };
    disk: {
      total: number;
      free: number;
      used: number;
      usage_percent: number;
    };
  };
  database: {
    servers_count: number;
    metrics_count: number;
    active_alerts_count: number;
    enabled_alert_rules_count: number;
    connection_status: string;
  };
  redis: {
    connected_clients: number;
    used_memory_human: string;
    uptime_days: number;
    status: string;
  };
  background_tasks: {
    running: boolean;
    active_tasks: number;
  };
}

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  timestamp: string;
  uptime: string;
  system: {
    platform: string;
    python_version: string;
    cpu_count: number;
    memory_total: number;
    memory_available: number;
  };
  checks: {
    database: any;
    redis: any;
    background_tasks: any;
  };
}

export interface Alert {
  id: number;
  alert_rule_id: number;
  server_id: number;
  message: string;
  severity: string;
  status: string;
  triggered_at: string;
  resolved_at?: string;
}

export interface AlertRule {
  id: number;
  name: string;
  description?: string;
  metric_type: string;
  metric_name: string;
  condition: string;
  threshold: number;
  severity: string;
  enabled: boolean;
  created_at: string;
}

// Auth API
export const authAPI = {
  login: (data: LoginRequest) => {
    const formData = new URLSearchParams();
    formData.append('username', data.username);
    formData.append('password', data.password);
    return api.post<LoginResponse>('/api/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
  },
  register: (data: any) => api.post('/api/auth/register', data),
  getProfile: () => api.get('/api/auth/me'),
};

// Servers API
export const serversAPI = {
  getServers: () => api.get<Server[]>('/api/servers'),
  getServer: (id: number) => api.get<Server>(`/api/servers/${id}`),
  createServer: (data: any) => api.post<Server>('/api/servers', data),
  updateServer: (id: number, data: any) => api.put<Server>(`/api/servers/${id}`, data),
  deleteServer: (id: number) => api.delete(`/api/servers/${id}`),
  getServerMetrics: (id: number, params?: any) => api.get(`/api/servers/${id}/metrics`, { params }),
  sendCommand: (id: number, command: string) => api.post<Command>(`/api/servers/${id}/command`, { command }),
  getServerCommands: (id: number, params?: any) => api.get<Command[]>(`/api/servers/${id}/commands`, { params }),
  getCommandStatus: (id: number) => api.get<Command>(`/api/commands/${id}/status`),
};

// Alerts API
export const alertsAPI = {
  getAlerts: () => api.get<Alert[]>('/api/alerts'),
  getAlert: (id: number) => api.get<Alert>(`/api/alerts/${id}`),
  updateAlert: (id: number, data: any) => api.put<Alert>(`/api/alerts/${id}`, data),
  getAlertRules: () => api.get<AlertRule[]>('/api/alerts/rules'),
  createAlertRule: (data: any) => api.post<AlertRule>('/api/alerts/rules', data),
  updateAlertRule: (id: number, data: any) => api.put<AlertRule>(`/api/alerts/rules/${id}`, data),
  deleteAlertRule: (id: number) => api.delete(`/api/alerts/rules/${id}`),
};

// System API
export const systemAPI = {
  getHealth: () => api.get<HealthStatus>('/health'),
  getSystemInfo: () => api.get<SystemInfo>('/api/system/info'),
  getMetrics: () => api.get('/metrics'),
};
