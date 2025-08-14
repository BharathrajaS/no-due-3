from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from database import get_db
from bson import ObjectId
from datetime import datetime
from functools import wraps

hod_bp = Blueprint('hod', __name__)

def hod_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_role') != 'hod':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@hod_bp.route('/dashboard')
@hod_required
def dashboard():
    return render_template('hod_dashboard.html')

@hod_bp.route('/api/department-students')
@hod_required
def get_department_students():
    db = get_db()
    hod = db.users.find_one({'_id': ObjectId(session['user_id'])})
    students = list(db.users.find({
        'role': 'student',
        'department': hod['department']
    }))
    
    students_data = []
    for student in students:
        # Get subject approval count
        total_subjects = db.subjects.count_documents({
            'department': student['department'],
            'semester': student['semester']
        })
        
        approved_subjects = db.no_due_status.count_documents({
            'student_id': str(student['_id']),
            'status': 'approved'
        })
        
        # Get final approval status
        final_approval = db.final_approvals.find_one({'student_id': str(student['_id'])})
        
        students_data.append({
            'id': str(student['_id']),
            'name': student['name'],
            'roll_number': student['roll_number'],
            'class_section': student['class_section'],
            'year': student['year'],
            'semester': student['semester'],
            'approved_subjects': approved_subjects,
            'total_subjects': total_subjects,
            'final_status': final_approval['status'] if final_approval else 'not_requested',
            'final_remarks': final_approval['remarks'] if final_approval else None
        })
    
    return jsonify(students_data)

@hod_bp.route('/api/final-approve', methods=['POST'])
@hod_required
def final_approve():
    data = request.get_json()
    student_id = data.get('student_id')
    action = data.get('action')  # approve or reject
    remarks = data.get('remarks', '')
    
    db = get_db()
    final_approval = db.final_approvals.find_one({'student_id': student_id})
    if not final_approval:
        return jsonify({
            'success': False,
            'message': 'No final approval request found'
        }), 404
    
    update_data = {
        'status': 'approved' if action == 'approve' else 'rejected',
        'approved_by': session['user_id'],
        'remarks': remarks,
        'updated_at': datetime.utcnow()
    }
    
    db.final_approvals.update_one(
        {'_id': final_approval['_id']},
        {'$set': update_data}
    )
    
    return jsonify({
        'success': True,
        'message': f'Final approval {action}d successfully'
    })

@hod_bp.route('/api/staff')
@hod_required
def get_staff():
    db = get_db()
    hod = db.users.find_one({'_id': ObjectId(session['user_id'])})
    staff = list(db.users.find({
        'role': 'staff',
        'department': hod['department']
    }))
    
    staff_data = []
    for member in staff:
        assignments = db.staff_subjects.count_documents({'staff_id': str(member['_id'])})
        advised_classes = db.classes.count_documents({'class_advisor_id': str(member['_id'])})
        staff_data.append({
            'id': str(member['_id']),
            'name': member['name'],
            'email': member['email'],
            'assignments': assignments,
            'advised_classes': advised_classes
        })
    
    return jsonify(staff_data)

@hod_bp.route('/api/subjects')
@hod_required
def get_subjects():
    db = get_db()
    hod = db.users.find_one({'_id': ObjectId(session['user_id'])})
    subjects = list(db.subjects.find({'department': hod['department']}))
    
    subjects_data = []
    for subject in subjects:
        class_info = db.classes.find_one({'_id': ObjectId(subject['class_id'])}) if subject.get('class_id') else None
        subjects_data.append({
            'id': str(subject['_id']),
            'name': subject['name'],
            'code': subject['code'],
            'semester': subject['semester'],
            'credits': subject['credits'],
            'class_name': class_info['name'] if class_info else 'Not assigned'
        })
    
    return jsonify(subjects_data)

@hod_bp.route('/api/classes')
@hod_required
def get_classes():
    db = get_db()
    hod = db.users.find_one({'_id': ObjectId(session['user_id'])})
    classes = list(db.classes.find({'department': hod['department']}))
    
    classes_data = []
    for cls in classes:
        advisor = db.users.find_one({'_id': ObjectId(cls['class_advisor_id'])}) if cls.get('class_advisor_id') else None
        subject_count = db.subjects.count_documents({'class_id': str(cls['_id'])})
        
        classes_data.append({
            'id': str(cls['_id']),
            'name': cls['name'],
            'year': cls['year'],
            'semester': cls['semester'],
            'section': cls['section'],
            'advisor_name': advisor['name'] if advisor else 'Not assigned',
            'advisor_id': str(cls['class_advisor_id']) if cls.get('class_advisor_id') else None,
            'subject_count': subject_count
        })
    
    return jsonify(classes_data)

