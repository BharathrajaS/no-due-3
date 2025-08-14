from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from database import init_db, get_db
from bson import ObjectId

app = Flask(__name__)
app.config['SECRET_KEY'] = 's8d7f6s8d7f6s8d7f6s8d7f6!@#%GHSDFhwefhwe'
app.config['MONGODB_URI'] = os.environ.get("MONGODB_URI")
# Initialize MongoDB
init_db(app)

# Import blueprints
from blueprints.auth import auth_bp
from blueprints.student import student_bp
from blueprints.staff import staff_bp
from blueprints.hod import hod_bp

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(student_bp, url_prefix='/student')
app.register_blueprint(staff_bp, url_prefix='/staff')
app.register_blueprint(hod_bp, url_prefix='/hod')

@app.route('/')
def index():
    if 'user_id' in session:
        db = get_db()
        user = db.users.find_one({'_id': ObjectId(session['user_id'])})
        if user is None:
            # User not found, clear session and redirect to login
            session.pop('user_id', None)
            return redirect(url_for('login'))
        if user['role'] == 'student':
            return redirect(url_for('student.dashboard'))
        elif user['role'] == 'staff':
            return redirect(url_for('staff.dashboard'))
        elif user['role'] == 'hod':
            return redirect(url_for('hod.dashboard'))
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

def create_sample_data():
    db = get_db()
    
    # Create sample HOD
    if not db.users.find_one({'role': 'hod'}):
        hod_data = {
            'name': 'Dr. John Smith',
            'email': 'hod@college.edu',
            'password': 'password123',
            'role': 'hod',
            'department': 'CSE',
            'class_section': 'A',
            'year': None,
            'semester': None,
            'roll_number': None,
            'created_at': datetime.utcnow()
        }
        db.users.insert_one(hod_data)
    
    # Create sample classes
    if not db.classes.find_one():
        classes_data = [
            {
                'name': 'CSE 1st Year Section A',
                'department': 'CSE',
                'year': 1,
                'semester': 1,
                'section': 'A',
                'class_advisor_id': None,
                'created_at': datetime.utcnow()
            },
            {
                'name': 'CSE 1st Year Section B',
                'department': 'CSE',
                'year': 1,
                'semester': 1,
                'section': 'B',
                'class_advisor_id': None,
                'created_at': datetime.utcnow()
            },
            {
                'name': 'CSE 2nd Year Section A',
                'department': 'CSE',
                'year': 2,
                'semester': 3,
                'section': 'A',
                'class_advisor_id': None,
                'created_at': datetime.utcnow()
            },
            {
                'name': 'CSE 2nd Year Section B',
                'department': 'CSE',
                'year': 2,
                'semester': 3,
                'section': 'B',
                'class_advisor_id': None,
                'created_at': datetime.utcnow()
            }
        ]
        db.classes.insert_many(classes_data)
    
    # Create sample subjects
    if not db.subjects.find_one():
        # Get the first class for assignment
        first_class = db.classes.find_one()
        subjects_data = [
            {
                'name': 'Mathematics',
                'code': 'MATH101',
                'department': 'CSE',
                'semester': 1,
                'credits': 4,
                'class_id': str(first_class['_id']) if first_class else None,
                'created_at': datetime.utcnow()
            },
            {
                'name': 'Physics',
                'code': 'PHY101',
                'department': 'CSE',
                'semester': 1,
                'credits': 3,
                'class_id': str(first_class['_id']) if first_class else None,
                'created_at': datetime.utcnow()
            },
            {
                'name': 'Chemistry',
                'code': 'CHEM101',
                'department': 'CSE',
                'semester': 1,
                'credits': 3,
                'class_id': str(first_class['_id']) if first_class else None,
                'created_at': datetime.utcnow()
            },
            {
                'name': 'Programming',
                'code': 'CS101',
                'department': 'CSE',
                'semester': 1,
                'credits': 4,
                'class_id': str(first_class['_id']) if first_class else None,
                'created_at': datetime.utcnow()
            },
            {
                'name': 'English',
                'code': 'ENG101',
                'department': 'CSE',
                'semester': 1,
                'credits': 2,
                'class_id': str(first_class['_id']) if first_class else None,
                'created_at': datetime.utcnow()
            }
        ]
        db.subjects.insert_many(subjects_data)

if __name__ == "__main__":
   with app.app_context():
    create_sample_data()
    app.run(debug=True)
