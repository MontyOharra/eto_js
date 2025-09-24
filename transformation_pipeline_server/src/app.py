import os
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from .database import init_database, get_db_service, create_database_if_not_exists, BaseModule
from .modules import get_module_registry, populate_database_with_modules
from .services import get_pipeline_analyzer, get_pipeline_executor, PipelineAnalysisError, PipelineExecutionError
from .services.simple_pipeline_execution import get_simple_pipeline_executor
from .services.step_based_execution import get_step_based_pipeline_executor

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
            
            # Convert to frontend format using new schema
            modules_data = []
            for module in modules:
                import json
                
                try:
                    # Parse the backend configurations directly
                    input_config = {"nodes": [], "dynamic": None, "allowedTypes": []}
                    output_config = {"nodes": [], "dynamic": None, "allowedTypes": []}
                    config_schema = []
                    
                    # Get the actual string values from the database row
                    input_config_str = getattr(module, 'input_config', None)
                    output_config_str = getattr(module, 'output_config', None)
                    config_schema_str = getattr(module, 'config_schema', None)
                    
                    if input_config_str and isinstance(input_config_str, str):
                        try:
                            parsed_input = json.loads(input_config_str)
                            if parsed_input and isinstance(parsed_input, dict):
                                input_config = parsed_input
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(f"Failed to parse input_config for module {module.id}: {e}")
                    
                    if output_config_str and isinstance(output_config_str, str):
                        try:
                            parsed_output = json.loads(output_config_str)
                            if parsed_output and isinstance(parsed_output, dict):
                                output_config = parsed_output
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(f"Failed to parse output_config for module {module.id}: {e}")
                    
                    if config_schema_str and isinstance(config_schema_str, str):
                        try:
                            parsed_config = json.loads(config_schema_str)
                            if parsed_config and isinstance(parsed_config, list):
                                config_schema = parsed_config
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(f"Failed to parse config_schema for module {module.id}: {e}")
                    
                    # Return the exact backend NodeConfiguration objects
                    module_data = {
                        "id": module.id,
                        "name": module.name,
                        "description": module.description or "",
                        "category": module.category or "Text Processing",
                        "color": module.color or "#3B82F6",
                        "version": module.version or "1.0.0",
                        # Direct backend schema format
                        "inputConfig": input_config,
                        "outputConfig": output_config,
                        "config": config_schema
                    }
                    
                    modules_data.append(module_data)
                    
                except (json.JSONDecodeError, TypeError) as e:
                    logger.error(f"Error parsing module {module.id} configuration: {e}")
                    # Skip malformed modules
                    continue
            
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


# Pipeline Execution Endpoints

@app.post("/api/pipeline/analyze")
def analyze_pipeline():
    """Analyze a pipeline for execution planning with step-based algorithm"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "Request body required"
            }), 400
        
        modules = data.get('modules', [])
        connections = data.get('connections', [])
        input_definitions = data.get('input_definitions', [])
        output_definitions = data.get('output_definitions', [])
        
        if not modules and not input_definitions and not output_definitions:
            return jsonify({
                "success": False,
                "message": "At least one module or I/O definition is required"
            }), 400
        
        analyzer = get_pipeline_analyzer()
        result = analyzer.analyze_pipeline_with_steps(modules, connections, input_definitions, output_definitions)
        
        return jsonify(result)
        
    except PipelineAnalysisError as e:
        return jsonify({
            "success": False,
            "message": f"Analysis error: {str(e)}"
        }), 400
    except Exception as e:
        logger.error(f"Error analyzing pipeline: {e}")
        return jsonify({
            "success": False,
            "message": f"Analysis failed: {str(e)}"
        }), 500

@app.post("/api/pipeline/execute")
def execute_pipeline():
    """Execute a complete transformation pipeline with clean separation"""
    try:
        logger.info("Pipeline execution request received")
        
        data = request.get_json()
        if not data:
            logger.error("No request body provided")
            return jsonify({
                "success": False,
                "message": "Request body required"
            }), 400
        
        logger.info(f"Request data keys: {list(data.keys())}")
        
        modules = data.get('modules', [])
        connections = data.get('connections', [])
        input_data = data.get('inputData', {})  # Changed from baseInputs to inputData
        
        logger.info(f"Received {len(modules)} modules, {len(connections)} connections")
        logger.info(f"Input data: {input_data}")
        
        if not modules:
            logger.error("No modules provided in request")
            return jsonify({
                "success": False,
                "message": "Modules list is required"
            }), 400
        
        # Step 1: Analyze pipeline to get transformation steps
        logger.info("Step 1: Analyzing pipeline...")
        analyzer = get_pipeline_analyzer()
        analysis_result = analyzer.analyze_pipeline(modules, connections)
        
        if not analysis_result['success']:
            logger.error("Pipeline analysis failed")
            return jsonify({
                "success": False,
                "message": "Pipeline analysis failed"
            }), 400
        
        transformation_steps = analysis_result['transformation_steps']
        field_mappings = analysis_result['field_mappings']
        
        logger.info(f"Analysis complete: {len(transformation_steps)} transformation steps")
        logger.info(f"Field mappings: {field_mappings}")
        
        # Step 2: Execute pipeline with clean separation
        logger.info("Step 2: Executing transformations...")
        executor = get_simple_pipeline_executor()
        
        final_outputs = executor.execute_pipeline(
            transformation_steps=transformation_steps,
            input_data=input_data,
            field_mappings=field_mappings
        )
        
        logger.info("Pipeline execution completed successfully")
        return jsonify({
            "success": True,
            "analysis": {
                "transformation_steps": transformation_steps,
                "field_mappings": field_mappings
            },
            "outputs": final_outputs
        })
        
    except PipelineAnalysisError as e:
        logger.error(f"Pipeline analysis error: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Analysis error: {str(e)}"
        }), 400
    except Exception as e:
        logger.error(f"Unexpected error executing pipeline: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Execution failed: {str(e)}"
        }), 500

@app.post("/api/pipeline/validate")
def validate_pipeline():
    """Validate a pipeline structure and requirements"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "Request body required"
            }), 400
        
        modules = data.get('modules', [])
        connections = data.get('connections', [])
        
        if not modules:
            return jsonify({
                "success": False,
                "message": "Modules list is required"
            }), 400
        
        executor = get_pipeline_executor()
        result = executor.validate_execution_requirements(modules, connections)
        
        return jsonify({
            "success": True,
            "validation": result
        })
        
    except Exception as e:
        logger.error(f"Error validating pipeline: {e}")
        return jsonify({
            "success": False,
            "message": f"Validation failed: {str(e)}"
        }), 500

