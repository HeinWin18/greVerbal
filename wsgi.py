"""Local entry point and production WSGI application."""

from app import create_app

app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
