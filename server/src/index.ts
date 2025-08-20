import express from "express";
import cors from "cors";
import helmet from "helmet";
import morgan from "morgan";
import dotenv from "dotenv";
import cron from "node-cron";
import { PrismaClient } from "@prisma/client";
import { EmailIngestService } from "./modules/email-ingest/email-ingest.service";
import { logger } from "./utils/logger";
import { createDeploymentWebhook } from "./deployment-webhook";
import path from "path";

// Load environment variables
dotenv.config();

const app = express();
const port = process.env.PORT || 8080;
const prisma = new PrismaClient();

// Middleware
app.use(helmet());
app.use(cors());
app.use(
  morgan("combined", {
    stream: { write: (message) => logger.info(message.trim()) },
  })
);
app.use(express.json({ limit: "10mb" }));
app.use(express.urlencoded({ extended: true }));

// Health check endpoint
app.get("/health", (req, res) => {
  res.json({
    status: "ok",
    timestamp: new Date().toISOString(),
    service: "eto-server",
  });
});

// Setup deployment webhook
createDeploymentWebhook(app);

// Email ingest configuration
const emailConfig = {
  host: process.env.EMAIL_HOST || "localhost",
  port: parseInt(process.env.EMAIL_PORT || "993"),
  secure: process.env.EMAIL_SECURE === "true",
  username: process.env.EMAIL_USERNAME || "",
  password: process.env.EMAIL_PASSWORD || "",
  folder: process.env.EMAIL_FOLDER || "INBOX",
};

const storagePath =
  process.env.STORAGE_PATH || path.join(process.cwd(), "storage");
const emailIngestService = new EmailIngestService(emailConfig, storagePath);

// Email ingest endpoint
app.post("/api/email/ingest", async (req, res) => {
  try {
    logger.info("Starting email ingest process");
    const result = await emailIngestService.pollMailbox();

    // Save processed files to database
    for (const file of result.savedFiles) {
      await prisma.pdfFile.upsert({
        where: { sha256: file.sha256 },
        update: {},
        create: {
          sha256: file.sha256,
          path: file.filePath,
          receivedAt: new Date(),
          sourceMessageId: file.messageId,
        },
      });
    }

    logger.info(
      `Email ingest completed: ${result.processedCount} files processed`
    );
    res.json({
      success: true,
      result,
    });
  } catch (error) {
    logger.error("Email ingest error:", error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : "Unknown error",
    });
  }
});

// Schedule email ingest (every 5 minutes)
if (process.env.ENABLE_EMAIL_CRON === "true") {
  cron.schedule("*/5 * * * *", async () => {
    try {
      logger.info("Running scheduled email ingest");
      const result = await emailIngestService.pollMailbox();

      // Save processed files to database
      for (const file of result.savedFiles) {
        await prisma.pdfFile.upsert({
          where: { sha256: file.sha256 },
          update: {},
          create: {
            sha256: file.sha256,
            path: file.filePath,
            receivedAt: new Date(),
            sourceMessageId: file.messageId,
          },
        });
      }

      logger.info(
        `Scheduled email ingest completed: ${result.processedCount} files processed`
      );
    } catch (error) {
      logger.error("Scheduled email ingest error:", error);
    }
  });
  logger.info("Email ingest cron job scheduled (every 5 minutes)");
}

// Start server
app.listen(port, () => {
  logger.info(`ETO Server running on port ${port}`);
  logger.info(`Health check available at http://localhost:${port}/health`);
});

// Graceful shutdown
process.on("SIGTERM", async () => {
  logger.info("SIGTERM received, shutting down gracefully");
  await prisma.$disconnect();
  process.exit(0);
});

process.on("SIGINT", async () => {
  logger.info("SIGINT received, shutting down gracefully");
  await prisma.$disconnect();
  process.exit(0);
});
