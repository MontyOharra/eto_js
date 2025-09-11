"""
ETO Processing API Blueprint
REST endpoints for ETO processing runs and results
"""
from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from pydantic import ValidationError
import logging
from typing import Dict, Any

from ..schemas.eto_processing import (
    EtoRunSummaryResponse,
    EtoRunDetailResponse,
    EtoRunListRequest,
    ReprocessEtoRunRequest,
    SkipEtoRunRequest,
    EtoRunStatsResponse
)
from ..schemas.common import PaginatedResponse
from ...shared.database import get_connection_manager
from ...shared.database.repositories import EtoRunRepository

logger = logging.getLogger(__name__)

# Create blueprint
eto_processing_bp = Blueprint('eto_processing', __name__, url_prefix='/api/eto-runs')

# Initialize repository
connection_manager = get_connection_manager()
if connection_manager:
    eto_run_repo = EtoRunRepository(connection_manager)
else:
    eto_run_repo = None


def handle_validation_error(e: ValidationError) -> Dict[str, Any]:
    """Convert Pydantic validation error to API response"""
    return {
        "success": False,
        "error": "Validation failed",
        "message": "Request data validation failed",
        "details": [
            {
                "field": ".".join(str(x) for x in error["loc"]),
                "error": error["msg"],
                "value": error.get("input")
            }
            for error in e.errors()
        ]
    }


@eto_processing_bp.route('', methods=['GET'])
@cross_origin()
def get_eto_runs():
    """Get ETO processing runs with filtering and pagination"""
    try:
        if not eto_run_repo:
            return jsonify({
                "success": False,
                "error": "Service unavailable",
                "message": "Database connection not available"
            }), 503
        
        # Parse query parameters
        try:
            request_params = EtoRunListRequest(
                status=request.args.get('status'),
                email_id=int(request.args.get('email_id')) if request.args.get('email_id') else None,
                template_id=int(request.args.get('template_id')) if request.args.get('template_id') else None,
                has_errors=request.args.get('has_errors') == 'true' if request.args.get('has_errors') else None,
                page=int(request.args.get('page', 1)),
                limit=int(request.args.get('limit', 20)),
                order_by=request.args.get('order_by', 'created_at'),
                desc=request.args.get('desc', 'true').lower() == 'true'
            )
        except ValidationError as e:
            return jsonify(handle_validation_error(e)), 400
        except ValueError as e:
            return jsonify({
                "success": False,
                "error": "Invalid parameter",
                "message": str(e)
            }), 400
        
        # Calculate offset for pagination
        offset = (request_params.page - 1) * request_params.limit
        
        # Get runs from repository
        runs = eto_run_repo.get_all(
            order_by=request_params.order_by,
            desc=request_params.desc,
            limit=request_params.limit,
            offset=offset
        )
        
        # Get total count for pagination
        total_count = eto_run_repo.count()
        
        # Convert to response format
        run_summaries = []
        for run in runs:
            # Get PDF filename from relationship if available
            pdf_filename = f"pdf_{run.pdf_file_id}.pdf"  # Default fallback
            try:
                if hasattr(run, 'pdf_file') and run.pdf_file:
                    pdf_filename = run.pdf_file.filename
            except:
                pass  # Use fallback if relationship access fails
            
            summary = EtoRunSummaryResponse(
                id=run.id,
                email_id=run.email_id,
                pdf_filename=pdf_filename,
                status=run.status,
                template_name=None,  # TODO: Get from template relationship
                processing_duration_ms=run.processing_duration_ms,
                created_at=run.created_at,
                completed_at=run.completed_at,
                error_message=run.error_message
            )
            run_summaries.append(summary.dict())
        
        # Build pagination info
        total_pages = (total_count + request_params.limit - 1) // request_params.limit
        pagination = {
            "page": request_params.page,
            "limit": request_params.limit,
            "total_items": total_count,
            "total_pages": total_pages,
            "has_next": request_params.page < total_pages,
            "has_prev": request_params.page > 1
        }
        
        return jsonify({
            "success": True,
            "data": run_summaries,
            "pagination": pagination
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting ETO runs: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to get ETO runs"
        }), 500


