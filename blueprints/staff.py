from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from database import get_db
from bson import ObjectId
from datetime import datetime
from functools import wraps

staff_bp = Blueprint('staff', __name__)

def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_role') not in ['staff', 'hod']:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@staff_bp.route('/dashboard')
@staff_required
def dashboard():
    return render_template('staff_dashboard.html')

@staff_bp.route('/api/assigned-subjects')
@staff_required
def get_assigned_subjects():
    db = get_db()
    staff_id = session['user_id']
    
    # Get staff assignments
    assignments = list(db.staff_subjects.find({'staff_id': staff_id}))
    
    subjects_data = []
    for assignment in assignments:
        subject = db.subjects.find_one({'_id': ObjectId(assignment['subject_id'])})
        assigned_class = db.classes.find_one({'_id': ObjectId(assignment['class_id'])})
        
        if subject and assigned_class:
            subjects_data.append({
                'id': str(subject['_id']),
                'name': subject['name'],
                'class_section': assigned_class['section'],
                'department': subject['department'],
                'semester': subject['semester']
            })
    
    return jsonify(subjects_data)

@staff_bp.route('/api/students/<subject_id>/<class_section>')
@staff_required
def get_students_for_subject(subject_id, class_section):
    db = get_db()
    subject = db.subjects.find_one({'_id': ObjectId(subject_id)})
    
    if not subject:
        return jsonify([]), 404
    
    students = list(db.users.find({
        'role': 'student',
        'department': subject['department'],
        'semester': subject['semester'],
        'class_section': class_section
    }))
    
    students_data = []
    for student in students:
        status = db.no_due_status.find_one({
            'student_id': str(student['_id']),
            'subject_id': subject_id
        })
        
        students_data.append({
            'id': str(student['_id']),
            'name': student['name'],
            'roll_number': student['roll_number'],
            'status': status['status'] if status else 'pending',
            'remarks': status['remarks'] if status else None,
            'updated_at': status['updated_at'].strftime('%Y-%m-%d %H:%M') if status and status.get('updated_at') else None
        })
    
    return jsonify(students_data)

@staff_bp.route('/api/approve-student', methods=['POST'])
@staff_required
def approve_student():
    data = request.get_json()
    student_id = data.get('student_id')
    subject_id = data.get('subject_id')
    action = data.get('action')  # approve or reject
    remarks = data.get('remarks', '')
    
    db = get_db()
    
    # Check if status already exists
    status = db.no_due_status.find_one({
        'student_id': student_id,
        'subject_id': subject_id
    })
    
    status_data = {
        'student_id': student_id,
        'subject_id': subject_id,
        'status': 'approved' if action == 'approve' else 'rejected',
        'approved_by': session['user_id'],
        'remarks': remarks,
        'updated_at': datetime.utcnow()
    }
    
    if status:
        db.no_due_status.update_one(
            {'_id': status['_id']},
            {'$set': status_data}
        )
    else:
        status_data['created_at'] = datetime.utcnow()
        db.no_due_status.insert_one(status_data)
    
    return jsonify({
        'success': True,
        'message': f'Student {action}d successfully'
    })
