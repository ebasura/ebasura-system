from flask import Blueprint, jsonify

system_health_bp = Blueprint('system_health', __name__)

@system_health_bp.route('/system-health', methods=['GET'])
def system_health():
    return jsonify({
        "servo_online": True,
        "sensors": {
            "recyclable_bin": False,
            "non_recyclable_bin": True,
            "proximity": True,
            "weight": False
        },
    })
