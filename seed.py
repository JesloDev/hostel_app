# seed.py
from app import app, db, Student, Room, Allocation
from datetime import datetime, timedelta
import random

# Sample data
FIRST_NAMES = [
    'John', 'Jane', 'Michael', 'Sarah', 'David', 'Emma', 'James', 'Olivia',
    'Robert', 'Ava', 'William', 'Sophia', 'Joseph', 'Mia', 'Charles', 'Charlotte',
    'Thomas', 'Amelia', 'Daniel', 'Harper', 'Matthew', 'Evelyn', 'Anthony', 'Abigail',
    'Donald', 'Emily', 'Mark', 'Elizabeth', 'Paul', 'Sofia', 'Steven', 'Avery',
    'Andrew', 'Ella', 'Kenneth', 'Madison', 'Joshua', 'Scarlett', 'Kevin', 'Victoria',
    'Brian', 'Aria', 'George', 'Grace', 'Timothy', 'Chloe', 'Ronald', 'Camila',
    'Edward', 'Penelope', 'Jason', 'Riley', 'Jeffrey', 'Layla', 'Ryan', 'Zoe',
    'Jacob', 'Nora', 'Gary', 'Lily', 'Nicholas', 'Eleanor', 'Eric', 'Hannah',
    'Jonathan', 'Lillian', 'Stephen', 'Addison', 'Larry', 'Stella', 'Justin', 'Natalie',
    'Scott', 'Zoey', 'Brandon', 'Leah', 'Benjamin', 'Hazel', 'Samuel', 'Violet',
    'Raymond', 'Aurora', 'Gregory', 'Savannah', 'Frank', 'Audrey', 'Alexander',
    'Brooklyn', 'Patrick', 'Bella', 'Jack', 'Claire', 'Dennis', 'Skylar', 'Jerry'
]

LAST_NAMES = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
    'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
    'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Perez', 'Thompson',
    'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson', 'Walker',
    'Young', 'Allen', 'King', 'Wright', 'Scott', 'Torres', 'Nguyen', 'Hill',
    'Flores', 'Green', 'Adams', 'Nelson', 'Baker', 'Hall', 'Rivera', 'Campbell',
    'Mitchell', 'Carter', 'Roberts', 'Turner', 'Phillips', 'Evans', 'Collins',
    'Edwards', 'Stewart', 'Morris', 'Murphy', 'Cook', 'Rogers', 'Morgan', 'Peterson'
]

COURSES = [
    'Computer Science', 'Engineering', 'Business Administration',
    'Mathematics', 'Physics', 'Biology', 'Chemistry', 'Economics',
    'Psychology', 'Sociology', 'English', 'History', 'Political Science',
    'Law', 'Medicine', 'Architecture', 'Design', 'Education'
]

def random_date(start_date, end_date):
    """Generate a random date between two dates"""
    time_between = end_date - start_date
    days_between = time_between.days
    random_days = random.randrange(days_between)
    return start_date + timedelta(days=random_days)

def create_students(num_students=50):
    """Create students with realistic data"""
    students = []
    used_emails = set()
    used_roll_numbers = set()
    
    for i in range(num_students):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        name = f"{first_name} {last_name}"
        
        # Generate unique roll number
        roll_number = f"{random.randint(2020, 2025)}-{random.randint(1000, 9999)}"
        while roll_number in used_roll_numbers:
            roll_number = f"{random.randint(2020, 2025)}-{random.randint(1000, 9999)}"
        used_roll_numbers.add(roll_number)
        
        # Generate unique email
        email = f"{first_name.lower()}.{last_name.lower()}@{random.choice(['university.edu', 'college.edu', 'student.edu'])}"
        email = email.replace(" ", "")
        counter = 1
        while email in used_emails:
            email = f"{first_name.lower()}.{last_name.lower()}{counter}@{random.choice(['university.edu', 'college.edu', 'student.edu'])}"
            email = email.replace(" ", "")
            counter += 1
        used_emails.add(email)
        
        # Random phone number
        phone = f"+1{random.randint(200, 999)}{random.randint(1000000, 9999999)}"
        
        # Random gender
        gender = random.choice(['Male', 'Female'])
        
        # Random course
        course = random.choice(COURSES)
        
        # Random year (1-4)
        year = random.randint(1, 4)
        
        student = Student(
            name=name,
            roll_number=roll_number,
            email=email,
            phone=phone,
            gender=gender,
            course=course,
            year=year,
            allocated_room=None,  # Initially not allocated
            created_at=datetime.utcnow()
        )
        students.append(student)
    
    return students

