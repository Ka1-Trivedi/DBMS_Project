from flask import Flask, render_template, request ,redirect , url_for , session
import sqlite3
from flask_bcrypt import Bcrypt
from flask_login import LoginManager , UserMixin , login_user , login_required , logout_user , current_user


app = Flask(__name__)

# Initialize Flask Extensions
app.secret_key = "Om_Namah_Shivay!!!Radhe...Radhe!!"
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login.view = "login"


# database path
DB_PATH = "database/attendance.db"

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

    conn.commit()
    conn.close()

# call the function to create table
create_tables()

class User(UserMixin):
    def __init__(self,id,name ,email,password):
        self.id =id
        self.name = name
        self.email = email
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Teacher WHERE id = ?" , (user_id))
    user = cursor.fetchone()
    conn.close()

    if user :
        return User(id  = user[0], name  = user[1] , email = user[2], password=user[3])
    return None

@app.route('/')
def home():
    return "Welcome to Attendance System."

if __name__ == '__main__':
    app.run(debug=True)



