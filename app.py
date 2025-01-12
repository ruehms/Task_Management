from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import os
import logging
import time
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
# إنشاء التطبيق
app = Flask(__name__)
# إعدادات البريد الإلكتروني
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get("MAIL_USERNAME")  # بريد المرسل
app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD") # كلمة المرور الخاصة بالتطبيق (App Password)


# إعداد التطبيق وإعدادات قاعدة البيانات
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "your_jwt_secret_key"  # مفتاح التوكن السري

mail = Mail(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

logging.basicConfig(level=logging.DEBUG)
#جدول الاشتراكات
class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    frequency = db.Column(db.String(10), nullable=False)  # daily, weekly, monthly
    report_time = db.Column(db.Time, nullable=False)  # وقت التقرير (ساعة فقط)

# نموذج المستخدم
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

# نموذج المهمة
class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    completion_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

# Batch Delete Endpoint
# إضافة قائمة مؤقتة لتخزين آخر مهمة محذوفة
last_deleted_task = {}

@app.route('/tasks/batch-delete', methods=['DELETE'])
@jwt_required()
def batch_delete_tasks():
    global last_deleted_task  # الوصول إلى المتغير كمتغير عام
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not start_date or not end_date:
        return jsonify({"message": "Please provide both start_date and end_date"}), 400

    try:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"message": "Invalid date format. Use YYYY-MM-DD"}), 400

    tasks_to_delete = Task.query.filter(Task.user_id == user.id, Task.start_date >= start_date, Task.due_date <= end_date).all()

    if not tasks_to_delete:
        return jsonify({"message": "No tasks found in the specified date range"}), 404

    last_deleted_task[user.id] = tasks_to_delete[-1]  # تخزين آخر مهمة محذوفة

    for task in tasks_to_delete:
        db.session.delete(task)

    db.session.commit()
    return jsonify({"message": f"{len(tasks_to_delete)} tasks deleted successfully"}), 200


@app.route('/tasks/undo-delete', methods=['POST'])
@jwt_required()
def undo_last_delete():
    global last_deleted_task  # الوصول إلى المتغير كمتغير عام
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()

    last_task = last_deleted_task.get(user.id)

    if not last_task:
        return jsonify({"message": "No task to restore"}), 404

    restored_task = Task(
        title=last_task.title,
        description=last_task.description,
        start_date=last_task.start_date,
        due_date=last_task.due_date,
        completion_date=last_task.completion_date,
        status=last_task.status,
        user_id=user.id
    )

    db.session.add(restored_task)
    db.session.commit()

    # إزالة المهمة من الذاكرة بعد استرجاعها
    last_deleted_task.pop(user.id, None)

    return jsonify({"message": "Task restored successfully!", "task": {
        "id": restored_task.id,
        "title": restored_task.title,
        "description": restored_task.description,
        "start_date": str(restored_task.start_date),
        "due_date": str(restored_task.due_date),
        "status": restored_task.status
    }}), 200


# **الصفحة الرئيسية**
@app.route('/')
def home():
    return "Flask App is Running!"

