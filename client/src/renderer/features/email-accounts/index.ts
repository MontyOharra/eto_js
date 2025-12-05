/**
 * Email Accounts Feature
 * Public exports for email account management
 */

// API hooks
export { useEmailAccountsApi } from './api/hooks';

// Types
export type {
  EmailAccountSummary,
  EmailAccountResponse,
  EmailAccountListResponse,
  CreateEmailAccountRequest,
  UpdateEmailAccountRequest,
  ValidateConnectionRequest,
  ValidationResultResponse,
  ImapProviderSettings,
  PasswordCredentials,
  FolderListResponse,
} from './api/types';