@eto_processing_bp.route('/<int:run_id>', methods=['GET'])
@cross_origin()
def get_eto_run_details(run_id: int):
    """Get detailed information for a specific ETO run"""
    try:
        if not eto_run_repo:
            return jsonify({
                "success": False,
                "error": "Service unavailable",
                "message": "Database connection not available"
            }), 503
        
        run = eto_run_repo.get_by_id(run_id)
        
        if not run:
            return jsonify({
                "success": False,
                "error": "ETO run not found",
                "message": f"ETO run with ID {run_id} does not exist"
            }), 404
        
        # Convert to detailed response
        run_detail = EtoRunDetailResponse(
            id=run.id,
            email_id=run.email_id,
            pdf_file_id=run.pdf_file_id,
            status=run.status,
            processing_step=run.processing_step,
            error_type=run.error_type,
            error_message=run.error_message,
            error_details=run.error_details,
            matched_template_id=run.matched_template_id,
            template_name=None,  # TODO: Get from relationship
            template_version=run.template_version,
            template_match_coverage=run.template_match_coverage,
            unmatched_object_count=run.unmatched_object_count,
            suggested_new_template=run.suggested_new_template,
            extracted_data=run.extracted_data,
            transformation_audit=run.transformation_audit,
            target_data=run.target_data,
            failed_step_id=run.failed_step_id,
            step_execution_log=run.step_execution_log,
            started_at=run.started_at,
            completed_at=run.completed_at,
            processing_duration_ms=run.processing_duration_ms,
            order_id=run.order_id,
            created_at=run.created_at,
            updated_at=run.updated_at
        )
        
        return jsonify({
            "success": True,
            "data": run_detail.dict()
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting ETO run {run_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to get ETO run details"
        }), 500


@eto_processing_bp.route('/<int:run_id>/reprocess', methods=['POST'])
@cross_origin()
def reprocess_eto_run(run_id: int):
    """Reprocess an ETO run (reset to not_started status)"""
    try:
        if not eto_run_repo:
            return jsonify({
                "success": False,
                "error": "Service unavailable",
                "message": "Database connection not available"
            }), 503
        
        data = request.get_json() or {}
        
        # Validate request data
        try:
            reprocess_request = ReprocessEtoRunRequest(**data)
        except ValidationError as e:
            return jsonify(handle_validation_error(e)), 400
        
        # Get the run
        run = eto_run_repo.get_by_id(run_id)
        if not run:
            return jsonify({
                "success": False,
                "error": "ETO run not found",
                "message": f"ETO run with ID {run_id} does not exist"
            }), 404
        
        # Check if reprocessing is allowed
        if run.status == 'success' and not reprocess_request.force:
            return jsonify({
                "success": False,
                "error": "Cannot reprocess successful run",
                "message": "Use force=true to reprocess successful runs"
            }), 400
        
        # Reset run status and clear results
        update_data = {
            "status": "not_started",
            "processing_step": None,
            "error_type": None,
            "error_message": None,
            "error_details": None,
            "extracted_data": None,
            "transformation_audit": None,
            "target_data": None,
            "failed_step_id": None,
            "step_execution_log": None,
            "started_at": None,
            "completed_at": None,
            "processing_duration_ms": None
        }
        
        if reprocess_request.template_id:
            update_data["matched_template_id"] = reprocess_request.template_id
        
        updated_run = eto_run_repo.update(run_id, update_data)
        
        return jsonify({
            "success": True,
            "message": f"ETO run {run_id} queued for reprocessing",
            "run_id": run_id,
            "status": "not_started"
        }), 200
    
    except Exception as e:
        logger.error(f"Error reprocessing ETO run {run_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to reprocess ETO run"
        }), 500


