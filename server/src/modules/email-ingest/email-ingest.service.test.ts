import { EmailIngestService } from "./email-ingest.service";
import { EmailConfig } from "./types";

// Mock dependencies
jest.mock("imap");
jest.mock("mailparser");
jest.mock("fs-extra");
jest.mock("crypto");

describe("EmailIngestService", () => {
  let service: EmailIngestService;
  let mockConfig: EmailConfig;

  beforeEach(() => {
    mockConfig = {
      host: "test.example.com",
      port: 993,
      secure: true,
      username: "test@example.com",
      password: "testpassword",
      folder: "INBOX",
    };

    service = new EmailIngestService(mockConfig, "/test/storage");
  });

  describe("constructor", () => {
    it("should create service with correct configuration", () => {
      expect(service).toBeInstanceOf(EmailIngestService);
    });
  });

  describe("pollMailbox", () => {
    it("should return result with correct structure", async () => {
      // This is a basic test - in a real implementation you'd mock the IMAP library
      // and test the actual polling logic
      const result = await service.pollMailbox();

      expect(result).toHaveProperty("processedCount");
      expect(result).toHaveProperty("savedFiles");
      expect(result).toHaveProperty("errors");
      expect(Array.isArray(result.savedFiles)).toBe(true);
      expect(Array.isArray(result.errors)).toBe(true);
    });
  });
});
