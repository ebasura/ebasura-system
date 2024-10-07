import uuid
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import pandas as pd
from ..routes.system_info import system_info_bp
from ..routes.system_health import system_health_bp
from ..routes.detection import detection_bp
from ..routes.gauge import gauge_bp
from ..engine import db
from .charts import create_dash
def create_app():
    app = Flask(__name__)
    create_dash(app)
    UPLOAD_FOLDER = 'models'    
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    CORS(app, resources={r"/*": {"origins": {"https://ebasura.online", "https://www.ebasura.online", "http://192.168.0.125:8000"}}})

    # Register blueprints
    app.register_blueprint(system_info_bp)
    app.register_blueprint(system_health_bp)
    app.register_blueprint(detection_bp)
    app.register_blueprint(gauge_bp)

    def generate_random_filename(filename):
        """Generate a random filename with the same file extension."""
        ext = os.path.splitext(filename)[1]  
        return str(uuid.uuid4()) + ext 

    @app.route('/upload-model', methods=['GET', 'POST'])
    def upload():
        if 'model_file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
        
        file = request.files['model_file']
        description = request.form.get('model_description')
        
        # Validate the file and description
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        if not description:
            return jsonify({"error": "No model description provided"}), 400

        # Save the file
        random_filename = generate_random_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], random_filename)
        file.save(file_path)

        try:
            query = "INSERT INTO models (description, file_path) VALUES (%s, %s)"
            db.execute(query, (description, file_path))
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        return jsonify({"message": "File uploaded successfully", "description": description}), 200
    
    @app.route('/')
    def ok():
        return jsonify({"status": 200})

    return app
