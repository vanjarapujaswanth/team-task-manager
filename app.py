from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime

app = Flask(__name__)

# Secret Key
app.config['SECRET_KEY'] = 'mysecretkey'

# Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# =========================
# DATABASE MODELS
# =========================

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)

# Project Model
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)

    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

# Task Model
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)

    status = db.Column(db.String(50), default='Pending')

    due_date = db.Column(db.DateTime)

    # Foreign Keys
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))

# =========================
# ROUTES
# =========================

# Home
@app.route('/')
def home():
    return render_template('index.html')

# Signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            return "Email already registered!"

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        new_user = User(
            name=name,
            email=email,
            password=hashed_password,
            role=role
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect('/login')

    return render_template('signup.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):

            session['user_id'] = user.id
            session['user_name'] = user.name
            session['role'] = user.role

            return redirect('/dashboard')

        return "Invalid Email or Password!"

    return render_template('login.html')

# Dashboard
@app.route('/dashboard')
def dashboard():

    if 'user_id' not in session:
        return redirect('/login')

    return render_template(
        'dashboard.html',
        name=session['user_name'],
        role=session['role']
    )

# =========================
# PROJECT MANAGEMENT
# =========================

@app.route('/projects', methods=['GET', 'POST'])
def projects():

    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':

        if session['role'] != 'Admin':
            return "Access Denied!"

        title = request.form['title']
        description = request.form['description']

        new_project = Project(
            title=title,
            description=description,
            created_by=session['user_id']
        )

        db.session.add(new_project)
        db.session.commit()

        return redirect('/projects')

    all_projects = Project.query.all()

    return render_template(
        'projects.html',
        projects=all_projects,
        role=session['role']
    )

# =========================
# TASK MANAGEMENT
# =========================

@app.route('/tasks', methods=['GET', 'POST'])
def tasks():

    if 'user_id' not in session:
        return redirect('/login')

    # Admin Creates Tasks
    if request.method == 'POST':

        if session['role'] != 'Admin':
            return "Access Denied!"

        title = request.form['title']
        description = request.form['description']
        status = request.form['status']
        due_date = request.form['due_date']
        assigned_to = request.form['assigned_to']
        project_id = request.form['project_id']

        new_task = Task(
            title=title,
            description=description,
            status=status,
            due_date=datetime.strptime(due_date, '%Y-%m-%d'),
            assigned_to=assigned_to,
            project_id=project_id
        )

        db.session.add(new_task)
        db.session.commit()

        return redirect('/tasks')

    # Fetch Data
    all_tasks = Task.query.all()
    all_users = User.query.all()
    all_projects = Project.query.all()

    return render_template(
        'tasks.html',
        tasks=all_tasks,
        users=all_users,
        projects=all_projects,
        role=session['role']
    )

# Logout
@app.route('/logout')
def logout():

    session.clear()

    return redirect('/login')

# Create Database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)