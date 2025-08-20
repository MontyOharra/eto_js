import * as Imap from "imap";
import { simpleParser } from "mailparser";
import * as crypto from "crypto";
import * as fs from "fs-extra";
import * as path from "path";
import {
  EmailConfig,
  EmailMessage,
  EmailAttachment,
  ProcessedAttachment,
  EmailIngestResult,
} from "./types";
import { logger } from "../../utils/logger";

export class EmailIngestService {
  private config: EmailConfig;
  private storagePath: string;

  constructor(config: EmailConfig, storagePath: string) {
    this.config = config;
    this.storagePath = storagePath;
  }

  async pollMailbox(): Promise<EmailIngestResult> {
    const result: EmailIngestResult = {
      processedCount: 0,
      savedFiles: [],
      errors: [],
    };

    return new Promise((resolve, reject) => {
      const imap = new Imap({
        host: this.config.host,
        port: this.config.port,
        tls: this.config.secure,
        user: this.config.username,
        password: this.config.password,
        tlsOptions: { rejectUnauthorized: false },
      });

      imap.once("ready", () => {
        logger.info("IMAP connection ready");
        this.openInbox(imap, result, resolve, reject);
      });

      imap.once("error", (err) => {
        logger.error("IMAP error:", err);
        result.errors.push(`IMAP connection error: ${err.message}`);
        reject(err);
      });

      imap.once("end", () => {
        logger.info("IMAP connection ended");
      });

      imap.connect();
    });
  }

  private openInbox(
    imap: Imap,
    result: EmailIngestResult,
    resolve: (value: EmailIngestResult) => void,
    reject: (reason: any) => void
  ) {
    imap.openBox(this.config.folder, false, (err, box) => {
      if (err) {
        logger.error("Error opening inbox:", err);
        result.errors.push(`Error opening inbox: ${err.message}`);
        imap.end();
        reject(err);
        return;
      }

      logger.info(`Opened inbox: ${box.messages.total} messages`);

      if (box.messages.total === 0) {
        imap.end();
        resolve(result);
        return;
      }

      // Search for unread messages
      imap.search(["UNSEEN"], (err, uids) => {
        if (err) {
          logger.error("Error searching messages:", err);
          result.errors.push(`Error searching messages: ${err.message}`);
          imap.end();
          reject(err);
          return;
        }

        if (uids.length === 0) {
          logger.info("No unread messages found");
          imap.end();
          resolve(result);
          return;
        }

        logger.info(`Found ${uids.length} unread messages`);
        this.processMessages(imap, uids, result, resolve, reject);
      });
    });
  }

  private processMessages(
    imap: Imap,
    uids: number[],
    result: EmailIngestResult,
    resolve: (value: EmailIngestResult) => void,
    reject: (reason: any) => void
  ) {
    const fetch = imap.fetch(uids, { bodies: "", struct: true });

    fetch.on("message", (msg, seqno) => {
      logger.info(`Processing message ${seqno}`);
      let messageData = "";

      msg.on("body", (stream, info) => {
        stream.on("data", (chunk) => {
          messageData += chunk.toString("utf8");
        });
      });

      msg.once("end", async () => {
        try {
          const parsed = await simpleParser(messageData);
          const emailMessage: EmailMessage = {
            id: parsed.messageId || `msg_${Date.now()}_${seqno}`,
            subject: parsed.subject || "No Subject",
            from: parsed.from?.text || "Unknown",
            to: parsed.to?.map((addr) => addr.text) || [],
            date: parsed.date || new Date(),
            attachments: [],
          };

          // Process attachments
          if (parsed.attachments && parsed.attachments.length > 0) {
            for (const attachment of parsed.attachments) {
              if (attachment.contentType === "application/pdf") {
                const emailAttachment: EmailAttachment = {
                  filename:
                    attachment.filename || `attachment_${Date.now()}.pdf`,
                  contentType: attachment.contentType,
                  size: attachment.size,
                  content: attachment.content,
                };

                try {
                  const processed = await this.saveAttachment(
                    emailAttachment,
                    emailMessage.id
                  );
                  if (processed) {
                    result.savedFiles.push(processed);
                    result.processedCount++;
                  }
                } catch (error) {
                  const errorMsg = `Error processing attachment ${emailAttachment.filename}: ${error}`;
                  logger.error(errorMsg);
                  result.errors.push(errorMsg);
                }
              }
            }
          }

          // Mark message as read
          imap.addFlags(uids[seqno - 1], ["\\Seen"], (err) => {
            if (err) {
              logger.error("Error marking message as read:", err);
            }
          });
        } catch (error) {
          const errorMsg = `Error parsing message ${seqno}: ${error}`;
          logger.error(errorMsg);
          result.errors.push(errorMsg);
        }
      });
    });

    fetch.once("error", (err) => {
      logger.error("Fetch error:", err);
      result.errors.push(`Fetch error: ${err.message}`);
      imap.end();
      reject(err);
    });

    fetch.once("end", () => {
      logger.info("Finished processing messages");
      imap.end();
      resolve(result);
    });
  }

  private async saveAttachment(
    attachment: EmailAttachment,
    messageId: string
  ): Promise<ProcessedAttachment | null> {
    try {
      // Calculate SHA-256 hash
      const hash = crypto.createHash("sha256");
      hash.update(attachment.content);
      const sha256 = hash.digest("hex");

      // Create filename based on hash
      const fileExtension = path.extname(attachment.filename);
      const fileName = `${sha256}${fileExtension}`;
      const filePath = path.join(this.storagePath, fileName);

      // Check if file already exists
      if (await fs.pathExists(filePath)) {
        logger.info(`File already exists: ${fileName}`);
        return {
          filename: attachment.filename,
          contentType: attachment.contentType,
          size: attachment.size,
          sha256,
          filePath,
          messageId,
        };
      }

      // Save file
      await fs.writeFile(filePath, attachment.content);
      logger.info(`Saved attachment: ${fileName}`);

      return {
        filename: attachment.filename,
        contentType: attachment.contentType,
        size: attachment.size,
        sha256,
        filePath,
        messageId,
      };
    } catch (error) {
      logger.error("Error saving attachment:", error);
      throw error;
    }
  }
}
