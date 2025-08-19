export interface DataService {
  testConnection(): Promise<boolean>;
  getPositions(): Promise<position[]>;
  disconnect(): Promise<void>;
}

export interface DatabaseConfig {
  authType: string;
  server: string;
  port: string;
  database: string;
  encrypt: string;
  trustServerCertificate: string;
  username?: string;
  password?: string;
  azureUser?: string;
  azurePassword?: string;
  azureClientId?: string;
}
