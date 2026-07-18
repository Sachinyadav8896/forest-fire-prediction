"""
app.py
Flask application factory + entry point.

Run:
    python backend/app.py
or, in production:
    gunicorn -w 4 -b 0.0.0.0:5000 "backend.app:create_app()"
"""

from __future__ import annotations

import os
import sys

from flask import Flask, jsonify
from flask_cors import CORS

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import API
from backend.utils.logger import get_logger
from backend.api.routes import api as api_blueprint

logger = get_logger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    app.register_blueprint(api_blueprint)

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def server_error(e):
        logger.exception("Unhandled server error")
        return jsonify({"error": "Internal server error"}), 500

    @app.route("/")
    def index():
        return jsonify({
            "service": "Forest Fire Prediction System API",
            "status": "running",
            "endpoints": [
                "POST /api/predict", "POST /api/predict/live",
                "GET /api/predictions/recent", "GET /api/predictions/map",
                "GET /api/models/compare", "GET /api/alerts/recent", "GET /api/health",
            ],
        })

    logger.info("Flask app created and routes registered.")
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host=API.host, port=API.port, debug=API.debug)
