from pymongo import MongoClient
from flask import g, current_app
import certifi

def init_db(app):
    uri = app.config.get("MONGODB_URI")
    if not uri:
        raise ValueError("MONGODB_URI is not set in app config")

    client = MongoClient(
        uri,
        tls=True,
        tlsCAFile=certifi.where()
    )

    # If DB name not in URI, specify here
    app.config['MONGO_CLIENT'] = client
    app.config['MONGO_DB'] = client.get_database()

def get_db():
    if 'db' not in g:
        g.db = current_app.config['MONGO_DB']
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    # Mongo closes automatically; nothing to do
