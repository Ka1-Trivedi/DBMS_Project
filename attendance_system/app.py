from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from functools import wraps
import os  # Import os module to handle directory creation
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)

app.secret_key = os.urandom(24)  # Generates a random secret key

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# database path
DB_PATH = "database/attendance.db"

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
                    password TEXT NOT NULL 
                   )
    '''
    )

    # Student
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Student (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    roll_number TEXT UNIQUE NOT NULL,
                    class_id INTEGER,
                    FOREIGN KEY (class_id) REFERENCES Class(id)
                   )
    '''
    )

    # Attendance
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    date TEXT NOT NULL,
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
            cursor.execute("INSERT INTO Teacher (user_id, name) VALUES (?, ?)", (user_id, name))
        elif role == 'student':
            roll_number = request.form['roll_number']
            class_id = request.form['class_id']
            cursor.execute("INSERT INTO Student (id, name, roll_number, class_id) VALUES (?, ?, ?, ?)", (user_id, name, roll_number, class_id))
        
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
        if user and user[2]==password:
            # print("in")
            session['user_id'] = user[0]
            session['role'] = user[3]
            login_user(User(user[0], user[1], user[3]))
            if session['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif session['role'] == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            elif session['role'] == 'student':
                return redirect(url_for('student_dashboard'))
        else:
            return "Invalid credentials. Please try again."
    
    return render_template('login.html')


# ------------------------------------------------dashboard------------------------------------------------------------
@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    return f"Admin!\nWelcome, {current_user.email}! Your role is {current_user.role}.<a href='/logout'>Logout</a>"

@app.route('/teacher_dashboard')
@teacher_required
def teacher_dashboard():
    return f"Teacher!\nWelcome, {current_user.email}! Your role is {current_user.role}.<a href='/logout'>Logout</a>"

@app.route('/student_dashboard')
@student_required
def student_dashboard():
    return f"Student!\nWelcome, {current_user.email}! Your role is {current_user.role}.<a href='/logout'>Logout</a>"

# ---------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------school oprations---------------------------------------------------
@app.route('/add_school', methods=['GET', 'POST'])
@admin_required
def add_school():
    if request.method == 'POST':
        name = request.form['name']
        
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
    cursor = conn.cursor
    cursor.execute("SELECT * FROM School")
    schools = cursor.fetchall()
    conn.close()

    return render_template('manage_schools',schools = schools)

@app.route('/edit_school/<int:school_id>', methods = ['GET','POST'])
@admin_required
def edit_school(school_id):
    conn =sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method=='POST':
        new_name = request.form['name']
        cursor.execute("UPDATE School SET name = ? WHERE id = ?",(new_name,school_id))
        conn.commmit()
        conn.close()
        return redirect(url_for('manage_schools')) 
    
    cursor.execute("SELECT * FROM School WHERE id = ? ",(school_id,))
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
@app.route('add_department',methods = ['GET','POST'])
@admin_required
def add_department():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form('name')
        school_id
# --------------------------------------------------------------------------------------------------------------------
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
    app.run(debug=True)