@app.post("/api/pipeline/execute-steps")
def execute_pipeline_with_steps():
    """Execute a pipeline using step-based dependency analysis with parallel processing"""
    try:
        logger.info("Step-based pipeline execution request received")
        
        data = request.get_json()
        if not data:
            logger.error("No request body provided")
            return jsonify({
                "success": False,
                "message": "Request body required"
            }), 400
        
        logger.info(f"Request data keys: {list(data.keys())}")
        
        modules = data.get('modules', [])
        connections = data.get('connections', [])
        input_definitions = data.get('input_definitions', [])
        output_definitions = data.get('output_definitions', [])
        input_data = data.get('input_data', {})  # Node ID -> value mapping
        
        logger.info(f"Received {len(modules)} modules, {len(connections)} connections")
        logger.info(f"Input definitions: {len(input_definitions)}, Output definitions: {len(output_definitions)}")
        logger.info(f"Input data keys: {list(input_data.keys())}")
        
        if not modules and not input_definitions:
            logger.error("No modules or input definitions provided")
            return jsonify({
                "success": False,
                "message": "Modules or input definitions are required"
            }), 400
        
        # Step 1: Analyze pipeline to get step-based execution plan
        logger.info("Step 1: Analyzing pipeline with steps...")
        analyzer = get_pipeline_analyzer()
        analysis_result = analyzer.analyze_pipeline_with_steps(
            modules, connections, input_definitions, output_definitions
        )
        
        if not analysis_result['success']:
            logger.error("Step-based pipeline analysis failed")
            return jsonify({
                "success": False,
                "message": "Pipeline analysis failed"
            }), 400
        
        steps = analysis_result['steps']
        output_endpoints = analysis_result['output_endpoints']
        
        logger.info(f"Analysis complete: {len(steps)} steps, {len(output_endpoints)} output endpoints")
        
        # Step 2: Execute pipeline using step-based executor
        logger.info("Step 2: Executing pipeline with steps...")
        import asyncio
        executor = get_step_based_pipeline_executor()
        
        # Run async executor in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            final_outputs = loop.run_until_complete(
                executor.execute_pipeline_with_steps(
                    steps=steps,
                    connections=connections,
                    input_data=input_data,
                    output_endpoints=output_endpoints
                )
            )
        finally:
            loop.close()
        
        logger.info("Step-based pipeline execution completed successfully")
        return jsonify({
            "success": True,
            "analysis": {
                "steps": steps,
                "output_endpoints": output_endpoints,
                "total_steps": analysis_result['total_steps'],
                "parallel_opportunities": analysis_result['parallel_opportunities']
            },
            "outputs": final_outputs
        })
        
    except PipelineAnalysisError as e:
        logger.error(f"Pipeline analysis error: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Analysis error: {str(e)}"
        }), 400
    except Exception as e:
        logger.error(f"Unexpected error executing step-based pipeline: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Execution failed: {str(e)}"
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8090"))
    app.run(host="0.0.0.0", port=port, debug=False)