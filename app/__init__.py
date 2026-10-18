"""Flask application factory for the GRE Preparation Guide & Planner."""

import os
from pathlib import Path

from flask import Flask
from dotenv import load_dotenv


def create_app():
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    app = Flask(__name__)
    app.config["MONGODB_URI"] = os.getenv("MONGODB_URI", "").strip()
    app.config["MONGODB_DATABASE"] = os.getenv("MONGODB_DATABASE", "gre_planner").strip()

    from app.routes import main

    app.register_blueprint(main)
    return app