def create_rooms():
    """Create rooms with different configurations"""
    rooms = []
    blocks = ['A', 'B', 'C', 'D', 'E']
    room_types = ['AC', 'Non-AC']
    genders = ['Male', 'Female']
    
    room_number = 101
    
    for block in blocks:
        for floor in range(1, 4):  # 3 floors per block
            # 4 rooms per floor per block
            for room_num in range(1, 5):
                gender = random.choice(genders)
                room_type = random.choice(room_types)
                
                # Capacity varies (2-4)
                capacity = random.choice([2, 3, 4])
                
                room = Room(
                    room_number=str(room_number),
                    block=block,
                    floor=floor,
                    capacity=capacity,
                    occupied=0,
                    room_type=room_type,
                    gender=gender,
                    status='Available'
                )
                rooms.append(room)
                room_number += 1
    
    return rooms

def allocate_rooms_randomly(students, rooms, num_to_allocate=30):
    """Randomly allocate rooms to some students with validation"""
    allocations = []
    allocated_students = set()
    room_occupancy = {room.id: 0 for room in rooms}
    
    # Shuffle lists for randomness
    random.shuffle(students)
    random.shuffle(rooms)
    
    allocated_count = 0
    max_attempts = 1000  # Prevent infinite loop
    attempts = 0
    
    for student in students:
        if allocated_count >= num_to_allocate:
            break
            
        if student.id in allocated_students:
            continue
            
        # Find an available room matching student's gender
        available_rooms = [
            room for room in rooms 
            if room.gender == student.gender 
            and room_occupancy[room.id] < room.capacity
        ]
        
        if available_rooms:
            # Pick a random available room
            room = random.choice(available_rooms)
            
            # Create allocation
            allocation = Allocation(
                student_id=student.id,
                room_id=room.id,
                allocation_date=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                status='Active'
            )
            
            # Update student and room
            student.allocated_room = room.room_number
            room_occupancy[room.id] += 1
            room.occupied = room_occupancy[room.id]
            
            if room.occupied >= room.capacity:
                room.status = 'Full'
            
            allocations.append(allocation)
            allocated_students.add(student.id)
            allocated_count += 1
            
        attempts += 1
        if attempts > max_attempts:
            break
    
    # Update room status for rooms that are now full
    for room in rooms:
        if room.occupied >= room.capacity:
            room.status = 'Full'
        else:
            room.status = 'Available'
    
    return allocations, allocated_count

def seed_database():
    """Main function to populate the database"""
    print("🌱 Seeding database...")
    
    with app.app_context():
        # Clear existing data
        print("🗑️ Clearing existing data...")
        db.session.query(Allocation).delete()
        db.session.query(Student).delete()
        db.session.query(Room).delete()
        db.session.commit()
        
        # Create rooms (60 rooms)
        print("🏠 Creating rooms...")
        rooms = create_rooms()
        db.session.add_all(rooms)
        db.session.commit()
        print(f"✅ Created {len(rooms)} rooms")
        
        # Create students (50 students)
        print("👨‍🎓 Creating students...")
        students = create_students(50)
        db.session.add_all(students)
        db.session.commit()
        print(f"✅ Created {len(students)} students")
        
        # Randomly allocate rooms (approx 30 students)
        print("🔑 Allocating rooms...")
        allocations, allocated_count = allocate_rooms_randomly(students, rooms, 30)
        db.session.add_all(allocations)
        
        # Update room and student records
        for student in students:
            db.session.add(student)
        for room in rooms:
            db.session.add(room)
        
        db.session.commit()
        print(f"✅ Allocated {allocated_count} students to rooms")
        
        # Statistics
        total_students = len(students)
        allocated_students = sum(1 for s in students if s.allocated_room is not None)
        unallocated_students = total_students - allocated_students
        
        print("\n📊 Database Statistics:")
        print(f"   - Total Students: {total_students}")
        print(f"   - Allocated Students: {allocated_students}")
        print(f"   - Unallocated Students: {unallocated_students}")
        print(f"   - Total Rooms: {len(rooms)}")
        
        # Count rooms by status
        available_rooms = sum(1 for r in rooms if r.status == 'Available')
        full_rooms = sum(1 for r in rooms if r.status == 'Full')
        print(f"   - Available Rooms: {available_rooms}")
        print(f"   - Full Rooms: {full_rooms}")
        
        # Count by gender
        male_students = sum(1 for s in students if s.gender == 'Male')
        female_students = sum(1 for s in students if s.gender == 'Female')
        print(f"   - Male Students: {male_students}")
        print(f"   - Female Students: {female_students}")
        
        print("\n🎯 Seeding complete!")

if __name__ == '__main__':
    seed_database()