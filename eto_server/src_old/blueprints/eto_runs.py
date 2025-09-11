"""
ETO Runs Blueprint - ETO processing run management and results
"""
from flask import Blueprint, jsonify, request

eto_runs_bp = Blueprint('eto_runs', __name__, url_prefix='/api/eto-runs')

@eto_runs_bp.route('', methods=['GET'])
def get_eto_runs():
    """Get ETO processing runs with filtering"""
    pass

@eto_runs_bp.route('/<int:run_id>/processing-details', methods=['GET'])
def get_eto_run_processing_details(run_id):
    """Get detailed processing information for an ETO run"""
    pass

@eto_runs_bp.route('/<int:run_id>/skip', methods=['POST'])
def skip_eto_run(run_id):
    """Skip an ETO run (mark as skipped status)"""
    pass

@eto_runs_bp.route('/<int:run_id>', methods=['DELETE'])
def delete_eto_run(run_id):
    """Permanently delete an ETO run and associated data"""
    pass

@eto_runs_bp.route('/<int:run_id>/reprocess', methods=['POST'])
def reprocess_eto_run(run_id):
    """Reprocess a skipped ETO run (reset to not_started status)"""
    pass

@eto_runs_bp.route('/<int:run_id>/pdf-data', methods=['GET'])
def get_eto_run_pdf_data(run_id):
    """Get complete PDF data (file + objects) for an ETO run"""
    pass

@eto_runs_bp.route('/<int:run_id>/extraction-results', methods=['GET'])
def get_extraction_results(run_id):
    """Get extraction results for a successful ETO run"""
    pass