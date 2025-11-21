/**
 * API Client
 * Configured Axios instance with interceptors for all API requests
 */

import axios from 'axios';
import { API_CONFIG } from './config';
import { authRequestInterceptor } from './interceptors/authInterceptor';
import {
  loggingRequestInterceptor,
  loggingResponseInterceptor,
} from './interceptors/loggingInterceptor';
import { errorResponseInterceptor } from './interceptors/errorInterceptor';

// Create axios instance
export const apiClient = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
  paramsSerializer: {
    indexes: null, // Use format: pages=1&pages=2&pages=3 (FastAPI compatible)
  },
});

// Request interceptors
apiClient.interceptors.request.use(authRequestInterceptor);
apiClient.interceptors.request.use(loggingRequestInterceptor);

// Response interceptors
apiClient.interceptors.response.use(
  loggingResponseInterceptor,
  errorResponseInterceptor
);
