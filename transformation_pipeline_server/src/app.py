import os
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from .database import init_database, get_db_service, create_database_if_not_exists, BaseModule
from .modules import get_module_registry, populate_database_with_modules

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Enable CORS for frontend integration
CORS(app, origins=["http://localhost:5002", "http://localhost:3000"], 
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"])

# Initialize database and services
try:
    logger.info("ETO Transformation Pipeline Server starting up...")
    
    # Initialize database
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    # Create database if it doesn't exist
    create_database_if_not_exists(database_url)
    
    # Initialize database service
    init_database(database_url)
    logger.info("Database initialized successfully")
    
    logger.info("All services initialized successfully")
    
except Exception as e:
    logger.error(f"Failed to initialize services: {e}")
    logger.error("Server will start but some functionality may be limited")

@app.get("/")
def hello_world():
    return jsonify({
        "message": "Hello from ETO Transformation Pipeline Server!",
        "version": "1.0.0",
        "port": int(os.environ.get("PORT", "8090"))
    })

@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "eto-transformation-pipeline-server",
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "port": int(os.environ.get("PORT", "8090"))
    })

# Module Management Endpoints

@app.post("/api/modules/populate")
def populate_modules():
    """Populate database with all registered base modules"""
    try:
        success = populate_database_with_modules()
        if success:
            return jsonify({
                "success": True,
                "message": "Database populated with base modules successfully"
            })
        else:
            return jsonify({
                "success": False,
                "message": "Failed to populate database with modules"
            }), 500
    except Exception as e:
        logger.error(f"Error populating modules: {e}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

@app.get("/api/modules")
def get_modules():
    """Get all available base modules from database"""
    try:
        db_service = get_db_service()
        if not db_service:
            return jsonify({
                "success": False,
                "message": "Database service not available"
            }), 500
        
        session = db_service.get_session()
        try:
            modules = session.query(BaseModule).filter(BaseModule.is_active == True).all()
            
            # Convert to frontend format
            modules_data = []
            for module in modules:
                import json
                
                # Parse dynamic node configurations if they exist
                dynamic_inputs = None
                dynamic_outputs = None
                
                if module.dynamic_inputs:
                    try:
                        dynamic_inputs = json.loads(module.dynamic_inputs)
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                if module.dynamic_outputs:
                    try:
                        dynamic_outputs = json.loads(module.dynamic_outputs)
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                module_data = {
                    "id": module.id,
                    "name": module.name,
                    "description": module.description,
                    "category": module.category or "Text Processing",
                    "color": module.color or "#3B82F6",
                    "version": module.version,
                    "inputs": json.loads(module.input_schema),
                    "outputs": json.loads(module.output_schema),
                    "config": json.loads(module.config_schema) if module.config_schema else [],
                    "maxInputs": module.max_inputs,
                    "maxOutputs": module.max_outputs,
                }
                
                # Add dynamic node configurations if they exist
                if dynamic_inputs:
                    module_data["dynamicInputs"] = dynamic_inputs
                
                if dynamic_outputs:
                    module_data["dynamicOutputs"] = dynamic_outputs
                
                modules_data.append(module_data)
            
            return jsonify({
                "success": True,
                "modules": modules_data
            })
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error getting modules: {e}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

@app.post("/api/modules/<module_id>/execute")
def execute_module(module_id):
    """Execute a specific module"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "Request body required"
            }), 400
        
        inputs = data.get('inputs', {})
        config = data.get('config', {})
        output_names = data.get('output_names', None)  # For variable output modules
        
        registry = get_module_registry()
        result = registry.execute_module(module_id, inputs, config, output_names)
        
        return jsonify({
            "success": True,
            "outputs": result
        })
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "message": f"Module error: {str(e)}"
        }), 404
    except Exception as e:
        logger.error(f"Error executing module {module_id}: {e}")
        return jsonify({
            "success": False,
            "message": f"Execution error: {str(e)}"
        }), 500

@app.post("/api/modules/<module_id>/outputs")
def get_dynamic_outputs(module_id):
    """Get dynamic outputs for a module based on configuration"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "Request body with config required"
            }), 400
        
        config = data.get('config', {})
        
        registry = get_module_registry()
        module = registry.get_module(module_id)
        
        if not module:
            return jsonify({
                "success": False,
                "message": f"Module not found: {module_id}"
            }), 404
        
        # Get dynamic outputs based on config
        outputs = module.get_dynamic_outputs(config)
        
        return jsonify({
            "success": True,
            "outputs": outputs,
            "supports_dynamic": module.supports_dynamic_outputs()
        })
        
    except Exception as e:
        logger.error(f"Error getting dynamic outputs for module {module_id}: {e}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8090"))
    app.run(host="0.0.0.0", port=port, debug=False)