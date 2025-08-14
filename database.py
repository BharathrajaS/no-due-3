from pymongo import MongoClient
from flask import g
import certifi 

def init_db(app):
    app.config['MONGO_CLIENT'] = MongoClient(app.config['MONGODB_URI'])
    app.config['MONGO_DB'] = app.config['MONGO_CLIENT'].get_database()

def get_db():
    if 'db' not in g:
        from flask import current_app
        g.db = current_app.config['MONGO_DB']
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        # MongoDB connections are handled automatically
        pass
