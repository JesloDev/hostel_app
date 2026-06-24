# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import sys
import importlib.util
from sqlalchemy import func

# Fix for Python 3.14 compatibility - Monkey patch pkgutil
import pkgutil

# Create a proper get_loader function that works with Python 3.14
def get_loader_patch(name):
    try:
        # Try to find the spec using importlib
        spec = importlib.util.find_spec(name)
        if spec is not None and spec.loader is not None:
            return spec.loader
    except (ValueError, AttributeError, ImportError):
        pass
    
    # Fallback: try to use the old get_loader if available
    if hasattr(pkgutil, 'get_loader') and callable(pkgutil.get_loader):
        try:
            return pkgutil.get_loader(name)
        except:
            pass
    
    return None

# Only patch if get_loader doesn't exist
if not hasattr(pkgutil, 'get_loader'):
    pkgutil.get_loader = get_loader_patch

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hostel.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15))
    gender = db.Column(db.String(10))
    course = db.Column(db.String(50))
    year = db.Column(db.Integer)
    allocated_room = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(20), unique=True, nullable=False)
    block = db.Column(db.String(10), nullable=False)
    floor = db.Column(db.Integer, nullable=False)
    capacity = db.Column(db.Integer, default=2)
    occupied = db.Column(db.Integer, default=0)
    room_type = db.Column(db.String(20))
    gender = db.Column(db.String(10))
    status = db.Column(db.String(20), default='Available')

class Allocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    allocation_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Active')
    
    student = db.relationship('Student', backref='allocations')
    room = db.relationship('Room', backref='allocations')

