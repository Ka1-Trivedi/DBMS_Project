from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
from functools import wraps
import os  # Import os module to handle directory creation
import pandas as pd
from werkzeug.utils import secure_filename
import csv
from flask import Response
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import uuid
import random

app = Flask(__name__)

app.secret_key = os.urandom(24)  # Generates a random secret key

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# database path
DB_PATH = "attendance_system/database/attendance.db"

# Ensure the database directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# function to create table
def create_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # School
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS School (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   name TEXT NOT NULL
                )
    '''
    )

    # Department 
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Department (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    school_id INTEGER,
                    FOREIGN KEY (school_id) REFERENCES School(id)
                   )
    '''
    )

    # Class
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Class (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    department_id INTEGER,
                    FOREIGN KEY (department_id) REFERENCES Department(id)
                   )
    '''
    )

    # Teacher
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Teacher (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    user_id INTEGER,
                    subject TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                   )
    '''
    )

    # Student
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Student (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    roll_number TEXT UNIQUE NOT NULL,
                    class_id INTEGER,
                    user_id INTEGER,
                    FOREIGN KEY (class_id) REFERENCES Class(id)
                    FOREIGN KEY (user_id) REFERENCES users(id)
                   )
    '''
    )

    # Attendance
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    date DATE NOT NULL,
                    status TEXT CHECK(status IN ('Present', 'Absent')),
                    FOREIGN KEY (student_id) REFERENCES Student(id)
                   )
    '''
    )

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT CHECK(role IN ('admin', 'teacher', 'student')) NOT NULL DEFAULT 'student'
        )
    ''')

    conn.commit()
    conn.close()

# call the function to create table
create_tables()

class User(UserMixin):
    def __init__(self, id, email, role):
        self.id = id
        self.email = email
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, role FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        return User(id=user[0], email=user[1], role=user[2])
    return None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            return "Access Denied: Admins Only", 403
        return f(*args, **kwargs)
    return decorated_function

def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'teacher':
            return "Access Denied: Teachers Only", 403
        return f(*args, **kwargs)
    return decorated_function

def teacher_or_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') not in ['teacher', 'admin']:
            return "Access Denied: Teachers or Admins Only", 403
        return f(*args, **kwargs)
    return decorated_function


def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'student':
            return "Access Denied: Students Only", 403
        return f(*args, **kwargs)
    return decorated_function

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        role = request.form['role']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # check if email already exists
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        existing_user = cursor.fetchone()
        if existing_user:
            return "Email already registered. Try logging in."

        cursor.execute("INSERT INTO users (email, password, role) VALUES (?, ?, ?)", (email, password, role))
        user_id = cursor.lastrowid

        # Insert into Teacher or Student table based on role
        if role == 'teacher':
            cursor.execute("INSERT INTO Teacher (user_id, name,email,password) VALUES (?, ?, ?, ?)", (user_id, name,email,password))
        elif role == 'student':
            roll_number = request.form['roll_number']
            class_id = request.form['class_id']
            cursor.execute("INSERT INTO Student (user_id, name, roll_number, class_id,email,password) VALUES (?, ?, ?, ?, ?, ?)", (user_id, name, roll_number, class_id, email, password))
        
        conn.commit()
        conn.close()

        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, password, role FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        conn.close()
        
            # user[0]=id	user[1]=email	user[2]=password	user[3]=role
        # print(user[2])
        # print(password)
        if user and bcrypt.check_password_hash(user[2], password):
            # print("in")
            session['user_id'] = user[0]
            session['role'] = user[3]
            login_user(User(user[0], user[1], user[3]))
            if session['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif session['role'] == 'teacher':
                return redirect(url_for('teacher_dashboard',teacher_id = user[0]))
            elif session['role'] == 'student':
                return redirect(url_for('student_dashboard',student_id = user[0]))
        else:
            return "Invalid credentials. Please try again."
    
    return render_template('login.html')


# ------------------------------------------------dashboard------------------------------------------------------------
@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/teacher_dashboard/<int:teacher_id>')
@teacher_required
def teacher_dashboard(teacher_id):
    return render_template('teacher_dashboard.html', teacher_id=teacher_id)

@app.route('/student_dashboard/<int:student_id>')
@student_required
def student_dashboard(student_id):
    return render_template('student_dashboard.html', student_id = student_id)

# ---------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------school oprations---------------------------------------------------
@app.route('/add_school', methods = ['GET','POST'])
@admin_required
def add_school():
    print("in add_school app.py")
    if request.method == 'POST':
        name = request.form['add_school']
        print("in method")
        print(name)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO School (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()

        return redirect(url_for('manage_schools'))  # Redirect to the school list page

    return render_template('add_school.html')  # Render a form for adding schools

@app.route('/manage_schools')
@admin_required
def manage_schools():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM School")
    schools = cursor.fetchall()
    conn.close()

    return render_template('manage_schools.html', schools=schools)

@app.route('/edit_school/<int:school_id>', methods = ['GET','POST'])
@admin_required
def edit_school(school_id):
    conn =sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method=='POST':
        new_name = request.form['name']
        cursor.execute("UPDATE School SET name = ? WHERE id = ?",(new_name,school_id))
        conn.commit()
        conn.close()
        return redirect(url_for('manage_schools')) 
    
    cursor.execute("SELECT * FROM School WHERE id = ?", (school_id,))
    school = cursor.fetchone()
    conn.close()

    return render_template('edit_school.html',school=school)

@app.route('/delete_school/<int:school_id>',methods =['GET','POST'])
@admin_required
def delete_school(school_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM School WHERE id = ?", (school_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('manage_schools'))
# --------------------------------------------------------------------------------------------------------------------

# -------------------------------------------------department---------------------------------------------------------
@app.route('/add_department',methods = ['GET','POST'])
@admin_required
def add_department():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        school_id = request.form['school_id']
        cursor.execute("INSERT INTO Department (name,school_id) VALUES (?,?)",(name,school_id))
        conn.commit()
        conn.close()
        return redirect(url_for('manage_departments'))
    
    cursor.execute("SELECT * FROM School")
    schools = cursor.fetchall()
    conn.close()

    return render_template('add_department.html',schools=schools)

@app.route('/manage_departments')
@admin_required
def manage_departments():
    conn =sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT Department.id, Department.name, School.name FROM Department JOIN School ON Department.school_id = School.id'''
    )
    departments = cursor.fetchall()
    conn.close()

    return render_template('manage_departments.html',departments = departments)

