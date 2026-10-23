import axios from "axios";

const envUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
const API_BASE_URL = envUrl.endsWith("/api/v1") ? envUrl : `${envUrl.replace(/\/$/, "")}/api/v1`;

const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("izone_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("izone_token");
      localStorage.removeItem("izone_user");
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default api;

export function apiErrorMessage(error, fallback = "Something went wrong. Please try again.") {
  return error?.response?.data?.detail || fallback;
}
