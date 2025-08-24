import os
import logging
from flask import Flask, jsonify, request
from outlook_service import outlook_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        }
    )


@app.post("/api/email/start")
def start_email_monitoring():
    """Start email monitoring - uses specific email if provided, otherwise defaults to first account"""
    try:
        data = request.get_json(silent=True)  # silent=True allows empty body
        email_address = data.get('email_address') if data else None
        
        if email_address:
            logger.info(f"Starting email monitoring for: {email_address}")
            connection_result = outlook_service.connect(email_address)
        else:
            logger.info("Starting email monitoring with default Outlook account")
            connection_result = outlook_service.connect_default()
        
        # Start monitoring
        monitoring_result = outlook_service.start_monitoring()
        
        return jsonify({
            "connection": connection_result,
            "monitoring": monitoring_result
        })
        
    except Exception as e:
        logger.error(f"Error starting email monitoring: {e}")
        return jsonify({"error": str(e)}), 500


@app.post("/api/email/stop")
def stop_email_monitoring():
    """Stop email monitoring"""
    try:
        logger.info("Stopping email monitoring")
        
        # Stop monitoring
        monitoring_result = outlook_service.stop_monitoring()
        
        # Disconnect from Outlook
        disconnect_result = outlook_service.disconnect()
        
        return jsonify({
            "monitoring": monitoring_result,
            "disconnection": disconnect_result
        })
        
    except Exception as e:
        logger.error(f"Error stopping email monitoring: {e}")
        return jsonify({"error": str(e)}), 500


@app.get("/api/email/status")
def get_email_status():
    """Get current email monitoring status"""
    try:
        status = outlook_service.get_status()
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting email status: {e}")
        return jsonify({"error": str(e)}), 500


@app.get("/api/email/recent")
def get_recent_emails():
    """Get recent emails for testing"""
    try:
        limit = request.args.get('limit', 10, type=int)
        emails = outlook_service.get_recent_emails(limit)
        return jsonify({"emails": emails})
        
    except Exception as e:
        logger.error(f"Error getting recent emails: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
