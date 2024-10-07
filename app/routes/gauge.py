from flask import Blueprint, jsonify
from ..engine import fetch_waste_bin_levels

gauge_bp = Blueprint('gauge', __name__)

@gauge_bp.route('/gauge', methods=['GET'])
def gauge():

    data = fetch_waste_bin_levels()

    gauge_values = {
        "recyclable_bin": int(next((item['current_fill_level'] for item in data if item['bin_name'] == 'Recyclable'), 0)) ,
        "non_recyclable_bin":int(next((item['current_fill_level'] for item in data if item['bin_name'] == 'Non-Recyclable'), 0)),
    }
    
    
    return jsonify(gauge_values)

@gauge_bp.route('/weights', methods=['GET'])
def weight():
    
    #TODO: fetch database 
    
    weight_values  = {
        "recyclable_bin": 0,
        "non_recyclable_bin": 0
    }
    
    return jsonify(weight_values)