@hod_bp.route('/api/create-class', methods=['POST'])
@hod_required
def create_class():
    data = request.get_json()
    db = get_db()
    hod = db.users.find_one({'_id': ObjectId(session['user_id'])})
    
    # Check if class already exists
    existing = db.classes.find_one({
        'department': hod['department'],
        'year': int(data.get('year')),
        'semester': int(data.get('semester')),
        'section': data.get('section')
    })
    
    if existing:
        return jsonify({
            'success': False,
            'message': 'Class already exists'
        }), 400
    
    new_class_data = {
        'name': data.get('name'),
        'department': hod['department'],
        'year': int(data.get('year')),
        'semester': int(data.get('semester')),
        'section': data.get('section'),
        'class_advisor_id': None,
        'created_at': datetime.utcnow()
    }
    
    db.classes.insert_one(new_class_data)
    
    return jsonify({
        'success': True,
        'message': 'Class created successfully'
    })

@hod_bp.route('/api/create-subject', methods=['POST'])
@hod_required
def create_subject():
    data = request.get_json()
    db = get_db()
    hod = db.users.find_one({'_id': ObjectId(session['user_id'])})
    
    # Check if subject code already exists
    existing = db.subjects.find_one({
        'code': data.get('code'),
        'department': hod['department']
    })
    
    if existing:
        return jsonify({
            'success': False,
            'message': 'Subject code already exists'
        }), 400
    
    new_subject_data = {
        'name': data.get('name'),
        'code': data.get('code'),
        'department': hod['department'],
        'semester': int(data.get('semester')),
        'credits': int(data.get('credits', 3)),
        'class_id': data.get('class_id') if data.get('class_id') else None,
        'created_at': datetime.utcnow()
    }
    
    db.subjects.insert_one(new_subject_data)
    
    return jsonify({
        'success': True,
        'message': 'Subject created successfully'
    })

@hod_bp.route('/api/assign-class-advisor', methods=['POST'])
@hod_required
def assign_class_advisor():
    data = request.get_json()
    class_id = data.get('class_id')
    staff_id = data.get('staff_id')
    
    db = get_db()
    class_obj = db.classes.find_one({'_id': ObjectId(class_id)})
    staff = db.users.find_one({'_id': ObjectId(staff_id)})
    
    if not class_obj:
        return jsonify({
            'success': False,
            'message': 'Class not found'
        }), 404
    
    if not staff or staff['role'] != 'staff':
        return jsonify({
            'success': False,
            'message': 'Selected user is not a staff member'
        }), 400
    
    db.classes.update_one(
        {'_id': ObjectId(class_id)},
        {'$set': {'class_advisor_id': staff_id}}
    )
    
    return jsonify({
        'success': True,
        'message': 'Class advisor assigned successfully'
    })

@hod_bp.route('/api/assign-subject', methods=['POST'])
@hod_required
def assign_subject():
    data = request.get_json()
    staff_id = data.get('staff_id')
    subject_id = data.get('subject_id')
    class_id = data.get('class_id')
    
    db = get_db()
    
    # Check if assignment already exists
    existing = db.staff_subjects.find_one({
        'staff_id': staff_id,
        'subject_id': subject_id,
        'class_id': class_id
    })
    
    if existing:
        return jsonify({
            'success': False,
            'message': 'Assignment already exists'
        }), 400
    
    assignment_data = {
        'staff_id': staff_id,
        'subject_id': subject_id,
        'class_id': class_id,
        'created_at': datetime.utcnow()
    }
    
    db.staff_subjects.insert_one(assignment_data)
    
    return jsonify({
        'success': True,
        'message': 'Subject assigned successfully'
    })

@hod_bp.route('/api/class-statistics/<class_id>')
@hod_required
def get_class_statistics(class_id):
    try:
        db = get_db()
        # Get class info
        class_obj = db.classes.find_one({'_id': ObjectId(class_id)})
        
        if not class_obj:
            return jsonify({
                'total_students': 0,
                'completed_dues': 0,
                'pending_dues': 0
            })
        
        # Get all students in this class
        students = list(db.users.find({
            'role': 'student',
            'department': class_obj['department'],
            'year': class_obj['year'],
            'semester': class_obj['semester'],
            'class_section': class_obj['section']
        }))
        
        total_students = len(students)
        completed_dues = 0
        pending_dues = 0
        
        # Get subjects for this class
        subjects = list(db.subjects.find({
            'department': class_obj['department'],
            'semester': class_obj['semester']
        }))
        
        for student in students:
            # Check if all subjects are approved for this student
            all_approved = True
            for subject in subjects:
                status = db.no_due_status.find_one({
                    'student_id': str(student['_id']),
                    'subject_id': str(subject['_id'])
                })
                if not status or status['status'] != 'approved':
                    all_approved = False
                    break
            
            if all_approved and len(subjects) > 0:
                completed_dues += 1
            else:
                pending_dues += 1
        
        return jsonify({
            'total_students': total_students,
            'completed_dues': completed_dues,
            'pending_dues': pending_dues
        })
        
    except Exception as e:
        return jsonify({
            'total_students': 0,
            'completed_dues': 0,
            'pending_dues': 0
        })