# Create tables
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    total_students = Student.query.count()
    total_rooms = Room.query.count()
    
    # Only count students with allocated_room not None and not empty
    allocated_students = Student.query.filter(
        Student.allocated_room.isnot(None),
        Student.allocated_room != ''
    ).count()
    
    available_rooms = Room.query.filter_by(status='Available').count()
    total_capacity = db.session.query(func.sum(Room.capacity)).scalar() or 0
    total_occupied = db.session.query(func.sum(Room.occupied)).scalar() or 0
    
    # Prevent negative values
    total_capacity = max(0, total_capacity)
    total_occupied = max(0, total_occupied)
    
    # Calculate occupancy rate safely (prevents negative percentages)
    occupancy_rate = 0
    if total_capacity > 0:
        occupancy_rate = round((total_occupied / total_capacity * 100), 1)
        # Ensure it doesn't exceed 100%
        occupancy_rate = min(100, occupancy_rate)
    
    stats = {
        'total_students': total_students,
        'total_rooms': total_rooms,
        'allocated_students': allocated_students,
        'available_rooms': available_rooms,
        'total_capacity': total_capacity,
        'total_occupied': total_occupied,
        'occupancy_rate': occupancy_rate
    }
    
    recent_allocations = Allocation.query.order_by(
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
    search = request.args.get('search', '')
    gender = request.args.get('gender', '')
    
    query = Student.query
    
    if search:
        query = query.filter(
            db.or_(
                Student.name.contains(search),
                Student.roll_number.contains(search),
                Student.email.contains(search)
            )
        )
    if gender:
        query = query.filter_by(gender=gender)
    
    students = query.all()
    return render_template('students.html', students=students)

@app.route('/student/add', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        try:
            existing = Student.query.filter_by(roll_number=request.form['roll_number']).first()
            if existing:
                flash('Roll number already exists!', 'error')
                return render_template('add_student.html')
            
            existing = Student.query.filter_by(email=request.form['email']).first()
            if existing:
                flash('Email already exists!', 'error')
                return render_template('add_student.html')
            
            student = Student(
                name=request.form['name'],
                roll_number=request.form['roll_number'],
                email=request.form['email'],
                phone=request.form['phone'],
                gender=request.form['gender'],
                course=request.form['course'],
                year=int(request.form['year'])
            )
            db.session.add(student)
            db.session.commit()
            flash('Student added successfully!', 'success')
            return redirect(url_for('students'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding student: {str(e)}', 'error')
    
    return render_template('add_student.html')

@app.route('/student/edit/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    student = Student.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            existing = Student.query.filter(
                Student.email == request.form['email'],
                Student.id != id
            ).first()
            if existing:
                flash('Email already exists!', 'error')
                return render_template('edit_student.html', student=student)
            
            student.name = request.form['name']
            student.email = request.form['email']
            student.phone = request.form['phone']
            student.gender = request.form['gender']
            student.course = request.form['course']
            student.year = int(request.form['year'])
            
            db.session.commit()
            flash('Student updated successfully!', 'success')
            return redirect(url_for('students'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating student: {str(e)}', 'error')
    
    return render_template('edit_student.html', student=student)

@app.route('/student/delete/<int:id>')
def delete_student(id):
    student = Student.query.get_or_404(id)
    
    try:
        allocations = Allocation.query.filter_by(student_id=id).all()
        for allocation in allocations:
            room = Room.query.get(allocation.room_id)
            if room:
                room.occupied = max(0, room.occupied - 1)
                if room.occupied < room.capacity:
                    room.status = 'Available'
            db.session.delete(allocation)
        
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
    
    query = Room.query
    
    if block:
        query = query.filter_by(block=block)
    if room_type:
        query = query.filter_by(room_type=room_type)
    if status:
        query = query.filter_by(status=status)
    
    rooms = query.all()
    return render_template('rooms.html', rooms=rooms)

@app.route('/room/add', methods=['GET', 'POST'])
def add_room():
    if request.method == 'POST':
        try:
            existing = Room.query.filter_by(room_number=request.form['room_number']).first()
            if existing:
                flash('Room number already exists!', 'error')
                return render_template('add_room.html')
            
            room = Room(
                room_number=request.form['room_number'],
                block=request.form['block'],
                floor=int(request.form['floor']),
                capacity=int(request.form['capacity']),
                room_type=request.form['room_type'],
                gender=request.form['gender']
            )
            db.session.add(room)
            db.session.commit()
            flash('Room added successfully!', 'success')
            return redirect(url_for('rooms'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding room: {str(e)}', 'error')
    
    return render_template('add_room.html')

@app.route('/room/edit/<int:id>', methods=['GET', 'POST'])
def edit_room(id):
    room = Room.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            new_capacity = int(request.form['capacity'])
            
            if new_capacity < room.occupied:
                flash(f'Cannot reduce capacity below current occupancy ({room.occupied})', 'error')
                return render_template('edit_room.html', room=room)
            
            room.block = request.form['block']
            room.floor = int(request.form['floor'])
            room.capacity = new_capacity
            room.room_type = request.form['room_type']
            room.gender = request.form['gender']
            
            if room.occupied >= room.capacity:
                room.status = 'Full'
            else:
                room.status = 'Available'
            
            db.session.commit()
            flash('Room updated successfully!', 'success')
            return redirect(url_for('rooms'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating room: {str(e)}', 'error')
    
    return render_template('edit_room.html', room=room)

@app.route('/room/delete/<int:id>')
def delete_room(id):
    room = Room.query.get_or_404(id)
    
    try:
        active_allocations = Allocation.query.filter_by(room_id=id, status='Active').count()
        if active_allocations > 0:
            flash('Cannot delete room with active allocations!', 'error')
            return redirect(url_for('rooms'))
        
        allocations = Allocation.query.filter_by(room_id=id).all()
        for allocation in allocations:
            student = Student.query.get(allocation.student_id)
            if student:
                student.allocated_room = None
            db.session.delete(allocation)
        
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
    allocations = Allocation.query.order_by(Allocation.allocation_date.desc()).all()
    return render_template('allocations.html', allocations=allocations)

@app.route('/allocate', methods=['GET', 'POST'])
def allocate_room():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        room_id = request.form.get('room_id')
        
        if not student_id or not room_id:
            flash('Please select both student and room!', 'error')
            return redirect(url_for('allocate_room'))
        
        student = Student.query.get(student_id)
        room = Room.query.get(room_id)
        
        if not student or not room:
            flash('Invalid student or room!', 'error')
            return redirect(url_for('allocate_room'))
        
        # Check if student is already allocated (prevents duplicate allocation)
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
        
        # Check if room already has an active allocation (additional safety)
        existing_allocation = Allocation.query.filter_by(
            room_id=room_id,
            status='Active'
        ).count()
        if existing_allocation >= room.capacity:
            flash('Room is already fully occupied!', 'error')
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
    ).all()
    available_rooms = Room.query.filter(
        Room.status.in_(['Available', 'Full'])
    ).all()
    
    return render_template('allocate_room.html', 
                         students=unallocated_students, 
                         rooms=available_rooms)

@app.route('/deallocate/<int:allocation_id>')
def deallocate_room(allocation_id):
    allocation = Allocation.query.get_or_404(allocation_id)
    
    try:
        student = Student.query.get(allocation.student_id)
        room = Room.query.get(allocation.room_id)
        
        if student:
            student.allocated_room = None
        
        if room:
            room.occupied = max(0, room.occupied - 1)  # Prevent negative
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
    rooms = Room.query.filter_by(status='Available', gender=gender).all()
    return jsonify([{
        'id': room.id,
        'room_number': room.room_number,
        'block': room.block,
        'floor': room.floor,
        'capacity': room.capacity,
        'occupied': room.occupied
    } for room in rooms])

@app.route('/api/student/<int:id>')
def get_student(id):
    student = Student.query.get_or_404(id)
    return jsonify({
        'id': student.id,
        'name': student.name,
        'roll_number': student.roll_number,
        'gender': student.gender,
        'allocated_room': student.allocated_room
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
        'status': room.status
    })

@app.route('/api/stats')
def get_stats():
    total_students = Student.query.count()
    total_rooms = Room.query.count()
    allocated_students = Student.query.filter(Student.allocated_room.isnot(None)).count()
    available_rooms = Room.query.filter_by(status='Available').count()
    total_capacity = db.session.query(db.func.sum(Room.capacity)).scalar() or 0
    total_occupied = db.session.query(db.func.sum(Room.occupied)).scalar() or 0
    
    return jsonify({
        'total_students': total_students,
        'total_rooms': total_rooms,
        'allocated_students': allocated_students,
        'available_rooms': available_rooms,
        'occupancy_rate': round((total_occupied / total_capacity * 100) if total_capacity > 0 else 0, 1)
    })

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