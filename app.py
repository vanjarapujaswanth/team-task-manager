from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)

# =========================
# CONFIGURATION
# =========================

app.config['SECRET_KEY'] = 'secret123'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# =========================
# DATABASE MODELS
# =========================

# USER MODEL
class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    email = db.Column(db.String(120), unique=True, nullable=False)

    password = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(20), nullable=False)


# PROJECT MODEL
class Project(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), nullable=False)

    description = db.Column(db.Text, nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# TASK MODEL
class Task(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), nullable=False)

    description = db.Column(db.Text, nullable=False)

    assigned_name = db.Column(
        db.String(100),
        nullable=False
    )

    status = db.Column(
        db.String(50),
        nullable=False
    )

    due_date = db.Column(
        db.DateTime,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    project_id = db.Column(
        db.Integer,
        db.ForeignKey('project.id')
    )

    # Relationship
    project = db.relationship(
        'Project',
        backref='tasks'
    )


# =========================
# HOME PAGE
# =========================

@app.route('/')
def home():

    return render_template('index.html')


# =========================
# SIGNUP
# =========================

@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        existing_user = User.query.filter_by(
            email=request.form['email']
        ).first()

        if existing_user:
            return "Email already exists!"

        hashed_password = generate_password_hash(
            request.form['password']
        )

        new_user = User(

            name=request.form['name'],

            email=request.form['email'],

            password=hashed_password,

            role=request.form['role']

        )

        db.session.add(new_user)

        db.session.commit()

        return redirect('/login')

    return render_template('signup.html')


# =========================
# LOGIN
# =========================

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        user = User.query.filter_by(
            email=request.form['email']
        ).first()

        if user and check_password_hash(
            user.password,
            request.form['password']
        ):

            session['user_id'] = user.id

            session['user_name'] = user.name

            session['role'] = user.role

            return redirect('/dashboard')

        else:

            return "Invalid Email or Password!"

    return render_template('login.html')


# =========================
# LOGOUT
# =========================

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/login')


# =========================
# DASHBOARD
# =========================

@app.route('/dashboard')
def dashboard():

    if 'user_id' not in session:
        return redirect('/login')

    total_tasks = Task.query.count()

    completed_tasks = Task.query.filter_by(
        status='Completed'
    ).count()

    pending_tasks = Task.query.filter_by(
        status='Pending'
    ).count()

    in_progress_tasks = Task.query.filter_by(
        status='In Progress'
    ).count()

    overdue_tasks = Task.query.filter(
        Task.due_date < datetime.utcnow(),
        Task.status != 'Completed'
    ).count()

    total_projects = Project.query.count()

    completion_percentage = 0

    if total_tasks > 0:

        completion_percentage = int(
            (completed_tasks / total_tasks) * 100
        )

    return render_template(

        'dashboard.html',

        name=session['user_name'],

        role=session['role'],

        total_tasks=total_tasks,

        completed_tasks=completed_tasks,

        pending_tasks=pending_tasks,

        in_progress_tasks=in_progress_tasks,

        overdue_tasks=overdue_tasks,

        total_projects=total_projects,

        completion_percentage=completion_percentage
    )


# =========================
# PROJECT MANAGEMENT
# =========================

@app.route('/projects', methods=['GET', 'POST'])
def projects():

    if 'user_id' not in session:
        return redirect('/login')

    # CREATE PROJECT
    if request.method == 'POST':

        if session['role'] != 'Admin':
            return "Access Denied!"

        new_project = Project(

            title=request.form['title'],

            description=request.form['description']

        )

        db.session.add(new_project)

        db.session.commit()

    all_projects = Project.query.order_by(
        Project.created_at.desc()
    ).all()

    return render_template(

        'projects.html',

        projects=all_projects,

        role=session['role']
    )


# =========================
# DELETE PROJECT
# =========================

@app.route('/delete_project/<int:id>')
def delete_project(id):

    if 'user_id' not in session:
        return redirect('/login')

    if session['role'] != 'Admin':
        return "Access Denied!"

    project = Project.query.get_or_404(id)

    # DELETE RELATED TASKS
    Task.query.filter_by(
        project_id=id
    ).delete()

    db.session.delete(project)

    db.session.commit()

    return redirect('/projects')


# =========================
# TASK MANAGEMENT
# =========================

@app.route('/tasks', methods=['GET', 'POST'])
def tasks():

    if 'user_id' not in session:
        return redirect('/login')

    # CREATE TASK
    if request.method == 'POST':

        if session['role'] != 'Admin':
            return "Access Denied!"

        due_date = datetime.strptime(
            request.form['due_date'],
            '%Y-%m-%d'
        )

        new_task = Task(

            title=request.form['title'],

            description=request.form['description'],

            assigned_name=request.form['assigned_name'],

            status=request.form['status'],

            due_date=due_date,

            project_id=request.form['project_id']

        )

        db.session.add(new_task)

        db.session.commit()

    # SEARCH & FILTER
    search = request.args.get('search', '')

    status_filter = request.args.get('status', '')

    query = Task.query.join(Project)

    # SEARCH BY TASK TITLE OR PROJECT NAME
    if search:

        query = query.filter(

            (Task.title.contains(search)) |

            (Project.title.contains(search))

        )

    # FILTER BY STATUS
    if status_filter:

        query = query.filter(
            Task.status == status_filter
        )

    all_tasks = query.order_by(
        Task.created_at.desc()
    ).all()

    all_projects = Project.query.all()

    return render_template(

        'tasks.html',

        tasks=all_tasks,

        projects=all_projects,

        role=session['role'],

        search=search,

        status_filter=status_filter,

        now=datetime.utcnow()

    )


# =========================
# DELETE TASK
# =========================

@app.route('/delete_task/<int:id>')
def delete_task(id):

    if 'user_id' not in session:
        return redirect('/login')

    if session['role'] != 'Admin':
        return "Access Denied!"

    task = Task.query.get_or_404(id)

    db.session.delete(task)

    db.session.commit()

    return redirect('/tasks')


# =========================
# OVERDUE TASKS
# =========================

@app.route('/overdue_tasks')
def overdue_tasks():

    if 'user_id' not in session:
        return redirect('/login')

    overdue = Task.query.filter(

        Task.due_date < datetime.utcnow(),

        Task.status != 'Completed'

    ).order_by(
        Task.due_date.asc()
    ).all()

    return render_template(

        'overdue_tasks.html',

        tasks=overdue

    )


# =========================
# FORGOT PASSWORD
# =========================

@app.route('/forgot_password')
def forgot_password():

    return render_template('forgot_password.html')


# =========================
# CREATE DATABASE
# =========================

with app.app_context():

    db.create_all()



# ==========================================
# REST API ROUTES
# ==========================================

from flask import jsonify


# ==========================================
# GET ALL PROJECTS API
# ==========================================

@app.route('/api/projects', methods=['GET'])
def api_projects():

    projects = Project.query.all()

    data = []

    for project in projects:

        data.append({

            "id": project.id,
            "title": project.title,
            "description": project.description,
            "created_at": project.created_at.strftime('%Y-%m-%d')

        })

    return jsonify(data)


# ==========================================
# GET ALL TASKS API
# ==========================================

@app.route('/api/tasks', methods=['GET'])
def api_tasks():

    tasks = Task.query.all()

    data = []

    for task in tasks:

        data.append({

            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "assigned_name": task.assigned_name,
            "due_date": task.due_date.strftime('%Y-%m-%d'),
            "project": task.project.title

        })

    return jsonify(data)


# ==========================================
# GET SINGLE TASK API
# ==========================================

@app.route('/api/task/<int:id>', methods=['GET'])
def api_single_task(id):

    task = Task.query.get_or_404(id)

    data = {

        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "assigned_name": task.assigned_name,
        "due_date": task.due_date.strftime('%Y-%m-%d'),
        "project": task.project.title

    }

    return jsonify(data)


# ==========================================
# CREATE TASK API
# ==========================================

@app.route('/api/create_task', methods=['POST'])
def api_create_task():

    data = request.get_json()

    title = data.get('title')
    description = data.get('description')
    status = data.get('status')
    assigned_name = data.get('assigned_name')
    due_date = data.get('due_date')
    project_id = data.get('project_id')
        # VALIDATIONS

    if not title or not description or not status:

        return jsonify({

            "error": "Missing required fields"

        }), 400

    task = Task(

        title=title,
        description=description,
        status=status,
        assigned_name=assigned_name,
        due_date=datetime.strptime(due_date, '%Y-%m-%d'),
        project_id=project_id

    )

    db.session.add(task)

    db.session.commit()

    return jsonify({

        "message": "Task created successfully"

    })


# ==========================================
# UPDATE TASK API
# ==========================================

@app.route('/api/update_task/<int:id>', methods=['PUT'])
def api_update_task(id):

    task = Task.query.get_or_404(id)

    data = request.get_json()

    task.title = data.get('title', task.title)

    task.description = data.get(
        'description',
        task.description
    )

    task.status = data.get(
        'status',
        task.status
    )

    task.assigned_name = data.get(
        'assigned_name',
        task.assigned_name
    )

    db.session.commit()

    return jsonify({

        "message": "Task updated successfully"

    })


# ==========================================
# DELETE TASK API
# ==========================================

@app.route('/api/delete_task/<int:id>', methods=['DELETE'])
def api_delete_task(id):

    task = Task.query.get_or_404(id)

    db.session.delete(task)

    db.session.commit()

    return jsonify({

        "message": "Task deleted successfully"

    })


# ==========================================
# DELETE PROJECT API
# ==========================================

@app.route('/api/delete_project/<int:id>', methods=['DELETE'])
def api_delete_project(id):

    project = Project.query.get_or_404(id)

    db.session.delete(project)

    db.session.commit()

    return jsonify({

        "message": "Project deleted successfully"

    })

# ==========================================
# SEARCH TASK API
# ==========================================

@app.route('/api/search_tasks', methods=['GET'])
def api_search_tasks():

    query = request.args.get('query')

    if not query:

        return jsonify({

            "error": "Search query missing"

        }), 400

    tasks = Task.query.filter(

        Task.title.contains(query) |

        Task.assigned_name.contains(query)

    ).all()

    data = []

    for task in tasks:

        data.append({

            "id": task.id,
            "title": task.title,
            "status": task.status,
            "assigned_name": task.assigned_name,
            "project": task.project.title

        })

    return jsonify(data)

# ==========================================
# FILTER TASKS BY STATUS
# ==========================================

@app.route('/api/filter_tasks', methods=['GET'])
def api_filter_tasks():

    status = request.args.get('status')

    if not status:

        return jsonify({

            "error": "Status missing"

        }), 400

    tasks = Task.query.filter_by(status=status).all()

    data = []

    for task in tasks:

        data.append({

            "id": task.id,
            "title": task.title,
            "status": task.status,
            "assigned_name": task.assigned_name,
            "project": task.project.title

        })

    return jsonify(data)


# =========================
# RUN APP
# =========================

if __name__ == '__main__':

    app.run(debug=True)