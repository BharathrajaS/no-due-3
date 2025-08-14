from flask import Blueprint, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db
from bson import ObjectId
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    db = get_db()
    user = db.users.find_one({'email': email})
    
    if user and user['password'] == password:
        session['user_id'] = str(user['_id'])
        session['user_role'] = user['role']
        session['user_name'] = user['name']
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'role': user['role'],
            'redirect': f'/{user["role"]}/dashboard'
        })
    
    return jsonify({
        'success': False,
        'message': 'Invalid email or password'
    }), 401

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    db = get_db()
    
    # Check if user already exists
    if db.users.find_one({'email': data.get('email')}):
        return jsonify({
            'success': False,
            'message': 'Email already registered'
        }), 400
    
    # Create new user
    user_data = {
        'name': data.get('name'),
        'email': data.get('email'),
        'password': data.get('password'),
        'role': data.get('role'),
        'department': data.get('department'),
        'class_section': data.get('class_section'),
        'year': int(data.get('year')) if data.get('role') == 'student' and data.get('year') else None,
        'semester': int(data.get('semester')) if data.get('role') == 'student' and data.get('semester') else None,
        'roll_number': data.get('roll_number') if data.get('role') == 'student' else None,
        'created_at': datetime.utcnow()
    }
    
    db.users.insert_one(user_data)
    
    return jsonify({
        'success': True,
        'message': 'Registration successful'
    })

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    })
