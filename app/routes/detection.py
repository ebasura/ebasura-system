from flask import Blueprint, jsonify
from app.ebasura import live_monitoring

detection_bp = Blueprint('detection', __name__)

@detection_bp.route('/detection', methods=['GET'])
def detection():
    return jsonify(live_monitoring.get_frame_data())
