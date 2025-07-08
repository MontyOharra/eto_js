import { app } from "electron";
import { config } from "dotenv";
import { DatabaseConfig } from "../../@types/database";
import * as keytar from "keytar";

const SERVICE_NAME = "eto-database-config";
const ACCOUNT_NAME = "database-credentials";

export class SecureConfigManager {
  private static config: DatabaseConfig | null = null;

  /**
   * Set database configuration
   * - Dev mode: sets local env variables
   * - Prod mode: saves to OS credential manager
   */
  static async setConfig(config: DatabaseConfig): Promise<void> {
    if (app.isPackaged) {
      // Production: Save to keytar
      await this.saveToKeychain(config);
    } else {
      // Development: Set environment variables
      this.setEnvironmentVariables(config);
    }

    // Cache the config
    this.config = config;
  }

  /**
   * Get database configuration
   * - Dev mode: reads from env variables (via dotenv)
   * - Prod mode: reads from OS credential manager
   */
  static async getConfig(): Promise<DatabaseConfig> {
    if (app.isPackaged) {
      // Production: Load from keytar
      return await this.loadFromKeychain();
    } else {
      // Development: Load from env variables
      return this.loadFromEnv();
    }
  }

  /**
   * Set environment variables from config (dev mode only)
   */
  private static setEnvironmentVariables(config: DatabaseConfig): void {
    process.env.DB_AUTH_TYPE = config.authType;
    process.env.DB_SERVER = config.server;
    process.env.DB_PORT = config.port;
    process.env.DB_NAME = config.database;
    process.env.DB_ENCRYPT = config.encrypt;
    process.env.DB_TRUST_SERVER_CERTIFICATE = config.trustServerCertificate;

    if (config.username) process.env.DB_USER = config.username;
    else delete process.env.DB_USER;

    if (config.password) process.env.DB_PASSWORD = config.password;
    else delete process.env.DB_PASSWORD;

    if (config.azureUser) process.env.DB_AZURE_USER = config.azureUser;
    else delete process.env.DB_AZURE_USER;

    if (config.azurePassword)
      process.env.DB_AZURE_PASSWORD = config.azurePassword;
    else delete process.env.DB_AZURE_PASSWORD;

    if (config.azureClientId)
      process.env.DB_AZURE_CLIENT_ID = config.azureClientId;
    else delete process.env.DB_AZURE_CLIENT_ID;

    console.log("Database configuration set in environment variables");
  }

  static async loadConfig(): Promise<DatabaseConfig> {
    if (this.config) {
      return this.config;
    }

    if (app.isPackaged) {
      // Production: Use OS credential manager
      return await this.loadFromKeychain();
    } else {
      // Development: Use .env file
      return this.loadFromEnv();
    }
  }

  private static async loadFromKeychain(): Promise<DatabaseConfig> {
    try {
      const storedConfig = await keytar.getPassword(SERVICE_NAME, ACCOUNT_NAME);

      if (storedConfig) {
        console.log("Loading database config from OS credential manager");
        this.config = JSON.parse(storedConfig);
        if (!this.config) {
          throw new Error("Invalid config format");
        }
        return this.config;
      } else {
        // First run: create default config and prompt user
        const defaultConfig = this.getDefaultConfig();
        await this.saveToKeychain(defaultConfig);

        console.log("Default database config created in credential manager");
        console.log(
          "Please update your database settings using the app settings menu"
        );

        return defaultConfig;
      }
    } catch (error) {
      console.error("Failed to load config from credential manager:", error);
      return this.getDefaultConfig();
    }
  }

  private static loadFromEnv(): DatabaseConfig {
    config(); // Load .env file

    this.config = {
      authType: process.env.DB_AUTH_TYPE || "windows",
      server: process.env.DB_SERVER || "localhost",
      port: process.env.DB_PORT || "1433",
      database: process.env.DB_NAME || "HTC",
      encrypt: process.env.DB_ENCRYPT || "optional",
      trustServerCertificate: process.env.DB_TRUST_SERVER_CERTIFICATE || "true",
      username: process.env.DB_USER,
      password: process.env.DB_PASSWORD,
      azureUser: process.env.DB_AZURE_USER,
      azurePassword: process.env.DB_AZURE_PASSWORD,
      azureClientId: process.env.DB_AZURE_CLIENT_ID,
    };

    return this.config;
  }

  static async saveToKeychain(config: DatabaseConfig): Promise<void> {
    try {
      await keytar.setPassword(
        SERVICE_NAME,
        ACCOUNT_NAME,
        JSON.stringify(config)
      );
      this.config = config;
      console.log("Database config saved to OS credential manager");
    } catch (error) {
      console.error("Failed to save config to credential manager:", error);
    }
  }

  static async updateConfig(updates: Partial<DatabaseConfig>): Promise<void> {
    const currentConfig = await this.loadConfig();
    const newConfig = { ...currentConfig, ...updates };
    await this.saveToKeychain(newConfig);
  }

  private static getDefaultConfig(): DatabaseConfig {
    return {
      authType: "windows",
      server: "localhost",
      port: "1433",
      database: "HTC",
      encrypt: "optional",
      trustServerCertificate: "true",
    };
  }

  static buildConnectionString(config: DatabaseConfig): string {
    let connectionString = `sqlserver://${config.server}:${config.port};database=${config.database};encrypt=${config.encrypt};trustServerCertificate=${config.trustServerCertificate}`;

    switch (config.authType.toLowerCase()) {
      case "windows":
      case "integrated":
        connectionString += ";integratedSecurity=true";
        break;

      case "sql":
      case "sqlserver":
        if (config.username && config.password) {
          connectionString += `;username=${config.username};password=${config.password}`;
        }
        break;

      case "azure":
      case "azuread":
        if (config.azureUser && config.azurePassword) {
          connectionString += `;username=${config.azureUser};password=${config.azurePassword}`;
        }
        if (config.azureClientId) {
          connectionString += `;clientId=${config.azureClientId}`;
        }
        break;
    }

    return connectionString;
  }
}
