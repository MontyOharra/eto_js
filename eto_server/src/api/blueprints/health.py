"""
Health Check API Blueprint
Service health monitoring endpoints
"""
from flask import Blueprint, jsonify
from flask_cors import cross_origin
import logging
from datetime import datetime

from ..schemas.common import HealthCheck
from shared.services import ServiceContainer

logger = logging.getLogger(__name__)

# Create blueprint
health_bp = Blueprint('health', __name__, url_prefix='/api')


@health_bp.route('/health', methods=['GET'])
@cross_origin()
def health_check():
    """Basic health check endpoint"""
    try:
        # Test database connection via ServiceContainer
        service_container = ServiceContainer()
        connection_manager = service_container.connection_manager
        db_healthy = True

        if connection_manager:
            db_healthy = connection_manager.test_connection()
        else:
            db_healthy = False
            
        # Create health response
        health_response = HealthCheck(
            service="Unified ETO Server",
            status="healthy" if db_healthy else "degraded",
            message="All systems operational" if db_healthy else "Database connection issues",
            timestamp=datetime.utcnow()
        )
        
        status_code = 200 if db_healthy else 503
        
        return jsonify(health_response.dict()), status_code
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        
        error_response = HealthCheck(
            service="Unified ETO Server",
            status="unhealthy",
            message=f"Health check failed: {str(e)}",
            timestamp=datetime.utcnow()
        )
        
        return jsonify(error_response.dict()), 500


@health_bp.route('/health/detailed', methods=['GET'])
@cross_origin()
def detailed_health_check():
    """Detailed health check with component status"""
    try:
        health_status = {
            "service": "Unified ETO Server",
            "status": "healthy",
            "message": "All systems operational",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {}
        }
        
        overall_healthy = True
        
        # Database health
        try:
            service_container = ServiceContainer()
            connection_manager = service_container.connection_manager
            if connection_manager:
                db_healthy = connection_manager.test_connection()
                health_status["components"]["database"] = {
                    "status": "healthy" if db_healthy else "unhealthy",
                    "message": "Connected" if db_healthy else "Connection failed"
                }
            else:
                db_healthy = False
                health_status["components"]["database"] = {
                    "status": "unhealthy",
                    "message": "Database connection manager not initialized"
                }
                
            overall_healthy = overall_healthy and db_healthy
        except Exception as e:
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "message": f"Database check failed: {str(e)}"
            }
            overall_healthy = False
        
        # Update overall status
        if not overall_healthy:
            health_status["status"] = "degraded"
            health_status["message"] = "Some components are unhealthy"
        
        status_code = 200 if overall_healthy else 503
        return jsonify(health_status), status_code
    
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return jsonify({
            "service": "Unified ETO Server",
            "status": "unhealthy",
            "message": f"Health check failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@health_bp.route('/health/ready', methods=['GET'])
@cross_origin()
def readiness_check():
    """Readiness check for container orchestration"""
    try:
        # Check if all required services are ready
        service_container = ServiceContainer()
        connection_manager = service_container.connection_manager

        if not connection_manager:
            return jsonify({
                "ready": False,
                "message": "Database connection manager not initialized"
            }), 503

        if not connection_manager.test_connection():
            return jsonify({
                "ready": False,
                "message": "Database connection not ready"
            }), 503
        
        return jsonify({
            "ready": True,
            "message": "Service is ready to handle requests"
        }), 200
    
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({
            "ready": False,
            "message": f"Readiness check failed: {str(e)}"
        }), 500


@health_bp.route('/health/live', methods=['GET'])
@cross_origin()
def liveness_check():
    """Liveness check for container orchestration"""
    try:
        # Basic liveness check - just ensure the service is running
        return jsonify({
            "alive": True,
            "message": "Service is alive",
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        return jsonify({
            "alive": False,
            "message": f"Liveness check failed: {str(e)}"
        }), 500


# Export the blueprint
__all__ = ['health_bp']