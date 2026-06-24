# app.py - Complete PostgreSQL Version
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import text

# Load environment variables from .env file
load_dotenv()

# Fix for Python 3.14 compatibility
import pkgutil
import importlib.util

def get_loader_patch(name):
    try:
        spec = importlib.util.find_spec(name)
        if spec is not None and spec.loader is not None:
            return spec.loader
    except (ValueError, AttributeError, ImportError):
        pass
    
    if hasattr(pkgutil, 'get_loader') and callable(pkgutil.get_loader):
        try:
            return pkgutil.get_loader(name)
        except:
            pass
    
    return None

if not hasattr(pkgutil, 'get_loader'):
    pkgutil.get_loader = get_loader_patch

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# PostgreSQL Database Configuration
# Format: postgresql://username:password@localhost:5432/database_name
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 
    'postgresql://hostel_admin:hostel@localhost:5432/hostel_db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# PostgreSQL specific optimizations
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,                # Number of connections to keep
    'pool_recycle': 3600,           # Recycle connections after 1 hour
    'pool_pre_ping': True,          # Check connection before using
    'max_overflow': 20,             # Extra connections if needed
    'pool_timeout': 30,             # Timeout for getting connection
}

db = SQLAlchemy(app)

# Models
class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(15))
    gender = db.Column(db.String(10), index=True)
    course = db.Column(db.String(50))
    year = db.Column(db.Integer)
    allocated_room = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    allocations = db.relationship('Allocation', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Student {self.roll_number}: {self.name}>'

class Room(db.Model):
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    block = db.Column(db.String(10), nullable=False, index=True)
    floor = db.Column(db.Integer, nullable=False)
    capacity = db.Column(db.Integer, default=2)
    occupied = db.Column(db.Integer, default=0)
    room_type = db.Column(db.String(20), index=True)
    gender = db.Column(db.String(10), index=True)
    status = db.Column(db.String(20), default='Available', index=True)
    
    # Relationships
    allocations = db.relationship('Allocation', backref='room', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Room {self.room_number} ({self.block})>'
    
    @property
    def available_spots(self):
        return self.capacity - self.occupied
    
    @property
    def is_full(self):
        return self.occupied >= self.capacity

class Allocation(db.Model):
    __tablename__ = 'allocations'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False)
    allocation_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    status = db.Column(db.String(20), default='Active', index=True)
    
    # Unique constraint to prevent duplicate active allocations
    __table_args__ = (
        db.UniqueConstraint('student_id', 'status', name='uq_active_student_allocation'),
    )
    
    def __repr__(self):
        return f'<Allocation {self.student_id} -> {self.room_id}>'

# Create tables
with app.app_context():
    db.create_all()
    
    # Create indexes for better performance
    try:
        db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_students_gender_year ON students(gender, year);'))
        db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_rooms_block_floor ON rooms(block, floor);'))
        db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_allocations_date_status ON allocations(allocation_date DESC, status);'))
        db.session.commit()
    except Exception as e:
        print(f"Note: Some indexes may already exist: {e}")
        db.session.rollback()


# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    # Get statistics
    total_students = Student.query.count()
    total_rooms = Room.query.count()
    
    # Only count students with allocated_room not None and not empty
    allocated_students = Student.query.filter(
        Student.allocated_room.isnot(None),
        Student.allocated_room != ''
    ).count()
    
    available_rooms = Room.query.filter_by(status='Available').count()
    
    # Aggregate totals
    result = db.session.query(
        func.coalesce(func.sum(Room.capacity), 0),
        func.coalesce(func.sum(Room.occupied), 0)
    ).first()
    
    total_capacity = result[0] or 0
    total_occupied = result[1] or 0
    
    # Prevent negative values
    total_capacity = max(0, total_capacity)
    total_occupied = max(0, total_occupied)
    
    # Calculate occupancy rate safely
    occupancy_rate = 0
    if total_capacity > 0:
        occupancy_rate = min(100, round((total_occupied / total_capacity * 100), 1))
    
    stats = {
        'total_students': total_students,
        'total_rooms': total_rooms,
        'allocated_students': allocated_students,
        'unallocated_students': total_students - allocated_students,
        'available_rooms': available_rooms,
        'total_capacity': total_capacity,
        'total_occupied': total_occupied,
        'occupancy_rate': occupancy_rate
    }
    
    recent_allocations = Allocation.query.options(
        db.joinedload(Allocation.student),
        db.joinedload(Allocation.room)
    ).order_by(
        Allocation.allocation_date.desc()
    ).limit(5).all()
    
    return render_template(
        'dashboard.html', 
        stats=stats, 
        recent_allocations=recent_allocations
    )

# Student CRUD
@app.route('/students')
def students():
    search = request.args.get('search', '').strip()
    gender = request.args.get('gender', '')
    course = request.args.get('course', '')
    year = request.args.get('year', '')
    
    query = Student.query
    
    if search:
        query = query.filter(
            db.or_(
                Student.name.ilike(f'%{search}%'),
                Student.roll_number.ilike(f'%{search}%'),
                Student.email.ilike(f'%{search}%')
            )
        )
    if gender:
        query = query.filter_by(gender=gender)
    if course:
        query = query.filter_by(course=course)
    if year:
        query = query.filter_by(year=int(year))
    
    students = query.order_by(Student.name).all()
    return render_template('students.html', students=students)

@app.route('/student/add', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        try:
            # Validate inputs
            roll_number = request.form.get('roll_number', '').strip()
            email = request.form.get('email', '').strip()
            name = request.form.get('name', '').strip()
            
            if not all([roll_number, email, name]):
                flash('Name, Roll Number, and Email are required!', 'error')
                return render_template('add_student.html')
            
            # Check for duplicates
            existing = Student.query.filter_by(roll_number=roll_number).first()
            if existing:
                flash('Roll number already exists!', 'error')
                return render_template('add_student.html')
            
            existing = Student.query.filter_by(email=email).first()
            if existing:
                flash('Email already exists!', 'error')
                return render_template('add_student.html')
            
            student = Student(
                name=name,
                roll_number=roll_number,
                email=email,
                phone=request.form.get('phone', '').strip(),
                gender=request.form.get('gender'),
                course=request.form.get('course', '').strip(),
                year=int(request.form.get('year', 1))
            )
            db.session.add(student)
            db.session.commit()
            flash('Student added successfully!', 'success')
            return redirect(url_for('students'))
        except ValueError:
            flash('Invalid year format!', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding student: {str(e)}', 'error')
    
    return render_template('add_student.html')

@app.route('/student/edit/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    student = Student.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip()
            name = request.form.get('name', '').strip()
            
            if not all([email, name]):
                flash('Name and Email are required!', 'error')
                return render_template('edit_student.html', student=student)
            
            # Check if email already exists (excluding current student)
            existing = Student.query.filter(
                Student.email == email,
                Student.id != id
            ).first()
            if existing:
                flash('Email already exists!', 'error')
                return render_template('edit_student.html', student=student)
            
            student.name = name
            student.email = email
            student.phone = request.form.get('phone', '').strip()
            student.gender = request.form.get('gender')
            student.course = request.form.get('course', '').strip()
            student.year = int(request.form.get('year', 1))
            
            db.session.commit()
            flash('Student updated successfully!', 'success')
            return redirect(url_for('students'))
        except ValueError:
            flash('Invalid year format!', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating student: {str(e)}', 'error')
    
    return render_template('edit_student.html', student=student)

@app.route('/student/delete/<int:id>')
def delete_student(id):
    student = Student.query.get_or_404(id)
    
    try:
        # Check if student is allocated
        if student.allocated_room:
            # Find and deallocate the student
            allocation = Allocation.query.filter_by(
                student_id=id,
                status='Active'
            ).first()
            if allocation:
                room = Room.query.get(allocation.room_id)
                if room:
                    room.occupied = max(0, room.occupied - 1)
                    if room.occupied < room.capacity:
                        room.status = 'Available'
        
        # Delete student (cascade will handle allocations)
        db.session.delete(student)
        db.session.commit()
        flash('Student deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting student: {str(e)}', 'error')
    
    return redirect(url_for('students'))

# Room CRUD
@app.route('/rooms')
def rooms():
    block = request.args.get('block', '')
    room_type = request.args.get('room_type', '')
    status = request.args.get('status', '')
    gender = request.args.get('gender', '')
    
    query = Room.query
    
    if block:
        query = query.filter_by(block=block)
    if room_type:
        query = query.filter_by(room_type=room_type)
    if status:
        query = query.filter_by(status=status)
    if gender:
        query = query.filter_by(gender=gender)
    
    rooms = query.order_by(Room.block, Room.floor, Room.room_number).all()
    return render_template('rooms.html', rooms=rooms)

@app.route('/room/add', methods=['GET', 'POST'])
def add_room():
    if request.method == 'POST':
        try:
            room_number = request.form.get('room_number', '').strip()
            if not room_number:
                flash('Room number is required!', 'error')
                return render_template('add_room.html')
            
            # Check if room number already exists
            existing = Room.query.filter_by(room_number=room_number).first()
            if existing:
                flash('Room number already exists!', 'error')
                return render_template('add_room.html')
            
            room = Room(
                room_number=room_number,
                block=request.form.get('block', '').strip(),
                floor=int(request.form.get('floor', 1)),
                capacity=int(request.form.get('capacity', 2)),
                room_type=request.form.get('room_type'),
                gender=request.form.get('gender')
            )
            db.session.add(room)
            db.session.commit()
            flash('Room added successfully!', 'success')
            return redirect(url_for('rooms'))
        except ValueError:
            flash('Invalid numeric value!', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding room: {str(e)}', 'error')
    
    return render_template('add_room.html')

@app.route('/room/edit/<int:id>', methods=['GET', 'POST'])
def edit_room(id):
    room = Room.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            new_capacity = int(request.form.get('capacity', 2))
            
            if new_capacity < room.occupied:
                flash(f'Cannot reduce capacity below current occupancy ({room.occupied})', 'error')
                return render_template('edit_room.html', room=room)
            
            room.block = request.form.get('block', '').strip()
            room.floor = int(request.form.get('floor', 1))
            room.capacity = new_capacity
            room.room_type = request.form.get('room_type')
            room.gender = request.form.get('gender')
            
            if room.occupied >= room.capacity:
                room.status = 'Full'
            else:
                room.status = 'Available'
            
            db.session.commit()
            flash('Room updated successfully!', 'success')
            return redirect(url_for('rooms'))
        except ValueError:
            flash('Invalid numeric value!', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating room: {str(e)}', 'error')
    
    return render_template('edit_room.html', room=room)

@app.route('/room/delete/<int:id>')
def delete_room(id):
    room = Room.query.get_or_404(id)
    
    try:
        # Check if room has active allocations
        active_allocations = Allocation.query.filter_by(
            room_id=id, 
            status='Active'
        ).count()
        
        if active_allocations > 0:
            flash('Cannot delete room with active allocations!', 'error')
            return redirect(url_for('rooms'))
        
        # Delete room (cascade will handle inactive allocations)
        db.session.delete(room)
        db.session.commit()
        flash('Room deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting room: {str(e)}', 'error')
    
    return redirect(url_for('rooms'))

# Allocation Management
@app.route('/allocations')
def allocations():
    allocations = Allocation.query.options(
        db.joinedload(Allocation.student),
        db.joinedload(Allocation.room)
    ).order_by(
        Allocation.allocation_date.desc()
    ).all()
    return render_template('allocations.html', allocations=allocations)

@app.route('/allocate', methods=['GET', 'POST'])
def allocate_room():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        room_id = request.form.get('room_id')
        
        if not student_id or not room_id:
            flash('Please select both student and room!', 'error')
            return redirect(url_for('allocate_room'))
        
        try:
            student_id = int(student_id)
            room_id = int(room_id)
        except ValueError:
            flash('Invalid student or room selection!', 'error')
            return redirect(url_for('allocate_room'))
        
        student = Student.query.get(student_id)
        room = Room.query.get(room_id)
        
        if not student or not room:
            flash('Invalid student or room!', 'error')
            return redirect(url_for('allocate_room'))
        
        # Check if student is already allocated
        if student.allocated_room and student.allocated_room != '':
            flash(f'Student {student.name} already has a room allocated!', 'error')
            return redirect(url_for('allocate_room'))
        
        # Check room availability
        if room.occupied >= room.capacity:
            flash('Room is full!', 'error')
            return redirect(url_for('allocate_room'))
        
        # Check gender compatibility
        if student.gender != room.gender:
            flash('Gender mismatch between student and room!', 'error')
            return redirect(url_for('allocate_room'))
        
        try:
            # Create allocation
            allocation = Allocation(
                student_id=student_id,
                room_id=room_id
            )
            
            # Update student and room
            student.allocated_room = room.room_number
            room.occupied += 1
            
            if room.occupied >= room.capacity:
                room.status = 'Full'
            
            db.session.add(allocation)
            db.session.commit()
            
            flash('Room allocated successfully!', 'success')
            return redirect(url_for('allocations'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error allocating room: {str(e)}', 'error')
    
    # GET request - show allocation form
    unallocated_students = Student.query.filter(
        (Student.allocated_room.is_(None)) | (Student.allocated_room == '')
    ).order_by(Student.name).all()
    
    available_rooms = Room.query.filter(
        Room.occupied < Room.capacity
    ).order_by(Room.block, Room.room_number).all()
    
    return render_template(
        'allocate_room.html', 
        students=unallocated_students, 
        rooms=available_rooms
    )

@app.route('/deallocate/<int:allocation_id>')
def deallocate_room(allocation_id):
    allocation = Allocation.query.get_or_404(allocation_id)
    
    try:
        student = Student.query.get(allocation.student_id)
        room = Room.query.get(allocation.room_id)
        
        if student:
            student.allocated_room = None
        
        if room:
            room.occupied = max(0, room.occupied - 1)
            if room.occupied < room.capacity:
                room.status = 'Available'
        
        allocation.status = 'Inactive'
        db.session.commit()
        
        flash('Room deallocated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deallocating room: {str(e)}', 'error')
    
    return redirect(url_for('allocations'))

# API endpoints for AJAX calls
@app.route('/api/available-rooms/<gender>')
def get_available_rooms(gender):
    rooms = Room.query.filter(
        Room.status == 'Available',
        Room.gender == gender,
        Room.occupied < Room.capacity
    ).all()
    
    return jsonify([{
        'id': room.id,
        'room_number': room.room_number,
        'block': room.block,
        'floor': room.floor,
        'capacity': room.capacity,
        'occupied': room.occupied,
        'available_spots': room.capacity - room.occupied
    } for room in rooms])

@app.route('/api/student/<int:id>')
def get_student(id):
    student = Student.query.get_or_404(id)
    return jsonify({
        'id': student.id,
        'name': student.name,
        'roll_number': student.roll_number,
        'gender': student.gender,
        'allocated_room': student.allocated_room,
        'course': student.course,
        'year': student.year
    })

@app.route('/api/room-status/<int:room_id>')
def get_room_status(room_id):
    room = Room.query.get_or_404(room_id)
    return jsonify({
        'id': room.id,
        'room_number': room.room_number,
        'capacity': room.capacity,
        'occupied': room.occupied,
        'available': room.capacity - room.occupied,
        'status': room.status,
        'gender': room.gender,
        'block': room.block,
        'floor': room.floor
    })

@app.route('/api/stats')
def get_stats():
    total_students = Student.query.count()
    total_rooms = Room.query.count()
    
    allocated_students = Student.query.filter(
        Student.allocated_room.isnot(None),
        Student.allocated_room != ''
    ).count()
    
    available_rooms = Room.query.filter_by(status='Available').count()
    
    result = db.session.query(
        func.coalesce(func.sum(Room.capacity), 0),
        func.coalesce(func.sum(Room.occupied), 0)
    ).first()
    
    total_capacity = result[0] or 0
    total_occupied = result[1] or 0
    
    occupancy_rate = 0
    if total_capacity > 0:
        occupancy_rate = min(100, round((total_occupied / total_capacity * 100), 1))
    
    return jsonify({
        'total_students': total_students,
        'total_rooms': total_rooms,
        'allocated_students': allocated_students,
        'available_rooms': available_rooms,
        'total_capacity': total_capacity,
        'total_occupied': total_occupied,
        'occupancy_rate': occupancy_rate
    })

@app.route('/api/courses')
def get_courses():
    courses = db.session.query(Student.course).distinct().order_by(Student.course).all()
    return jsonify([course[0] for course in courses if course[0]])

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)