@eto_processing_bp.route('/<int:run_id>/skip', methods=['POST'])
@cross_origin()
def skip_eto_run(run_id: int):
    """Skip an ETO run (mark as skipped status)"""
    try:
        if not eto_run_repo:
            return jsonify({
                "success": False,
                "error": "Service unavailable",
                "message": "Database connection not available"
            }), 503
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body required",
                "message": "Skip reason is required"
            }), 400
        
        # Validate request data
        try:
            skip_request = SkipEtoRunRequest(**data)
        except ValidationError as e:
            return jsonify(handle_validation_error(e)), 400
        
        # Get the run
        run = eto_run_repo.get_by_id(run_id)
        if not run:
            return jsonify({
                "success": False,
                "error": "ETO run not found",
                "message": f"ETO run with ID {run_id} does not exist"
            }), 404
        
        # Update run to skipped status
        update_data = {
            "status": "skipped",
            "error_message": f"Manually skipped: {skip_request.reason}",
            "completed_at": None  # Keep as None for skipped runs
        }
        
        updated_run = eto_run_repo.update(run_id, update_data)
        
        return jsonify({
            "success": True,
            "message": f"ETO run {run_id} marked as skipped",
            "run_id": run_id,
            "status": "skipped",
            "reason": skip_request.reason
        }), 200
    
    except Exception as e:
        logger.error(f"Error skipping ETO run {run_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to skip ETO run"
        }), 500


@eto_processing_bp.route('/<int:run_id>', methods=['DELETE'])
@cross_origin()
def delete_eto_run(run_id: int):
    """Permanently delete an ETO run and associated data"""
    try:
        if not eto_run_repo:
            return jsonify({
                "success": False,
                "error": "Service unavailable",
                "message": "Database connection not available"
            }), 503
        
        # Check if run exists
        run = eto_run_repo.get_by_id(run_id)
        if not run:
            return jsonify({
                "success": False,
                "error": "ETO run not found",
                "message": f"ETO run with ID {run_id} does not exist"
            }), 404
        
        # Delete the run
        success = eto_run_repo.delete(run_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"ETO run {run_id} deleted successfully",
                "run_id": run_id
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Failed to delete ETO run",
                "message": "Delete operation failed"
            }), 500
    
    except Exception as e:
        logger.error(f"Error deleting ETO run {run_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to delete ETO run"
        }), 500


@eto_processing_bp.route('/statistics', methods=['GET'])
@cross_origin()
def get_eto_run_statistics():
    """Get ETO processing statistics"""
    try:
        if not eto_run_repo:
            return jsonify({
                "success": False,
                "error": "Service unavailable",
                "message": "Database connection not available"
            }), 503
        
        # Get basic counts from repository
        # Note: This is a simplified implementation. In a real system,
        # you'd want to implement efficient stat queries in the repository
        all_runs = eto_run_repo.get_all()
        
        total_runs = len(all_runs)
        successful_runs = len([r for r in all_runs if r.status == 'success'])
        failed_runs = len([r for r in all_runs if r.status == 'failure'])
        skipped_runs = len([r for r in all_runs if r.status == 'skipped'])
        processing_runs = len([r for r in all_runs if r.status == 'processing'])
        needs_template_runs = len([r for r in all_runs if r.status == 'needs_template'])
        
        success_rate = successful_runs / total_runs if total_runs > 0 else 0.0
        
        # Calculate average processing time for successful runs
        successful_with_duration = [r for r in all_runs if r.status == 'success' and r.processing_duration_ms]
        avg_processing_time = sum(r.processing_duration_ms for r in successful_with_duration) // len(successful_with_duration) if successful_with_duration else 0
        
        # TODO: Implement last_24h_runs calculation with proper date filtering
        last_24h_runs = 0  # Placeholder
        
        # Get most recent successful and failed runs
        successful_runs_list = [r for r in all_runs if r.status == 'success']
        failed_runs_list = [r for r in all_runs if r.status == 'failure']
        
        last_successful_run = max(successful_runs_list, key=lambda x: x.completed_at).completed_at if successful_runs_list else None
        last_failed_run = max(failed_runs_list, key=lambda x: x.created_at).created_at if failed_runs_list else None
        
        stats = EtoRunStatsResponse(
            total_runs=total_runs,
            successful_runs=successful_runs,
            failed_runs=failed_runs,
            skipped_runs=skipped_runs,
            processing_runs=processing_runs,
            needs_template_runs=needs_template_runs,
            success_rate=success_rate,
            avg_processing_time_ms=avg_processing_time,
            last_24h_runs=last_24h_runs,
            last_successful_run=last_successful_run,
            last_failed_run=last_failed_run
        )
        
        return jsonify({
            "success": True,
            "data": stats.dict()
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting ETO run statistics: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to get ETO run statistics"
        }), 500


# Export the blueprint
__all__ = ['eto_processing_bp']