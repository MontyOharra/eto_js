"""
Health Blueprint - Service health checks
"""
from flask import Blueprint, jsonify

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Unified health check with service identification"""
    return jsonify({
        "success": True,
        "service": "Unified ETO Server",
        "status": "healthy",
        "message": "All systems operational"
    }), 200