"""
Templates Blueprint - PDF template management and template matching
"""
from flask import Blueprint, jsonify, request

templates_bp = Blueprint('templates', __name__, url_prefix='/api/templates')

@templates_bp.route('', methods=['GET'])
@templates_bp.route('/', methods=['GET'])
def get_templates():
    """Get PDF templates with filtering and pagination"""
    pass

@templates_bp.route('', methods=['POST'])
@templates_bp.route('/', methods=['POST'])
def create_template():
    """Create a new PDF template"""
    pass

@templates_bp.route('/reprocess', methods=['POST'])
def reprocess_unrecognized():
    """Manually trigger reprocessing of unrecognized runs"""
    pass

@templates_bp.route('/<int:template_id>/view', methods=['GET'])
def get_template_view_data(template_id):
    """Get detailed template data for viewing, including PDF and object information"""
    pass