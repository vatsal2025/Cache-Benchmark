import axios from "axios";
import { useAuthStore } from "./store";

const BASE = import.meta.env.VITE_API_URL || "";

export const apiClient = axios.create({ baseURL: BASE });

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(err);
  }
);

// Auth
export const login = (clientId: string, clientSecret: string) =>
  apiClient.post("/auth/token", { client_id: clientId, client_secret: clientSecret });

export const register = (name: string, email: string, roleTier = "standard") =>
  apiClient.post("/auth/register", { name, email, role_tier: roleTier, tos_accepted: true });

// Overview
export const fetchOverview = () => apiClient.get("/v1/overview").then((r) => r.data);

// CAPTCHAs
export const fetchCaptchas = (params?: Record<string, string>) =>
  apiClient.get("/v1/captchas", { params }).then((r) => r.data);

export const fetchCaptcha = (id: string) =>
  apiClient.get(`/v1/captchas/${id}`).then((r) => r.data);

export const submitCaptcha = (data: Record<string, unknown>) =>
  apiClient.post("/v1/captchas", data).then((r) => r.data);

export const confirmUpload = (id: string) =>
  apiClient.post(`/v1/captchas/${id}/confirm-upload`).then((r) => r.data);

export const uploadAsset = (id: string, file: File) => {
  const fd = new FormData();
  fd.append("file", file);
  return apiClient.post(`/v1/captchas/${id}/upload-asset`, fd).then((r) => r.data);
};

export const fetchAttackResults = (captchaId: string) =>
  apiClient.get(`/v1/captchas/${captchaId}/attacks`).then((r) => r.data);

export const runAttacks = (captchaId: string, data: Record<string, unknown>) =>
  apiClient.post(`/v1/captchas/${captchaId}/attacks`, data).then((r) => r.data);

export const fetchCaptchaHistory = (captchaId: string) =>
  apiClient.get(`/v1/captchas/${captchaId}/history`).then((r) => r.data);

// Experiments
export const fetchExperiments = () =>
  apiClient.get("/v1/experiments").then((r) => r.data);

export const fetchExperiment = (id: string) =>
  apiClient.get(`/v1/experiments/${id}`).then((r) => r.data);

export const createExperiment = (data: Record<string, unknown>) =>
  apiClient.post("/v1/experiments", data).then((r) => r.data);

export const startExperiment = (id: string) =>
  apiClient.post(`/v1/experiments/${id}/start`).then((r) => r.data);

export const fetchScorecard = (id: string) =>
  apiClient.get(`/v1/experiments/${id}/scorecard`).then((r) => r.data);

export const fetchClearanceRates = (id: string) =>
  apiClient.get(`/v1/experiments/${id}/clearance-rates`).then((r) => r.data);

export const uploadLabels = (experimentId: string, file: File) => {
  const fd = new FormData();
  fd.append("file", file);
  return apiClient.post(`/v1/experiments/${experimentId}/labels`, fd).then((r) => r.data);
};

// Backtests
export const fetchBacktests = (experimentId: string) =>
  apiClient.get(`/v1/experiments/${experimentId}/backtests`).then((r) => r.data);

export const fetchAlerts = () =>
  apiClient.get("/v1/alerts").then((r) => r.data);

export const resolveAlert = (alertId: string) =>
  apiClient.post(`/v1/alerts/${alertId}/resolve`).then((r) => r.data);

// Reports
export const downloadScorecardJson = (experimentId: string) =>
  `${BASE}/v1/reports/experiments/${experimentId}/scorecard.json`;

export const downloadScorecardPdf = (experimentId: string) =>
  `${BASE}/v1/reports/experiments/${experimentId}/scorecard.pdf`;