@app.route('/edit_department/<int:department_id>',methods =['GET','POST'])
@admin_required
def edit_department(department_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == 'POST':
        new_name = request.form['new_name']
        new_school_id  = request.form['new_school_id']
        cursor.execute(
            "UPDATE Department SET name = ?, school_id = ? WHERE id = ?", (new_name, new_school_id, department_id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('manage_departments'))
    
    cursor.execute("SELECT * FROM Department WHERE id = ?", (department_id,))
    department = cursor.fetchone()

    cursor.execute("SELECT * FROM School")
    schools = cursor.fetchall()

    conn.close()

    return render_template('edit_department.html',department= department , schools = schools)

@app.route('/delete_department/<int:department_id>')
@admin_required
def delete_department(department_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Department WHERE id = ?", (department_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('manage_departments'))
# --------------------------------------------------------------------------------------------------------------------
# -----------------------------------------------------class----------------------------------------------------------
@app.route('/add_class', methods = ['GET','POST'])
@admin_required
def add_class():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        department_id = request.form['department_id']
        cursor.execute("INSERT INTO Class (name,department_id) VALUES (?,?)" , (name,department_id))
        conn.commit()
        conn.close()
        return redirect(url_for('manage_classes'))
    
    cursor.execute("SELECT * FROM Department")
    departments = cursor.fetchall()
    conn.close()

    return render_template('add_class.html',departments = departments)

@app.route('/manage_classes')
@admin_required
def manage_classes():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT Class.id , Class.name , Department.name from Class JOIN Department ON Class.department_id = Department.id
''')
    classes = cursor.fetchall()
    conn.close()
    
    return render_template('manage_classes.html',classes = classes)

@app.route('/edit_class/<int:class_id>', methods=['GET', 'POST'])
@admin_required
def edit_class(class_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == 'POST':
        new_name = request.form['name']
        new_department_id = request.form['department_id']
        cursor.execute("UPDATE Class SET name = ?, department_id = ? WHERE id = ?", (new_name, new_department_id, class_id))
        conn.commit()
        conn.close()

        return redirect(url_for('manage_classes'))
    
    cursor.execute("SELECT * FROM Class WHERE id = ?",(class_id,))
    class_ = cursor.fetchone()

    cursor.execute("SELECT * FROM Department")
    departments = cursor.fetchall()

    conn.close()

    return render_template('edit_class.html',class_ = class_ , departments = departments)

@app.route('/delete_class/<int:class_id>', methods=['GET', 'POST'])
@admin_required
def delete_class(class_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Class WHERE id = ?", (class_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('manage_classes'))  
# --------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------student---------------------------------------------------------
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def add_students_from_excel(filepath):
    df = pd.read_excel(filepath)  # Read Excel file

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for _, row in df.iterrows():
        name = row['Name']
        email = row['Email']
        password = bcrypt.generate_password_hash(str(row['Password'])).decode('utf-8')  # Hash password
        roll_number = row['Roll Number']  # New field
        class_name = row['Class Name']
        department_name = row['Department Name']
        # class_id = row['Class ID']

        # Find class_id from Class table by Class Name
        cursor.execute("SELECT id FROM Department WHERE name = ?", (department_name,))
        department_id = cursor.fetchone()[0]
        # print(department_id)
        # print(class_name)
        cursor.execute("SELECT id FROM Class WHERE name = ? and department_id = ?", (class_name, department_id))
        class_id = cursor.fetchone()[0]
        print(class_id)

        # Insert into users table
        cursor.execute("INSERT INTO users (email, password, role) VALUES (?, ?, 'student')", 
                       (email, password))
        user_id = cursor.lastrowid  # Get newly created user ID

        # Insert into Student table
        cursor.execute("INSERT INTO Student (user_id, name, roll_number, class_id, email, password) VALUES (?, ?, ?, ?, ?, ?)", 
                       (user_id, name, roll_number, class_id, email, password))

    conn.commit()
    conn.close()


# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload_students', methods=['GET', 'POST'])
@teacher_or_admin_required
def upload_students():
    if request.method == 'POST':
        if 'file' not in request.files:
            return "No file part", 400
        
        file = request.files['file']
        
        if file.filename == '':
            return "No selected file", 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Process the Excel file
            add_students_from_excel(filepath)
            
            return redirect(url_for('manage_students'))
    
    return render_template('upload_students.html')

@app.route('/manage_students')
@teacher_or_admin_required
def manage_students():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM School")
    schools = cursor.fetchall()

    cursor.execute("SELECT * FROM Department")
    departments = cursor.fetchall()

    cursor.execute("SELECT  * FROM Class")
    classes = cursor.fetchall()

    # Build the query for filtering students
    query = "SELECT Student.id, Student.name, Student.email, Class.name FROM Student JOIN Class ON Student.class_id = Class.id JOIN Department ON Class.department_id = Department.id"
    filters = []
    params = []

    school_id = request.args.get('school_id')
    if school_id:
        filters.append("Department.school_id = ?")
        params.append(school_id)

    department_id = request.args.get('department_id')
    if department_id:
        filters.append("Class.department_id = ?")
        params.append(department_id)

    class_id = request.args.get('class_id')
    if class_id:
        filters.append("Student.class_id = ?")
        params.append(class_id)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    cursor.execute(query, params)
    students = cursor.fetchall()
    conn.close()

    return render_template('manage_students.html', students=students, schools=schools, departments=departments, classes=classes)


    # cursor.execute('''
    #     SELECT Student.id, Student.name, users.email, Class.name FROM Student
    #     JOIN users ON Student.id = users.id
    #     JOIN Class ON Student.class_id = Class.id
    #     WHERE users.role = 'student'
    # ''')
    # students = cursor.fetchall()
    # conn.close()
    # return render_template('manage_students.html',students = students )

@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
@teacher_or_admin_required
def edit_student(student_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == 'POST':
        new_name = request.form['name']
        new_email = request.form['email']
        new_class_id = request.form['class_id']
        cursor.execute("UPDATE Student SET name = ?, class_id = ? WHERE id = ?", (new_name, new_class_id, student_id))
        cursor.execute("UPDATE users SET email = ? WHERE id = ?", (new_email, student_id))
        cursor.execute("UPDATE users SET name = ?, email = ?, clss_id = ? WHERE id = ?", (new_name, new_email, new_class_id, student_id))
        conn.commit()
        conn.close()

        return redirect(url_for('manage_students'))
    cursor.execute("SELECT * FROM users WHERE id = ?", (student_id,))
    student = cursor.fetchone()

    cursor.execute("SELECT * FROM Class")
    classes = cursor.fetchall()

    conn.close()

    return render_template('edit_student.html', student=student, classes=classes)

@app.route('/delete_student/<int:student_id>', methods=['GET', 'POST'])
@admin_required
def delete_student(student_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM student WHERE user_id = ?", (student_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('manage_students'))
# --------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------teacher---------------------------------------------------------
@app.route('/add_teacher', methods=['GET', 'POST'])
@admin_required
def add_teacher():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        subject = request.form['subject']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Insert into users table
        cursor.execute("INSERT INTO users (email, password, role) VALUES (?, ?, 'teacher')", (email, password))
        user_id = cursor.lastrowid  # Get newly created user ID

        # Insert into Teacher table
        cursor.execute("INSERT INTO Teacher (user_id, name, email, subject, password) VALUES (?, ?, ?, ?, ?)", (user_id, name, email, subject, password))

        conn.commit()
        conn.close()

        return redirect(url_for('manage_teachers'))

    return render_template('add_teacher.html')

@app.route('/manage_teachers')
@admin_required
def manage_teachers():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT users.id, Teacher.name, users.email FROM users
        JOIN Teacher ON users.id = Teacher.user_id
        WHERE users.role = 'teacher'
    ''')
    teachers = cursor.fetchall()
    conn.close()

    return render_template('manage_teachers.html', teachers=teachers)

@app.route('/edit_teacher/<int:teacher_id>', methods=['GET', 'POST'])
@admin_required
def edit_teacher(teacher_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == 'POST':
        new_name = request.form['name']
        new_email = request.form['email']
        new_subject = request.form['subject']
        cursor.execute("UPDATE users SET email = ? WHERE id = ?", (new_email, teacher_id))
        cursor.execute("UPDATE Teacher SET name = ? WHERE user_id = ?", (new_name, teacher_id))
        conn.commit()
        conn.close()

        return redirect(url_for('manage_teachers'))

    cursor.execute("SELECT users.id, Teacher.name, users.email , Teacher.subject FROM users JOIN Teacher ON users.id = Teacher.user_id WHERE users.id = ?", (teacher_id,))
    teacher = cursor.fetchone()
    conn.close()

    return render_template('edit_teacher.html', teacher=teacher)

@app.route('/delete_teacher/<int:teacher_id>', methods=['GET', 'POST'])
@admin_required
def delete_teacher(teacher_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Teacher WHERE user_id = ?", (teacher_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (teacher_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('manage_teachers'))
# --------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------attendance------------------------------------------------------
@app.route('/mark_attendance', methods=['GET', 'POST'])
@teacher_required
def mark_attendance():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    teacher_id = session['user_id']

    if request.method == 'POST':
        class_id = request.form['class_id']
        date = request.form['date']

        # Get the list of student IDs in the selected class
        cursor.execute("SELECT id FROM Student WHERE class_id = ?", (class_id,))
        student_ids = [row[0] for row in cursor.fetchall()]

        # Iterate over all student IDs and check if they are present or absent
        for student_id in student_ids:
            status = 'Present' if str(student_id) in request.form else 'Absent'
            cursor.execute("INSERT INTO Attendance (student_id, date, status) VALUES (?, ?, ?)", 
                           (student_id, date, status))
        
        conn.commit()
        conn.close()
        return redirect(url_for('teacher_dashboard', teacher_id = teacher_id))
    
    cursor.execute('''SELECT Class.id, Class.name 
    FROM Class 
    JOIN TeacherClassSubject ON Class.id = TeacherClassSubject.class_id 
    WHERE TeacherClassSubject.teacher_id = ?
    ''', (teacher_id,))
    print(teacher_id)
    classes = cursor.fetchall()
    print(classes)

    selected_class_id = request.args.get('class_id')
    selected_date = request.args.get('date')
    students = []
    if selected_class_id:
        cursor.execute("SELECT id, name, roll_number FROM Student WHERE class_id = ?", (selected_class_id,))
        students = cursor.fetchall()

    conn.close()

    return render_template('mark_attendance.html', classes=classes, students=students, selected_class_id=selected_class_id, selected_date=selected_date,teacher_id = teacher_id)

@app.route('/view_attendance', methods=['GET', 'POST'])
@login_required
def view_attendance():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    teacher_id = session['user_id']

    if current_user.role == 'teacher':
        if request.method == 'POST':
            class_id = request.form['class_id']
            date = request.form['date']
            cursor.execute('''
            SELECT Student.roll_number, Student.name, Attendance.status 
            FROM Attendance 
            JOIN Student ON Attendance.student_id = Student.id 
            WHERE Student.class_id = ? AND Attendance.date = ?''', (class_id, date))

            attendance_records = cursor.fetchall()
        else:
            attendance_records = []

        cursor.execute('''
        SELECT Class.id, Class.name 
        FROM Class 
        JOIN TeacherClassSubject ON Class.id = TeacherClassSubject.class_id 
        WHERE TeacherClassSubject.teacher_id = ?
        ''', (teacher_id,))
        print(teacher_id)
        classes = cursor.fetchall()
        print(classes)

        conn.close()
        return render_template('view_attendance_teacher.html', attendance_records=attendance_records, classes=classes,teacher_id = teacher_id)
    elif current_user.role == 'student':
        cursor.execute('''SELECT Teacher.subject, Attendance.date, Attendance.status FROM Attendance 
        JOIN Student ON Attendance.student_id = Student.id 
        JOIN TeacherClassSubject ON Student.class_id = TeacherClassSubject.class_id 
        JOIN Teacher ON TeacherClassSubject.teacher_id = Teacher.user_id WHERE Attendance.student_id = ?''', (current_user.id,))
        attendance_records = cursor.fetchall()

        conn.close()
        return render_template('view_attendance_student.html', attendance_records=attendance_records)
    
    return "Access Denied!!", 403

@app.route('/download_attendance', methods=['POST'])
@teacher_required
def download_attendance():
    class_id = request.form['class_id']
    start_date = request.form['start_date']
    end_date = request.form['end_date']

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    teacher_id = session['user_id']

    cursor.execute('''
    SELECT Student.roll_number, Student.name, Attendance.date, Attendance.status 
    FROM Attendance 
    JOIN Student ON Student.id = Attendance.student_id 
    JOIN TeacherClassSubject ON Student.class_id = TeacherClassSubject.class_id 
    WHERE TeacherClassSubject.teacher_id = ? AND Student.class_id = ? AND Attendance.date BETWEEN ? AND ? 
    ORDER BY Attendance.date''', (teacher_id,class_id, start_date, end_date))
    attendance_records = cursor.fetchall()
    conn.close()

    # Create csv file 
    output = []
    output.append(['Roll Number', 'Student Name', 'Date', 'Status'])

    for record in attendance_records:
        output.append([record[0], record[1], record[2], record[3]])

    response = Response('\n'.join([','.join(map(str, row)) for row in output]), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=attendance_report.csv"
    return response
# --------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------attendance_Analysis-----------------------------------------------
@app.route('/attendance_summary/<int:class_id>')
# @teacher_or_admin_required
def attendance_summary(class_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''SELECT Student.name, SUM(CASE WHEN Attendance.status = 'Present' THEN 1 ELSE 0 END) AS present_days, COUNT(Attendance.id) AS total_days FROM Attendance JOIN Student ON Attendance.student_id = Student.id WHERE Student.class_id = ? GROUP BY Student.id''', (class_id,))

    data = cursor.fetchall()
    conn.close()

    result = []
    for row in data:
        name, present_days, total_days = row
        attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
        result.append({'name': name, 'attendance_percentage': round(attendance_percentage, 2)})

    return jsonify(result)

# --------------------------------------------------------------------------------------------------------------------
@app.route('/assign_teacher', methods=['GET', 'POST'])
@admin_required
def assign_teacher():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == 'POST':
        teacher_id = request.form['teacher_id']
        class_id = request.form['class_id']
        cursor.execute("INSERT INTO TeacherClassSubject (teacher_id, class_id) VALUES (?, ?)", 
                       (teacher_id, class_id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_dashboard'))

    cursor.execute("SELECT user_id, name FROM Teacher")
    teachers = cursor.fetchall()

    cursor.execute("SELECT id, name FROM Class")
    classes = cursor.fetchall()

    conn.close()

    return render_template('assign_teacher_to_class.html', teachers=teachers, classes=classes)

test_id = None
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------IA taking---------------------------------------------------------------
@app.route("/Create_IA/<int:teacher_id>", methods=["GET", "POST"])
@teacher_required
def Create_IA(teacher_id):
    global test_id
    questions = []
    selected_questions = []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("Select Subject FROM Teacher WHERE user_id = ? ", (teacher_id,))
    subjects = cursor.fetchall()

    cursor.execute('''
        SELECT Class.id, Class.name 
        FROM Class 
        JOIN TeacherClassSubject ON Class.id = TeacherClassSubject.class_id 
        WHERE TeacherClassSubject.teacher_id = ?
        ''',(teacher_id,))
    classes = cursor.fetchall()

    subject = request.form.get("subject")
    class_id = request.form.get("class_id")
    difficulty = request.form.get("difficulty")
    test_name = request.form.get("test_name")
    ia_date = request.form.get("ia_date")
    if request.method == "POST":
        if test_id is None:
            test_id = str(uuid.uuid4())
            cursor.execute("INSERT INTO tests (test_id, subject, test_name, teacher_id,class_id, ia_date) VALUES (?, ?, ?, ?, ?, ?)",
                           (test_id, subject, test_name, teacher_id , class_id,ia_date))
            print("test_id")
            conn.commit()

    if request.method == "POST":
        if "fetch_questions" in request.form:
            print(difficulty,subject)
            cursor.execute(
                "SELECT qid, question FROM Question_Database WHERE difficulty = ? AND subject = ?",
                (difficulty, subject))
            questions = cursor.fetchall()
            print(questions)
            

        elif "save_questions" in request.form:
            selected_questions = request.form.getlist("selected_questions")
            for qid in selected_questions:
                cursor.execute("SELECT ans FROM Question_Database WHERE qid = ?", (qid,))
                answer = cursor.fetchone()
                cursor.execute("INSERT INTO Test_Questions (test_id, qid, answer) VALUES (?, ?, ?)", (test_id, qid, answer[0]))
            conn.commit()
            conn.close()

        elif "link" in request.form:
            return f"IA has been created Successfully!!!👍👍<a href='{url_for('teacher_dashboard', teacher_id=session['user_id'])}'>Teacher Dashboard</a>"

    return render_template("Create_IA.html", questions=questions, subjects=subjects, difficulty=difficulty, test_name=test_name, test_id=test_id, classes=classes,ia_date = ia_date,teacher_id = teacher_id)

@app.route("/available_IA/<int:student_id>", methods=["GET", "POST"])
@student_required
def available_IA(student_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Fetch student details
    cursor.execute("SELECT name, roll_number FROM Student WHERE user_id = ?", (student_id,))
    student_detail = cursor.fetchone()
    # student_detail[0] = name, student_detail[1] = roll_number

    # Fetch available IA tests for the student
    cursor.execute('''
        SELECT Tests.test_id, Tests.test_name, Tests.subject 
        FROM Tests 
        JOIN Student ON Student.class_id = Tests.class_id 
        WHERE Student.user_id = ? AND Tests.ia_date = date('now')
    ''', (student_id,))
    test_details = cursor.fetchall()
    # test_details contains tuples: (test_id, test_name, subject)

    conn.close()

    return render_template("available_IA.html", 
                           name=student_detail[0], 
                           roll=student_detail[1], 
                           test_details=test_details)

s = {}
@app.route("/give_IA/<test_id>/<roll>", methods=["GET", "POST"])
@student_required
def give_IA(test_id, roll):
    global s
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT roll , test_id FROM Test_Response")
    given = cursor.fetchall()
    markes = cursor.execute("SELECT markes FROM Student_Result WHERE roll = ? and test_id = ?", (roll, test_id)).fetchone()
    for record in given:
        if roll == record[0] and test_id == record[1] or markes is not None:
            return f"You have already submitted your IA or IA has reached its deadline!!!<a href ='{url_for('student_dashboard', student_id=session['user_id'])}'>Student_Dashboard</a>"

    questions = []

    if test_id not in s.keys():
        test_questions = cursor.execute("SELECT qid FROM Test_Questions WHERE test_id = ?", (test_id,)).fetchall()
        for qid_tuple in test_questions:
            qid = qid_tuple[0]  # Extract the qid value from the tuple
            question = cursor.execute(
                "SELECT qid, question, option_A, option_B, option_C, option_D FROM Question_Database WHERE qid = ?",
                (qid,)
            ).fetchone()
            if question:
                questions.append(dict(zip(["qid", "question", "option_A", "option_B", "option_C", "option_D"], question)))
        random.shuffle(questions)
        s[test_id] = questions
    else:
        questions = s[test_id]

    if request.method == "POST":
        if "submit" in request.form:
            for question in questions:
                answer = request.form.get(f"answer_{question['qid']}")
                cursor.execute(
                    "INSERT INTO Test_Response (roll, qid, answer, test_id) VALUES (?, ?, ?, ?)",
                    (roll, question['qid'], answer, test_id)
                )
            conn.commit()
            conn.close()
            del s[test_id]
            return f"Test submitted successfully!🤦‍♂️🥳<a href ='{url_for('student_dashboard', student_id=session['user_id'])}'>Student_Dashboard</a>"

    return render_template("give_IA.html", questions=questions, test_id=test_id, roll=roll, auto_submit_url=url_for('auto_submit_IA', test_id=test_id, roll=roll))

@app.route("/auto_submit_IA/<test_id>/<roll>", methods=["POST"])
@student_required
def auto_submit_IA(test_id, roll):
    global s
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if test_id in s:
        questions = s[test_id]
        for question in questions:
            answer = request.form.get(f"answer_{question['qid']}", None)  # Default to None if no answer
            cursor.execute(
                "INSERT INTO Test_Response (roll, qid, answer, test_id) VALUES (?, ?, ?, ?)",
                (roll, question['qid'], answer, test_id)
            )
        conn.commit()
        conn.close()
        del s[test_id]
        return "Test auto-submitted due to screen focus loss! <a href='{url_for('student_dashboard', student_id=session['user_id'])}'>Student Dashboard</a>"

    return "Error: Test not found or already submitted."

@app.route("/list_IA/<int:teacher_id>", methods = ['GET','POST'])
@teacher_required
def list_IA(teacher_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT test_name, class_id, ia_date ,test_id FROM Tests WHERE teacher_id = ?" , (teacher_id, ))
    ia_list = cursor.fetchall()
    conn.close()

    return render_template("list_IA.html",test_id = test_id , teacher_id = teacher_id , ia_list = ia_list)

@app.route("/download_IA_Result/<test_id>" , methods = ['GET','POST'])
@teacher_required
def download_IA_Result(test_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT Student_result.roll , Class.name , Student_result.markes , Student_result.total_markes FROM Student_result Join Class on Student_result.class_id = Class.id WHERE test_id = ? ",(test_id, ))
    IA_Result = cursor.fetchall()

    output = []
    output.append(['Roll Number', 'Class Name', 'Obtained Marks', 'Total Marks'])

    for record in IA_Result:
        output.append([record[0], record[1], record[2], record[3]])

    response = Response('\n'.join([','.join(map(str, row)) for row in output]), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=IA_Result.csv"
    return response

@app.route("/close_IA/<test_id>", methods=['GET', 'POST'])
@teacher_required
def close_IA(test_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Fetch class_id as a single value
    cursor.execute("SELECT class_id FROM Tests WHERE test_id = ?", (test_id,))
    class_id_tuple = cursor.fetchall()
    if class_id_tuple is None:
        conn.close()
        return "Error: Test not found", 404
    for class_id in class_id_tuple: # Extract the value from the tuple

        # Fetch roll numbers of students in the class
        cursor.execute("SELECT roll_number FROM Student WHERE class_id = ?", (class_id[0],))
        rolls = cursor.fetchall()

        # Fetch roll numbers of students who have given the IA
        cursor.execute("SELECT roll FROM Test_Response WHERE test_id = ?", (test_id,))
        ia_given_rolls = cursor.fetchall()

        for roll_tuple in rolls:
            roll = roll_tuple[0]  # Extract the roll number from the tuple
            markes = 0
            total_markes = cursor.execute("SELECT count(qid) FROM Test_Questions WHERE test_id = ?", (test_id,)).fetchone()[0]
            if roll in [r[0] for r in ia_given_rolls]:  # Compare roll numbers
                qids = cursor.execute("SELECT qid FROM Test_Questions WHERE test_id = ?", (test_id,)).fetchall()
                for qid_tuple in qids:
                    qid = qid_tuple[0]  # Extract the qid value
                    answer = cursor.execute(
                        "SELECT answer FROM Test_Questions WHERE test_id = ? AND qid = ?", (test_id, qid)
                    ).fetchone()
                    response_ans = cursor.execute(
                        "SELECT answer FROM Test_Response WHERE roll = ? AND qid = ? AND test_id = ?", (roll, qid, test_id)
                    ).fetchone()
                    if response_ans == answer:
                        markes += 1
            cursor.execute(
                "INSERT INTO Student_Result (roll, class_id, test_id, markes, total_markes) VALUES (?, ?, ?, ?, ?)",
                (roll, class_id[0], test_id, markes, total_markes,)
            )
            conn.commit()

    cursor.execute("DELETE FROM Test_Response WHERE test_id = ?",(test_id,))
    cursor.execute("DELETE FROM Test_Questions WHERE test_id = ?",(test_id,))
    conn.commit()
    conn.close()
    return f"Test Closed. Result Generated successfully! 🤦‍♂️🥳 <a href='{url_for('teacher_dashboard', teacher_id=session['user_id'])}'>Teacher Dashboard</a>"


@app.route('/logout')
@login_required
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
def home():
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
