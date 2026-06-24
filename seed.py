# seed.py - PostgreSQL Compatible Version
from app import app, db, Student, Room, Allocation
from datetime import datetime, timedelta
import random
import os

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

def reset_database():
    """Reset PostgreSQL database - drop and recreate tables"""
    with app.app_context():
        try:
            # Drop all tables
            db.drop_all()
            # Create all tables
            db.create_all()
            print("✅ Database reset successfully")
        except Exception as e:
            print(f"❌ Error resetting database: {e}")
            raise

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
        email = email.replace(" ", "").replace("'", "")
        counter = 1
        while email in used_emails:
            email = f"{first_name.lower()}.{last_name.lower()}{counter}@{random.choice(['university.edu', 'college.edu', 'student.edu'])}"
            email = email.replace(" ", "").replace("'", "")
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
    
    # Create a list of students that can be allocated
    available_students = [s for s in students if s.id not in allocated_students]
    
    for student in available_students:
        if allocated_count >= num_to_allocate:
            break
            
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
    print("🌱 Seeding PostgreSQL database...")
    print("=" * 50)
    
    with app.app_context():
        try:
            # Reset database
            print("🔄 Resetting database...")
            reset_database()
            
            # Create rooms
            print("🏠 Creating rooms...")
            rooms = create_rooms()
            db.session.add_all(rooms)
            db.session.commit()
            print(f"✅ Created {len(rooms)} rooms")
            
            # Create students
            print("👨‍🎓 Creating students...")
            students = create_students(50)
            db.session.add_all(students)
            db.session.commit()
            print(f"✅ Created {len(students)} students")
            
            # Randomly allocate rooms
            print("🔑 Allocating rooms...")
            allocations, allocated_count = allocate_rooms_randomly(students, rooms, 30)
            
            if allocations:
                db.session.add_all(allocations)
            
            # Update students and rooms
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
            
            print("\n" + "=" * 50)
            print("📊 Database Statistics:")
            print("=" * 50)
            print(f"   👥 Total Students: {total_students}")
            print(f"   🏠 Allocated Students: {allocated_students}")
            print(f"   🚫 Unallocated Students: {unallocated_students}")
            print(f"   🏢 Total Rooms: {len(rooms)}")
            
            available_rooms = sum(1 for r in rooms if r.status == 'Available')
            full_rooms = sum(1 for r in rooms if r.status == 'Full')
            print(f"   🟢 Available Rooms: {available_rooms}")
            print(f"   🔴 Full Rooms: {full_rooms}")
            
            male_students = sum(1 for s in students if s.gender == 'Male')
            female_students = sum(1 for s in students if s.gender == 'Female')
            print(f"   👨 Male Students: {male_students}")
            print(f"   👩 Female Students: {female_students}")
            
            # Room type distribution
            ac_rooms = sum(1 for r in rooms if r.room_type == 'AC')
            non_ac_rooms = sum(1 for r in rooms if r.room_type == 'Non-AC')
            print(f"   ❄️ AC Rooms: {ac_rooms}")
            print(f"   🌡️ Non-AC Rooms: {non_ac_rooms}")
            
            # Capacity distribution
            total_capacity = sum(r.capacity for r in rooms)
            total_occupied = sum(r.occupied for r in rooms)
            occupancy_rate = round((total_occupied / total_capacity * 100), 1) if total_capacity > 0 else 0
            print(f"   📈 Occupancy Rate: {occupancy_rate}%")
            
            print("=" * 50)
            print("\n🎯 Seeding complete!")
            print("🚀 You can now run: python app.py")
            
        except Exception as e:
            print(f"\n❌ Error seeding database: {str(e)}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    seed_database()