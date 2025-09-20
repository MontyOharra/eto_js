"""
ETO Processing API Blueprint
REST endpoints for ETO processing runs and results
"""
from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin
from pydantic import ValidationError
from datetime import datetime
import logging
from typing import Dict, Any, Optional

from ..schemas.eto_processing import (
    EtoRunListRequest,
    EtoRunListResponse,
    EtoRunSummary,
    EtoRunDetailResponse,
    EtoRunDetail,
    ReprocessEtoRunRequest,
    ReprocessEtoRunResponse,
    SkipEtoRunRequest,
    SkipEtoRunResponse,
    DeleteEtoRunResponse,
    EtoStatisticsResponse,
    ProcessingStatistics
)
from ..schemas.common import APIResponse
from shared.domain import EtoRun
from shared.services import get_eto_processing_service, get_pdf_processing_service, get_email_ingestion_service

logger = logging.getLogger(__name__)

# Create blueprint
eto_processing_bp = Blueprint('eto_processing', __name__, url_prefix='/api/eto-runs')


def get_eto_service():
    """Get ETO processing service from service container"""
    return get_eto_processing_service()


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


def convert_to_summary(eto_run: EtoRun) -> EtoRunSummary:
    """Convert EtoRun domain object to EtoRunSummary with real data"""

    # Default values in case services are unavailable
    pdf_filename = "unknown.pdf"
    email_subject = "Unknown Subject"
    sender_email = "unknown@example.com"
    file_size = 0
    template_name = None

    try:
        # Get PDF information
        pdf_service = get_pdf_processing_service()
        pdf_metadata = pdf_service.get_pdf_metadata(eto_run.pdf_file_id)
        if pdf_metadata:
            pdf_filename = pdf_metadata.get('filename', pdf_filename)
            file_size = pdf_metadata.get('file_size', file_size)
    except Exception as e:
        logger.warning(f"Could not fetch PDF metadata for PDF {eto_run.pdf_file_id}: {e}")

    try:
        # Get email information
        email_service = get_email_ingestion_service()
        email_data = email_service.get_email_by_id(eto_run.email_id)
        if email_data:
            email_subject = email_data.subject or email_subject
            sender_email = email_data.sender_email or sender_email
    except Exception as e:
        logger.warning(f"Could not fetch email data for email {eto_run.email_id}: {e}")

    # TODO: Get template name when template service is available
    # if eto_run.matched_template_id:
    #     try:
    #         template_service = get_pdf_template_service()
    #         template = template_service.get_template_by_id(eto_run.matched_template_id)
    #         if template:
    #             template_name = template.name
    #     except Exception as e:
    #         logger.warning(f"Could not fetch template name for template {eto_run.matched_template_id}: {e}")

    return EtoRunSummary(
        id=eto_run.id,
        email_id=eto_run.email_id,
        pdf_file_id=eto_run.pdf_file_id,
        status=eto_run.status,
        processing_step=eto_run.processing_step,
        pdf_filename=pdf_filename,
        email_subject=email_subject,
        sender_email=sender_email,
        file_size=file_size,
        matched_template_id=eto_run.matched_template_id,
        template_name=template_name,
        processing_duration_ms=eto_run.processing_duration_ms,
        error_message=eto_run.error_message,
        created_at=eto_run.created_at,
        started_at=eto_run.started_at,
        completed_at=eto_run.completed_at
    )