# **Sign Up (تسجيل مستخدم جديد)**
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()

    if user:
        return jsonify({"message": "User already exists"}), 409

    new_user = User(
        username=data['username'],
        email=data['email'],
        password_hash=generate_password_hash(data['password'])
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User registered successfully!"}), 201

# **Sign In (تسجيل الدخول)**
@app.route('/signin', methods=['POST'])
def signin():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()

    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({"message": "Invalid credentials!"}), 401

    access_token = create_access_token(identity=user.email)
    return jsonify({"access_token": access_token}), 200

# **إنشاء مهمة جديدة**
@app.route('/tasks', methods=['POST'])
@jwt_required()
def create_task():
    current_user_email = get_jwt_identity()  # الحصول على البريد الإلكتروني للمستخدم الحالي من التوكن
    user = User.query.filter_by(email=current_user_email).first()  # جلب المستخدم من قاعدة البيانات

    data = request.get_json()

    # التحقق من إرسال جميع الحقول المطلوبة
    if not all(key in data for key in ['title', 'start_date', 'due_date', 'status']):
        return jsonify({"message": "Please provide 'title', 'start_date', 'due_date', and 'status' fields"}), 400

    # إنشاء مهمة جديدة
    new_task = Task(
        title=data['title'],
        description=data.get('description', ''),  # إذا لم يتم إرسال الوصف، يكون فارغًا
        start_date=data['start_date'],
        due_date=data['due_date'],
        completion_date=data.get('completion_date', None),  # إذا لم يتم إرسال تاريخ الإكمال، يكون None
        status=data['status'],  # Pending, Completed, Overdue
        user_id=user.id
    )

    db.session.add(new_task)
    db.session.commit()
    return jsonify({"message": "Task created successfully!", "task": {"title": new_task.title, "status": new_task.status}}), 201

# **عرض كل المهام الخاصة بالمستخدم**
@app.route('/tasks', methods=['GET'])
@jwt_required()
def get_tasks():
    current_user_email = get_jwt_identity()  # جلب البريد الإلكتروني للمستخدم من التوكن
    user = User.query.filter_by(email=current_user_email).first()  # جلب بيانات المستخدم من قاعدة البيانات

    # الحصول على الفلاتر من الطلب
    status = request.args.get('status')  # Pending, Completed, Overdue
    start_date = request.args.get('start_date')  # صيغة التاريخ: YYYY-MM-DD
    end_date = request.args.get('end_date')  # صيغة التاريخ: YYYY-MM-DD

    # تصفية المهام حسب المستخدم
    tasks_query = Task.query.filter_by(user_id=user.id)

    # فلترة حسب الحالة
    if status:
        tasks_query = tasks_query.filter_by(status=status)

    # فلترة حسب الفترة الزمنية
    if start_date and end_date:
        tasks_query = tasks_query.filter(Task.start_date >= start_date, Task.due_date <= end_date)

    tasks = tasks_query.all()

    # تحويل المهام إلى صيغة JSON للرد
    tasks_list = [{"id": task.id, "title": task.title, "description": task.description, "status": task.status, "start_date": str(task.start_date), "due_date": str(task.due_date)} for task in tasks]
    return jsonify(tasks_list), 200


    # تحويل المهام إلى JSON للرد
    tasks_list = [{"id": task.id, "title": task.title, "description": task.description, "status": task.status} for task in tasks]
    return jsonify(tasks_list), 200

# **عرض مهمة معينة بواسطة ID**
@app.route('/tasks/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task(task_id):
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()
    task = Task.query.filter_by(id=task_id, user_id=user.id).first()

    if not task:
        return jsonify({"message": "Task not found"}), 404

    return jsonify({"id": task.id, "title": task.title, "description": task.description}), 200

# **تحديث مهمة معينة**
@app.route('/tasks/<int:task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()
    task = Task.query.filter_by(id=task_id, user_id=user.id).first()

    if not task:
        return jsonify({"message": "Task not found"}), 404

    data = request.get_json()
    task.title = data.get('title', task.title)
    task.description = data.get('description', task.description)
    db.session.commit()
    return jsonify({"message": "Task updated successfully!"}), 200

# **حذف مهمة معينة**
@app.route('/tasks/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()
    task = Task.query.filter_by(id=task_id, user_id=user.id).first()

    if not task:
        return jsonify({"message": "Task not found"}), 404

    db.session.delete(task)
    db.session.commit()
    return jsonify({"message": "Task deleted successfully!"}), 200
@app.route('/subscribe', methods=['POST'])
@jwt_required()
def subscribe():
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()

    data = request.get_json()
    start_date_str = data.get('start_date')  # Format: YYYY-MM-DD
    frequency = data.get('frequency')        # daily, weekly, monthly
    report_time_str = data.get('report_time')  # e.g., 10:00:00

    # Basic checks for missing data
    if not start_date_str or not frequency or not report_time_str:
        return jsonify({"message": "Please provide start_date, frequency, and report_time"}), 400

    # Validate start_date
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"message": "Invalid date format. Use YYYY-MM-DD"}), 400

    # Validate frequency
    if frequency not in ['daily', 'weekly', 'monthly']:
        return jsonify({"message": "Frequency must be daily, weekly, or monthly"}), 400

    # **Strictly validate report_time** to ensure hour-only (e.g., 10:00:00)
    try:
        parsed_time = datetime.strptime(report_time_str, "%H:%M:%S").time()
        # Check if minutes or seconds are non-zero
        if parsed_time.minute != 0 or parsed_time.second != 0:
            return jsonify({"message": "report_time must have zero minutes and seconds, e.g. 10:00:00"}), 400
    except ValueError:
        return jsonify({"message": "Invalid time format. Use HH:MM:SS (e.g. 10:00:00)"}), 400

    # Ensure the user doesn't already have a subscription
    subscription = Subscription.query.filter_by(user_id=user.id).first()
    if subscription:
        return jsonify({"message": "You are already subscribed"}), 400

    # Create and commit the subscription
    new_subscription = Subscription(
        user_id=user.id,
        start_date=start_date,
        frequency=frequency,
        report_time=parsed_time
    )
    db.session.add(new_subscription)
    db.session.commit()

    # Schedule the newly added subscription job
    schedule_reports()

    return jsonify({"message": "Subscribed to reports successfully!"}), 201


@app.route('/unsubscribe', methods=['DELETE'])
@jwt_required()
def unsubscribe():
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()

    subscription = Subscription.query.filter_by(user_id=user.id).first()

    if not subscription:
        return jsonify({"message": "No active subscription found"}), 404

    db.session.delete(subscription)
    db.session.commit()

    return jsonify({"message": "Unsubscribed successfully!"}), 200

@app.route('/jobs', methods=['GET'])
def list_jobs():
    jobs = scheduler.get_jobs()
    job_list = [{"id": job.id, "next_run_time": str(job.next_run_time)} for job in jobs]
    return jsonify(job_list), 200


def send_report_email(subscription):
    with app.app_context():
        user = User.query.get(subscription.user_id)

        # 1. Determine the end_date (today's date).
        end_date = datetime.today().date()

        # 2. Determine the start_of_range based on subscription frequency.
        if subscription.frequency == 'daily':
            start_of_range = end_date - timedelta(days=1)
        elif subscription.frequency == 'weekly':
            start_of_range = end_date - timedelta(days=7)
        elif subscription.frequency == 'monthly':
            start_of_range = end_date - timedelta(days=30)
        else:
            # Fallback if frequency isn't recognized
            # or if you want to default to the subscription's own start_date
            start_of_range = subscription.start_date

        # 3. Ensure we don't go earlier than subscription.start_date:
        if start_of_range < subscription.start_date:
            start_of_range = subscription.start_date

        # 4. Fetch tasks in the desired date range for due_date:
        tasks = Task.query.filter(
            Task.user_id == user.id,
            Task.due_date >= start_of_range,
            Task.due_date <= end_date
        ).all()

        # 5. Build the HTML body listing the tasks:
        task_details = "".join(
            f"<li>{task.title}: {task.description} - Status: {task.status}</li>"
            for task in tasks
        )
        html_body = f"""
        <h2>Task Report for {user.username}</h2>
        <p>Here are your tasks (from {start_of_range} to {end_date}):</p>
        <ul>{task_details}</ul>
        """

        # 6. Send the email
        msg = Message(
            subject="Your Scheduled Task Report",
            sender=app.config['MAIL_USERNAME'],
            recipients=[user.email],
            html=html_body
        )
        mail.send(msg)

@app.route('/test-email', methods=['GET'])
def test_email():
    msg = Message(
        subject="Hello from Flask-Mail",
        sender=app.config.get("MAIL_USERNAME"),
        recipients=["Khaledw0097@gmail.com"],
        body="This is a test email!"
    )
    try:
        mail.send(msg)
        return {"message": "Email sent successfully!"}
    except Exception as e:
        return {"error": str(e)}, 500

def schedule_reports():
    subscriptions = Subscription.query.all()
    if not subscriptions:
        logging.warning("No subscriptions found for scheduling.")
    for subscription in subscriptions:
        logging.info(f"Scheduling report for user_id {subscription.user_id} at {subscription.report_time}")
        scheduler.add_job(
            func=send_report_email,
            trigger='cron',
            args=[subscription],
            hour=subscription.report_time.hour,
            minute=subscription.report_time.minute,
            id=f"subscription_{subscription.id}",
            replace_existing=True
        )
        logging.info(f"Job subscription_{subscription.id} added")

# تهيئة الـ APScheduler
scheduler = BackgroundScheduler()
scheduler.add_jobstore(SQLAlchemyJobStore(url=os.getenv("DATABASE_URI")), alias='default')
scheduler.start()

# **تشغيل التطبيق**
if __name__ == "__main__":
    time.sleep(2)
    schedule_reports()
    app.run(host="0.0.0.0", port=5000, debug=True)

