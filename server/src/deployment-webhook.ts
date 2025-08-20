import express from "express";
import { exec } from "child_process";
import { promisify } from "util";
import * as path from "path";
import { logger } from "./utils/logger";

const execAsync = promisify(exec);

export function createDeploymentWebhook(app: express.Application) {
  const webhookSecret =
    process.env.DEPLOY_WEBHOOK_SECRET || "your-webhook-secret";
  const repoUrl = process.env.GIT_REPO_URL || "";
  const deployBranch = process.env.DEPLOY_BRANCH || "main";
  const appDir = process.env.APP_DIR || "C:\\apps\\eto\\server";

  app.post("/api/deploy/webhook", async (req, res) => {
    try {
      // Verify webhook secret (basic security)
      const authHeader = req.headers.authorization;
      if (authHeader !== `Bearer ${webhookSecret}`) {
        logger.warn("Invalid webhook secret received");
        return res.status(401).json({ error: "Unauthorized" });
      }

      const { ref, repository } = req.body;

      // Only deploy from main branch
      if (ref !== `refs/heads/${deployBranch}`) {
        logger.info(`Ignoring deployment for branch: ${ref}`);
        return res.json({ message: "Ignored - not main branch" });
      }

      logger.info(`Deployment triggered for ${repository} at ${ref}`);

      // Start deployment process
      deployToServer(repoUrl, deployBranch, appDir)
        .then(() => {
          logger.info("Deployment completed successfully");
        })
        .catch((error) => {
          logger.error("Deployment failed:", error);
        });

      // Respond immediately
      res.json({
        message: "Deployment started",
        repository,
        ref,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      logger.error("Webhook error:", error);
      res.status(500).json({ error: "Internal server error" });
    }
  });

  // Health check for deployment status
  app.get("/api/deploy/status", (req, res) => {
    res.json({
      status: "ready",
      lastDeployment: new Date().toISOString(),
      repository: repoUrl,
      branch: deployBranch,
    });
  });
}

async function deployToServer(
  repoUrl: string,
  branch: string,
  appDir: string
): Promise<void> {
  try {
    logger.info("Starting deployment process...");

    // Change to app directory
    process.chdir(appDir);

    // Stop the service
    logger.info("Stopping ETO service...");
    try {
      await execAsync('powershell -Command "Stop-Service eto-server -Force"');
      await new Promise((resolve) => setTimeout(resolve, 3000)); // Wait for service to stop
    } catch (error) {
      logger.warn("Service was not running or could not be stopped");
    }

    // Pull latest changes
    logger.info("Pulling latest changes from repository...");
    await execAsync(`git fetch origin ${branch}`);
    await execAsync(`git reset --hard origin/${branch}`);

    // Install dependencies
    logger.info("Installing dependencies...");
    await execAsync("npm ci --production");

    // Generate Prisma client
    logger.info("Generating Prisma client...");
    await execAsync("npm run prisma:generate");

    // Run database migrations
    logger.info("Running database migrations...");
    await execAsync("npm run prisma:migrate");

    // Build the application
    logger.info("Building application...");
    await execAsync("npm run build");

    // Copy files to bin directory
    logger.info("Copying files to bin directory...");
    await execAsync("xcopy dist\\* bin\\ /E /Y");
    await execAsync("copy package.json bin\\");
    await execAsync("xcopy node_modules bin\\node_modules\\ /E /Y");

    // Copy environment file if it exists
    try {
      await execAsync("copy .env bin\\");
      logger.info("Environment file copied");
    } catch (error) {
      logger.warn("No .env file found, using existing one");
    }

    // Start the service
    logger.info("Starting ETO service...");
    await execAsync('powershell -Command "Start-Service eto-server"');

    // Wait a moment and check service status
    await new Promise((resolve) => setTimeout(resolve, 5000));
    const { stdout } = await execAsync(
      'powershell -Command "Get-Service eto-server | Select-Object Status"'
    );

    if (stdout.includes("Running")) {
      logger.info("Service started successfully");
    } else {
      throw new Error("Service failed to start");
    }

    logger.info("Deployment completed successfully");
  } catch (error) {
    logger.error("Deployment failed:", error);

    // Try to restart service if it was stopped
    try {
      await execAsync('powershell -Command "Start-Service eto-server"');
      logger.info("Service restarted after failed deployment");
    } catch (restartError) {
      logger.error("Failed to restart service:", restartError);
    }

    throw error;
  }
}