@eto_processing_bp.route('', methods=['GET'])
@cross_origin()
def get_eto_runs():
    """Get ETO processing runs with filtering and pagination"""
    try:
        # Parse query parameters using Pydantic
        # Helper function to safely convert to int
        def safe_int(value: str | None) -> int | None:
            if value is None or value.strip() == "":
                return None
            try:
                return int(value)
            except ValueError:
                return None

        # Helper function to safely convert to datetime
        def safe_datetime(value: str | None) -> datetime | None:
            if value is None or value.strip() == "":
                return None
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None

        request_data = {
            "status": request.args.get("status"),
            "email_id": safe_int(request.args.get("email_id")),
            "template_id": safe_int(request.args.get("template_id")),
            "has_errors": request.args.get("has_errors", "").lower() in ("true", "1") if request.args.get("has_errors") else None,
            "date_from": safe_datetime(request.args.get("date_from")),
            "date_to": safe_datetime(request.args.get("date_to")),
            "page": int(request.args.get("page") or "1"),
            "limit": int(request.args.get("limit") or "20"),
            "order_by": request.args.get("order_by") or "created_at",
            "desc": request.args.get("desc", "true").lower() in ("true", "1")
        }

        # Validate request
        request_obj = EtoRunListRequest(**request_data)

        # Get service and fetch data
        service = get_eto_service()
        result = service.get_runs_with_filters(
            status=request_obj.status,
            email_id=request_obj.email_id,
            template_id=request_obj.template_id,
            has_errors=request_obj.has_errors,
            date_from=request_obj.date_from,
            date_to=request_obj.date_to,
            page=request_obj.page,
            limit=request_obj.limit,
            order_by=request_obj.order_by,
            desc=request_obj.desc
        )

        # Convert to response schema
        run_summaries = [convert_to_summary(run) for run in result["runs"]]

        response = EtoRunListResponse(
            success=True,
            data=run_summaries,
            total=result["total"],
            page=result["page"],
            limit=result["limit"],
            total_pages=result["total_pages"]
        )

        return jsonify(response.dict()), 200

    except ValidationError as e:
        logger.warning(f"Validation error in get_eto_runs: {e}")
        return jsonify(handle_validation_error(e)), 400

    except ValueError as e:
        logger.warning(f"Value error in get_eto_runs: {e}")
        return jsonify({
            "success": False,
            "error": "Invalid parameter",
            "message": str(e)
        }), 400

    except Exception as e:
        logger.error(f"Error in get_eto_runs: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }), 500


def convert_to_detail(eto_run: EtoRun) -> EtoRunDetail:
    """Convert EtoRun domain object to EtoRunDetail"""
    import json

    # Parse JSON fields safely
    error_details = None
    if eto_run.error_details:
        try:
            error_details = json.loads(eto_run.error_details)
        except (json.JSONDecodeError, TypeError):
            error_details = {"raw": eto_run.error_details}

    step_execution_log = None
    if eto_run.step_execution_log:
        try:
            step_execution_log = json.loads(eto_run.step_execution_log)
        except (json.JSONDecodeError, TypeError):
            step_execution_log = {"raw": eto_run.step_execution_log}

    return EtoRunDetail(
        id=eto_run.id,
        email_id=eto_run.email_id,
        pdf_file_id=eto_run.pdf_file_id,
        status=eto_run.status,
        processing_step=eto_run.processing_step,
        error_type=eto_run.error_type,
        error_message=eto_run.error_message,
        error_details=error_details,
        matched_template_id=eto_run.matched_template_id,
        template_name=None,  # TODO: Get template name if template_id exists
        template_version=eto_run.template_version,
        template_match_coverage=eto_run.template_match_coverage,
        has_extracted_data=bool(eto_run.extracted_data),
        has_transformation_audit=bool(eto_run.transformation_audit),
        has_target_data=bool(eto_run.target_data),
        failed_step_id=eto_run.failed_step_id,
        step_execution_log=step_execution_log,
        created_at=eto_run.created_at,
        updated_at=eto_run.updated_at,
        started_at=eto_run.started_at,
        completed_at=eto_run.completed_at,
        processing_duration_ms=eto_run.processing_duration_ms,
        order_id=eto_run.order_id
    )


@eto_processing_bp.route('/<int:run_id>', methods=['GET'])
@cross_origin()
def get_eto_run_details(run_id: int):
    """Get detailed information for a specific ETO run"""
    try:
        # Validate run_id
        if run_id <= 0:
            return jsonify({
                "success": False,
                "error": "Invalid run ID",
                "message": "Run ID must be a positive integer"
            }), 400

        # Get service and fetch run
        service = get_eto_service()
        eto_run = service.get_run_by_id(run_id)

        if not eto_run:
            return jsonify({
                "success": False,
                "error": "Not found",
                "message": f"ETO run {run_id} not found"
            }), 404

        # Convert to response schema
        run_detail = convert_to_detail(eto_run)

        response = EtoRunDetailResponse(
            success=True,
            data=run_detail
        )

        return jsonify(response.dict()), 200

    except Exception as e:
        logger.error(f"Error in get_eto_run_details for run {run_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }), 500


@eto_processing_bp.route('/<int:run_id>/reprocess', methods=['POST'])
@cross_origin()
def reprocess_eto_run(run_id: int):
    """Reprocess an ETO run (reset to not_started status)"""
    try:
        # Validate run_id
        if run_id <= 0:
            return jsonify({
                "success": False,
                "error": "Invalid run ID",
                "message": "Run ID must be a positive integer"
            }), 400

        # Parse request body
        request_data = request.get_json() or {}

        try:
            reprocess_request = ReprocessEtoRunRequest(**request_data)
        except ValidationError as e:
            logger.warning(f"Validation error in reprocess_eto_run: {e}")
            return jsonify(handle_validation_error(e)), 400

        # Get service and reprocess run
        service = get_eto_service()

        # Get current run for old_status
        eto_run = service.get_run_by_id(run_id)
        if not eto_run:
            return jsonify({
                "success": False,
                "error": "Not found",
                "message": f"ETO run {run_id} not found"
            }), 404

        old_status = eto_run.status

        # Reprocess the run using service
        updated_run = service.reprocess_run(
            run_id=run_id,
            force=reprocess_request.force,
            template_id=reprocess_request.template_id,
            reset_template=reprocess_request.reset_template,
            reason=reprocess_request.reason
        )

        response = ReprocessEtoRunResponse(
            success=True,
            run_id=run_id,
            old_status=old_status,
            new_status=updated_run.status,
            message=f"ETO run {run_id} reset for reprocessing"
        )

        return jsonify(response.dict()), 200

    except ValueError as e:
        logger.warning(f"Validation error in reprocess_eto_run for run {run_id}: {e}")
        return jsonify({
            "success": False,
            "error": "Cannot reprocess",
            "message": str(e)
        }), 400

    except Exception as e:
        logger.error(f"Error in reprocess_eto_run for run {run_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }), 500


@eto_processing_bp.route('/<int:run_id>/skip', methods=['POST'])
@cross_origin()
def skip_eto_run(run_id: int):
    """Skip an ETO run (mark as skipped status)"""
    try:
        # Validate run_id
        if run_id <= 0:
            return jsonify({
                "success": False,
                "error": "Invalid run ID",
                "message": "Run ID must be a positive integer"
            }), 400

        # Parse request body
        request_data = request.get_json() or {}

        try:
            skip_request = SkipEtoRunRequest(**request_data)
        except ValidationError as e:
            logger.warning(f"Validation error in skip_eto_run: {e}")
            return jsonify(handle_validation_error(e)), 400

        # Get service and skip run
        service = get_eto_service()
        updated_run = service.skip_run(
            run_id=run_id,
            reason=skip_request.reason,
            permanent=skip_request.permanent
        )

        response = SkipEtoRunResponse(
            success=True,
            run_id=run_id,
            status=updated_run.status,
            reason=skip_request.reason,
            message=f"ETO run {run_id} has been skipped"
        )

        return jsonify(response.dict()), 200

    except ValueError as e:
        logger.warning(f"Validation error in skip_eto_run for run {run_id}: {e}")
        return jsonify({
            "success": False,
            "error": "Cannot skip",
            "message": str(e)
        }), 400

    except Exception as e:
        logger.error(f"Error in skip_eto_run for run {run_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }), 500


@eto_processing_bp.route('/<int:run_id>', methods=['DELETE'])
@cross_origin()
def delete_eto_run(run_id: int):
    """Permanently delete an ETO run and associated data"""
    try:
        # Validate run_id
        if run_id <= 0:
            return jsonify({
                "success": False,
                "error": "Invalid run ID",
                "message": "Run ID must be a positive integer"
            }), 400

        # Get service and delete run
        service = get_eto_service()
        success = service.delete_run(run_id)

        response = DeleteEtoRunResponse(
            success=True,
            run_id=run_id,
            message=f"ETO run {run_id} has been permanently deleted"
        )

        return jsonify(response.dict()), 200

    except ValueError as e:
        logger.warning(f"Validation error in delete_eto_run for run {run_id}: {e}")
        return jsonify({
            "success": False,
            "error": "Cannot delete",
            "message": str(e)
        }), 400

    except Exception as e:
        logger.error(f"Error in delete_eto_run for run {run_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }), 500


@eto_processing_bp.route('/statistics', methods=['GET'])
@cross_origin()
def get_eto_run_statistics():
    """Get ETO processing statistics"""
    try:
        # Get service and fetch statistics
        service = get_eto_service()
        stats_data = service.get_processing_statistics()

        # Convert to response schema
        # Map status counts to schema format
        status_counts = []
        for status_info in stats_data["status_counts"]:
            status_counts.append({
                "status": status_info["status"],
                "count": status_info["count"]
            })

        processing_stats = ProcessingStatistics(
            total_runs=stats_data["total_runs"],
            successful_runs=sum(sc["count"] for sc in status_counts if sc["status"] == "success"),
            failed_runs=sum(sc["count"] for sc in status_counts if sc["status"] == "failure"),
            skipped_runs=sum(sc["count"] for sc in status_counts if sc["status"] == "skipped"),
            processing_runs=sum(sc["count"] for sc in status_counts if sc["status"] == "processing"),
            needs_template_runs=sum(sc["count"] for sc in status_counts if sc["status"] == "needs_template"),
            success_rate=stats_data["success_rate"],
            avg_processing_time_ms=stats_data["average_processing_time_ms"],
            median_processing_time_ms=None,  # TODO: Calculate median if needed
            last_24h_runs=stats_data["last_24h_runs"],
            last_7d_runs=0,  # TODO: Add 7d and 30d calculations to repository
            last_30d_runs=0,
            most_common_errors=[],  # TODO: Add error analysis to repository
            template_coverage=0.0,  # TODO: Calculate template coverage
            last_successful_run=stats_data["last_successful_run"],
            last_failed_run=stats_data["last_failed_run"],
            last_processed_run=None  # TODO: Add to repository query
        )

        response = EtoStatisticsResponse(
            success=True,
            data=processing_stats
        )

        return jsonify(response.dict()), 200

    except Exception as e:
        logger.error(f"Error in get_eto_run_statistics: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }), 500


# === Processing Results & Data Endpoints ===

@eto_processing_bp.route('/<int:run_id>/results', methods=['GET'])
@cross_origin()
def get_eto_run_results(run_id: int):
    """Get extracted and transformed data for an ETO run"""
    # TODO: Implement extraction and transformation results retrieval
    pass


@eto_processing_bp.route('/<int:run_id>/pdf-data', methods=['GET'])
@cross_origin()
def get_eto_run_pdf_data(run_id: int):
    """Get PDF file and objects for this ETO run for template building"""
    try:
        service = get_eto_service()

        # Get the ETO run
        eto_run = service.eto_run_repo.get_by_id(run_id)
        if not eto_run:
            return jsonify({
                "success": False,
                "error": "ETO run not found",
                "message": f"ETO run {run_id} does not exist"
            }), 404

        # Get PDF file information
        pdf_service = get_pdf_processing_service()
        pdf_metadata = pdf_service.get_pdf_metadata(eto_run.pdf_file_id)
        if not pdf_metadata:
            return jsonify({
                "success": False,
                "error": "PDF file not found",
                "message": f"PDF file {eto_run.pdf_file_id} does not exist"
            }), 404

        # Get PDF content (bytes) for template building
        pdf_content = pdf_service.get_pdf_content(eto_run.pdf_file_id)
        if not pdf_content:
            return jsonify({
                "success": False,
                "error": "PDF content not found",
                "message": f"PDF content for file {eto_run.pdf_file_id} is not accessible"
            }), 404

        # Get PDF objects for template building
        pdf_objects = pdf_service.get_pdf_objects(eto_run.pdf_file_id)
        if pdf_objects is None:
            pdf_objects = []

        # Get email information
        email_service = get_email_ingestion_service()
        email_data = email_service.get_email_by_id(eto_run.email_id)

        # Encode PDF bytes as base64 for JSON transmission
        import base64
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

        # Build response matching frontend expectations for template building
        response_data = {
            "eto_run_id": eto_run.id,
            "pdf_id": eto_run.pdf_file_id,
            "filename": pdf_metadata.get('filename', 'unknown.pdf'),
            "page_count": pdf_metadata.get('page_count', 0),
            "object_count": pdf_metadata.get('object_count', 0),
            "file_size": pdf_metadata.get('file_size', 0),
            "pdf_objects": pdf_objects,
            "pdf_content_base64": pdf_base64,
            "status": eto_run.status,
            "processing_step": eto_run.processing_step,
            "matched_template_id": eto_run.matched_template_id,
            "extracted_data": eto_run.extracted_data,
            "transformation_audit": eto_run.transformation_audit,
            "target_data": eto_run.target_data,
            "email": {
                "subject": email_data.subject if email_data else "Unknown Subject",
                "sender_email": email_data.sender_email if email_data else "unknown@example.com",
                "received_date": email_data.received_date.isoformat() if email_data and email_data.received_date else None
            },
            "timestamps": {
                "created_at": eto_run.created_at.isoformat() if eto_run.created_at else None,
                "started_at": eto_run.started_at.isoformat() if eto_run.started_at else None,
                "completed_at": eto_run.completed_at.isoformat() if eto_run.completed_at else None
            },
            "error_info": {
                "error_type": eto_run.error_type,
                "error_message": eto_run.error_message
            }
        }

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error getting PDF data for ETO run {run_id}: {e}")
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": "Failed to retrieve PDF data"
        }), 500


@eto_processing_bp.route('/<int:run_id>/audit', methods=['GET'])
@cross_origin()
def get_eto_run_audit(run_id: int):
    """Get processing audit trail and error details for an ETO run"""
    # TODO: Implement audit trail and error details retrieval
    pass


# === Template Integration Endpoints ===

@eto_processing_bp.route('/<int:run_id>/template-suggestions', methods=['GET'])
@cross_origin()
def get_template_suggestions(run_id: int):
    """Get suggested templates for failed ETO runs"""
    # TODO: Implement template suggestion logic
    pass


@eto_processing_bp.route('/<int:run_id>/assign-template', methods=['POST'])
@cross_origin()
def assign_template_to_run(run_id: int):
    """Manually assign template to ETO run and reprocess"""
    # TODO: Implement template assignment and reprocessing
    pass


# === Batch Operations Endpoints ===

@eto_processing_bp.route('/reprocess-all', methods=['POST'])
@cross_origin()
def reprocess_all_failed_runs():
    """
    Reprocess all ETO runs with status 'failure' or 'needs_template'

    Resets them to 'not_started' status and clears processing fields,
    allowing the continuous processing loop to pick them up again.

    Returns:
        JSON response with reprocessing results and statistics
    """
    try:
        # Get ETO processing service
        eto_service = get_eto_processing_service()
        if not eto_service:
            return jsonify({
                "success": False,
                "error": "ETO processing service not available",
                "message": "ETO processing service is not available"
            }), 500

        # Execute bulk reprocessing
        result = eto_service.reprocess_all_failed_runs()

        if result['success']:
            # Return success response with statistics
            return jsonify({
                "success": True,
                "result": {
                    "reprocessed": result['reprocessed'],
                    "needs_template_count": result['breakdown']['needs_template_count'],
                    "failure_count": result['breakdown']['failure_count'],
                    "message": result['message']
                }
            }), 200
        else:
            # Return error response
            return jsonify({
                "success": False,
                "result": {
                    "reprocessed": 0,
                    "needs_template_count": 0,
                    "failure_count": 0,
                    "error": result.get('error', 'Unknown error'),
                    "message": result['message']
                }
            }), 500

    except Exception as e:
        logger.error(f"Error in reprocess_all_failed_runs endpoint: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "result": {
                "reprocessed": 0,
                "needs_template_count": 0,
                "failure_count": 0,
                "error": str(e),
                "message": "An unexpected error occurred while reprocessing runs"
            }
        }), 500


@eto_processing_bp.route('/summary', methods=['GET'])
@cross_origin()
def get_eto_runs_summary():
    """Get status summary with counts by status"""
    # TODO: Implement status summary with counts
    pass


# Export the blueprint
__all__ = ['eto_processing_bp']