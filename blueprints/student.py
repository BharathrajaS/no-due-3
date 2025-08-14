from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from database import get_db
from bson import ObjectId
from datetime import datetime
from functools import wraps

student_bp = Blueprint('student', __name__)

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_role') != 'student':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@student_bp.route('/dashboard')
@student_required
def dashboard():
    return render_template('student_dashboard.html')

@student_bp.route('/api/subjects')
@student_required
def get_subjects():
    db = get_db()
    user = db.users.find_one({'_id': ObjectId(session['user_id'])})
    
    subjects = list(db.subjects.find({
        'department': user['department'],
        'semester': user['semester']
    }))
    
    subject_data = []
    for subject in subjects:
        status = db.no_due_status.find_one({
            'student_id': str(user['_id']),
            'subject_id': str(subject['_id'])
        })
        
        subject_data.append({
            'id': str(subject['_id']),
            'name': subject['name'],
            'status': status['status'] if status else 'pending',
            'remarks': status['remarks'] if status else None,
            'updated_at': status['updated_at'].strftime('%Y-%m-%d %H:%M') if status and status.get('updated_at') else None
        })
    
    return jsonify(subject_data)

@student_bp.route('/api/final-approval-status')
@student_required
def get_final_approval_status():
    db = get_db()
    user = db.users.find_one({'_id': ObjectId(session['user_id'])})
    final_approval = db.final_approvals.find_one({'student_id': str(user['_id'])})
    
    # Check if all subjects are approved
    subjects = list(db.subjects.find({
        'department': user['department'],
        'semester': user['semester']
    }))
    
    all_approved = True
    for subject in subjects:
        status = db.no_due_status.find_one({
            'student_id': str(user['_id']),
            'subject_id': str(subject['_id'])
        })
        if not status or status['status'] != 'approved':
            all_approved = False
            break
    
    return jsonify({
        'can_request': all_approved and not final_approval,
        'status': final_approval['status'] if final_approval else None,
        'remarks': final_approval['remarks'] if final_approval else None,
        'updated_at': final_approval['updated_at'].strftime('%Y-%m-%d %H:%M') if final_approval and final_approval.get('updated_at') else None
    })

@student_bp.route('/api/request-final-approval', methods=['POST'])
@student_required
def request_final_approval():
    db = get_db()
    user = db.users.find_one({'_id': ObjectId(session['user_id'])})
    
    # Check if already requested
    existing = db.final_approvals.find_one({'student_id': str(user['_id'])})
    if existing:
        return jsonify({
            'success': False,
            'message': 'Final approval already requested'
        }), 400
    
    # Create final approval request
    final_approval_data = {
        'student_id': str(user['_id']),
        'status': 'pending',
        'approved_by': None,
        'remarks': None,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    
    db.final_approvals.insert_one(final_approval_data)
    
    return jsonify({
        'success': True,
        'message': 'Final approval requested successfully'
    })
