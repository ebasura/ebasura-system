from flask import Blueprint, jsonify
from app.ebasura import system_monitor

system_info_bp = Blueprint('system_info', __name__)

@system_info_bp.route('/system-info', methods=['GET'])
def system_info():
    monitor = system_monitor.SystemMonitor()
    info = {
        "os": monitor.get_os_info(),
        "kernel_version": monitor.get_kernel_version(),
        "uptime": monitor.get_system_uptime(),
        "cpu_usage": monitor.get_cpu_usage(),
        "memory_usage": monitor.get_memory_usage(),
        "disk_usage": monitor.get_disk_usage(),
        "temperature": monitor.get_rpi_temperature_from_file()
    }
    return jsonify(info)
