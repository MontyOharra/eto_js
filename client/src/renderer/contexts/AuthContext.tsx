/**
 * Authentication Context
 *
 * Provides user authentication state and methods throughout the app.
 * Supports:
 * - Auto-login via HTC WhosLoggedIn table
 * - Manual login via username/password
 * - Session management (in-memory only)
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from 'react';
import { apiClient } from '../shared/api/client';

// Types
export interface AuthUser {
  staffEmpId: number;
  username: string; // Staff_Login - used for audit trail (Orders_UpdtLID)
  displayName: string;
  firstName: string;
  lastName: string;
}

export interface AuthSession {
  user: AuthUser;
  loginMethod: 'auto' | 'manual';
  loginTime: Date;
}

interface AuthContextValue {
  session: AuthSession | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<boolean>;
  autoLogin: () => Promise<boolean>;
  logout: () => void;
  clearError: () => void;
}

// Create context with undefined default (must be used within provider)
const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// Provider component
interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isAuthenticated = session !== null;

  // Auto-login using machine credentials
  const autoLogin = useCallback(async (): Promise<boolean> => {
    console.log('[AuthContext] autoLogin() called');
    setIsLoading(true);
    setError(null);

    try {
      // Get machine info from Electron
      console.log('[AuthContext] Getting machine info...');
      const machineInfo = await window.electron.getMachineInfo();
      console.log('[AuthContext] Machine info received:', machineInfo);

      // Call auto-login API
      console.log('[AuthContext] Calling /api/auth/auto-login...');
      const response = await apiClient.post('/api/auth/auto-login', {
        pc_name: machineInfo.pcName,
        pc_lid: machineInfo.pcLid,
      });
      console.log('[AuthContext] Response status:', response.status);

      const data = response.data;
      console.log('[AuthContext] Response data:', data);

      if (data.success && data.user) {
        console.log('[AuthContext] Auto-login successful, setting session...');
        setSession({
          user: {
            staffEmpId: data.user.staff_emp_id,
            username: data.user.username,
            displayName: data.user.display_name,
            firstName: data.user.first_name,
            lastName: data.user.last_name,
          },
          loginMethod: 'auto',
          loginTime: new Date(),
        });
        console.log('[AuthContext] Session set, returning true');
        return true;
      } else {
        // Auto-login failed - not an error, just means manual login needed
        console.log('[AuthContext] Auto-login failed:', data.error);
        return false;
      }
    } catch (err) {
      console.error('[AuthContext] Auto-login error:', err);
      // Don't set error for auto-login failure - it's expected sometimes
      return false;
    } finally {
      console.log('[AuthContext] autoLogin() finally block, setting isLoading=false');
      setIsLoading(false);
    }
  }, []);

  // Manual login with username/password
  const login = useCallback(
    async (username: string, password: string): Promise<boolean> => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await apiClient.post('/api/auth/login', {
          username,
          password,
        });

        const data = response.data;

        if (data.success && data.user) {
          setSession({
            user: {
              staffEmpId: data.user.staff_emp_id,
              username: data.user.username,
              displayName: data.user.display_name,
              firstName: data.user.first_name,
              lastName: data.user.last_name,
            },
            loginMethod: 'manual',
            loginTime: new Date(),
          });
          return true;
        } else {
          setError(data.error || 'Login failed');
          return false;
        }
      } catch (err) {
        console.error('Login error:', err);
        setError('Unable to connect to server');
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  // Logout - clear session
  const logout = useCallback(() => {
    setSession(null);
    setError(null);
  }, []);

  // Clear error message
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const value: AuthContextValue = {
    session,
    isAuthenticated,
    isLoading,
    error,
    login,
    autoLogin,
    logout,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Hook to use auth context
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
}
