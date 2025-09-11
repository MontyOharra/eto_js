"""
Processing Blueprint - Background processing management and worker control
"""
from flask import Blueprint, jsonify, request

processing_bp = Blueprint('processing', __name__, url_prefix='/api/processing')

@processing_bp.route('/start', methods=['POST'])
def start_processing():
    """Start background processing worker"""
    pass

@processing_bp.route('/stop', methods=['POST'])
def stop_processing():
    """Stop background processing worker"""
    pass

@processing_bp.route('/status', methods=['GET'])
def get_processing_status():
    """Get processing worker status and statistics"""
    pass

@processing_bp.route('/trigger', methods=['POST'])
def trigger_processing():
    """Manually trigger processing of pending runs"""
    pass