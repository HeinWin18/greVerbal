"""MongoDB connection helpers shared by Flask routes and scripts."""

from flask import current_app
import certifi
from pymongo import MongoClient
from pymongo.errors import ConfigurationError, PyMongoError, ServerSelectionTimeoutError


class DatabaseError(RuntimeError):
    """Base exception for MongoDB configuration and connection failures."""


class DatabaseConfigurationError(DatabaseError):
    """Raised when the required MongoDB settings are missing or invalid."""


class DatabaseConnectionError(DatabaseError):
    """Raised when MongoDB cannot be reached or a database operation fails."""


_client = None
_client_uri = None


def get_client():
    """Return a reusable MongoClient configured for the current Flask app."""
    global _client, _client_uri

    uri = current_app.config.get("MONGODB_URI", "").strip()
    if not uri:
        raise DatabaseConfigurationError(
            "MONGODB_URI is missing. Add your Atlas connection string to .env."
        )

    if _client is None or _client_uri != uri:
        if _client is not None:
            _client.close()
        try:
            _client = MongoClient(
                uri,
                tlsCAFile=certifi.where(),
                serverSelectionTimeoutMS=10000,
            )
        except (ConfigurationError, ValueError) as exc:
            raise DatabaseConfigurationError(
                "Could not initialize MongoDB client. Check the URI format, Atlas cluster host, and DNS/network access."
            ) from exc
        _client_uri = uri
    return _client


def get_database():
    """Return the configured MongoDB database."""
    name = current_app.config.get("MONGODB_DATABASE", "").strip()
    if not name:
        raise DatabaseConfigurationError("MONGODB_DATABASE is missing from .env.")
    try:
        return get_client()[name]
    except DatabaseError:
        raise
    except (ConfigurationError, ValueError) as exc:
        raise DatabaseConfigurationError("MongoDB database configuration is invalid.") from exc


def test_connection():
    """Ping MongoDB and return True, with a clear error on failure."""
    try:
        get_client().admin.command("ping")
        return True
    except DatabaseError:
        raise
    except (ServerSelectionTimeoutError, PyMongoError) as exc:
        raise DatabaseConnectionError(
            "Could not connect to MongoDB. Check the Atlas URI, network access list, and credentials."
        ) from exc