@hod_bp.route('/api/subject-statistics/<subject_id>')
@hod_required
def get_subject_statistics(subject_id):
    try:
        db = get_db()
        subject = db.subjects.find_one({'_id': ObjectId(subject_id)})
        
        if not subject:
            return jsonify({
                'completed': 0,
                'pending': 0
            })
        
        # Get all students for this subject's department and semester
        students = list(db.users.find({
            'role': 'student',
            'department': subject['department'],
            'semester': subject['semester']
        }))
        
        completed = 0
        pending = 0
        
        for student in students:
            status = db.no_due_status.find_one({
                'student_id': str(student['_id']),
                'subject_id': subject_id
            })
            
            if status and status['status'] == 'approved':
                completed += 1
            else:
                pending += 1
        
        return jsonify({
            'completed': completed,
            'pending': pending
        })
        
    except Exception as e:
        return jsonify({
            'completed': 0,
            'pending': 0
        })

@hod_bp.route('/api/class-students/<class_id>')
@hod_required
def get_class_students(class_id):
    try:
        db = get_db()
        # Get class info
        class_obj = db.classes.find_one({'_id': ObjectId(class_id)})
        
        if not class_obj:
            return jsonify([])
        
        # Get all students in this class
        students = list(db.users.find({
            'role': 'student',
            'department': class_obj['department'],
            'year': class_obj['year'],
            'semester': class_obj['semester'],
            'class_section': class_obj['section']
        }))
        
        students_data = []
        for student in students:
            # Get subject approval count
            total_subjects = db.subjects.count_documents({
                'department': student['department'],
                'semester': student['semester']
            })
            
            approved_subjects = db.no_due_status.count_documents({
                'student_id': str(student['_id']),
                'status': 'approved'
            })
            
            # Get final approval status
            final_approval = db.final_approvals.find_one({'student_id': str(student['_id'])})
            
            # Get teacher notes/remarks for this student
            teacher_notes = []
            subjects = list(db.subjects.find({
                'department': student['department'],
                'semester': student['semester']
            }))
            
            for subject in subjects:
                status = db.no_due_status.find_one({
                    'student_id': str(student['_id']),
                    'subject_id': str(subject['_id'])
                })
                
                if status and status.get('remarks'):
                    teacher = db.users.find_one({'_id': ObjectId(status['approved_by'])}) if status.get('approved_by') else None
                    teacher_notes.append({
                        'subject': subject['name'],
                        'remarks': status['remarks'],
                        'teacher_name': teacher['name'] if teacher else None
                    })
            
            students_data.append({
                'id': str(student['_id']),
                'name': student['name'],
                'roll_number': student['roll_number'],
                'approved_subjects': approved_subjects,
                'total_subjects': total_subjects,
                'final_status': final_approval['status'] if final_approval else 'not_requested',
                'final_remarks': final_approval['remarks'] if final_approval else None,
                'teacher_notes': teacher_notes
            })
        
        return jsonify(students_data)
        
    except Exception as e:
        return jsonify([])

@hod_bp.route('/api/class-subjects/<class_id>/<int:semester>')
@hod_required
def get_class_subjects(class_id, semester):
    try:
        db = get_db()
        # Get class info
        class_obj = db.classes.find_one({'_id': ObjectId(class_id)})
        
        if not class_obj:
            return jsonify([])
        
        # Get all subjects for this semester and department
        subjects = list(db.subjects.find({
            'department': class_obj['department'],
            'semester': semester
        }))
        
        subjects_data = []
        for subject in subjects:
            # Get all students for this class
            students = list(db.users.find({
                'role': 'student',
                'department': class_obj['department'],
                'year': class_obj['year'],
                'semester': class_obj['semester'],
                'class_section': class_obj['section']
            }))
            
            completed = 0
            pending = 0
            
            for student in students:
                status = db.no_due_status.find_one({
                    'student_id': str(student['_id']),
                    'subject_id': str(subject['_id'])
                })
                
                if status and status['status'] == 'approved':
                    completed += 1
                else:
                    pending += 1
            
            subjects_data.append({
                'id': str(subject['_id']),
                'name': subject['name'],
                'code': subject['code'],
                'credits': subject['credits'],
                'completed': completed,
                'pending': pending
            })
        
        return jsonify(subjects_data)
        
    except Exception as e:
        return jsonify([])

@hod_bp.route('/api/class-subject-count/<class_id>/<int:semester>')
@hod_required
def get_class_subject_count(class_id, semester):
    try:
        db = get_db()
        # Get class info
        class_obj = db.classes.find_one({'_id': ObjectId(class_id)})
        
        if not class_obj:
            return jsonify({'subject_count': 0})
        
        # Count subjects for this semester and department
        subject_count = db.subjects.count_documents({
            'department': class_obj['department'],
            'semester': semester
        })
        
        return jsonify({
            'subject_count': subject_count
        })
        
    except Exception as e:
        return jsonify({
            'subject_count': 0
        })
