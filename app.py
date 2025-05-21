import os
import numpy as np
import face_recognition
import cv2
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
import base64
from datetime import datetime
import json
import uuid
import shutil

# Import database models
from database.models import User, FaceEncoding, Attendance
from database.db_setup import init_database

# Initialize the Flask application
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a random secret key in production

# Initialize database
init_database()

# Configure upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Home page route"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login route"""
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        password = request.form.get('password')

        if not student_id or not password:
            flash('Please provide both student ID and password', 'danger')
            return render_template('login.html')

        user = User.authenticate(student_id, password)

        if user:
            session['user_id'] = user['id']
            session['student_id'] = user['student_id']
            session['name'] = user['name']
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid student ID or password', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route"""
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Validate input
        if not all([student_id, name, email, password, confirm_password]):
            flash('Please fill in all fields', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')

        # Check if student ID already exists
        existing_user = User.get_user_by_student_id(student_id)
        if existing_user:
            flash('Student ID already registered', 'danger')
            return render_template('register.html')

        # Create user
        user_id = User.create_user(student_id, name, email, password)

        if user_id:
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Registration failed. Please try again.', 'danger')

    return render_template('register.html')


@app.route('/logout')
def logout():
    """Logout route"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
def dashboard():
    """User dashboard route"""
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.get_user_by_id(user_id)

    # Get user's face encodings
    face_encodings = FaceEncoding.get_face_encodings_by_user_id(user_id)
    has_face_data = len(face_encodings) > 0

    # Get user's attendance records
    attendance_records = Attendance.get_attendance_by_user(user_id)

    return render_template('dashboard.html',
                           user=user,
                           has_face_data=has_face_data,
                           attendance_records=attendance_records)


@app.route('/face-registration', methods=['GET', 'POST'])
def face_registration():
    """Face registration route"""
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Check if the post request has the file part
        if 'face_image' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)

        file = request.files['face_image']

        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            # Generate a unique filename
            filename = secure_filename(f"{session['student_id']}_{uuid.uuid4().hex}.jpg")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Process the image for face detection
            image = face_recognition.load_image_file(filepath)
            face_locations = face_recognition.face_locations(image)

            if not face_locations:
                os.remove(filepath)  # Remove the file if no face is detected
                flash('No face detected in the image. Please try again.', 'danger')
                return redirect(request.url)

            if len(face_locations) > 1:
                os.remove(filepath)  # Remove the file if multiple faces are detected
                flash('Multiple faces detected in the image. Please upload an image with only your face.', 'danger')
                return redirect(request.url)

            # Extract face encoding
            face_encoding = face_recognition.face_encodings(image, face_locations)[0]

            # Save face encoding to database
            encoding_id = FaceEncoding.save_face_encoding(session['user_id'], face_encoding)

            if encoding_id:
                flash('Face registered successfully!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Failed to register face. Please try again.', 'danger')
        else:
            flash('Invalid file type. Please upload a JPG, JPEG or PNG image.', 'danger')

    return render_template('face_registration.html')


@app.route('/webcam-registration', methods=['GET', 'POST'])
def webcam_registration():
    """Face registration using webcam"""
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Get the base64 encoded image from the request
        image_data = request.form.get('image_data')

        if not image_data:
            return jsonify({'success': False, 'message': 'No image data received'})

        # Remove the data URL prefix
        image_data = image_data.split(',')[1]

        # Decode the base64 image
        image_bytes = base64.b64decode(image_data)

        # Generate a unique filename
        filename = f"{session['student_id']}_{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Save the image
        with open(filepath, 'wb') as f:
            f.write(image_bytes)

        # Process the image for face detection
        image = face_recognition.load_image_file(filepath)
        face_locations = face_recognition.face_locations(image)

        if not face_locations:
            os.remove(filepath)  # Remove the file if no face is detected
            return jsonify({'success': False, 'message': 'No face detected in the image. Please try again.'})

        if len(face_locations) > 1:
            os.remove(filepath)  # Remove the file if multiple faces are detected
            return jsonify({'success': False,
                            'message': 'Multiple faces detected in the image. Please ensure only your face is visible.'})

        # Extract face encoding
        face_encoding = face_recognition.face_encodings(image, face_locations)[0]

        # Save face encoding to database
        encoding_id = FaceEncoding.save_face_encoding(session['user_id'], face_encoding)

        if encoding_id:
            return jsonify({'success': True, 'message': 'Face registered successfully!'})
        else:
            os.remove(filepath)
            return jsonify({'success': False, 'message': 'Failed to register face. Please try again.'})

    return render_template('webcam_registration.html')


@app.route('/webcam-registration-admin', methods=['POST'])
def webcam_registration_admin():
    """Process webcam registration for face data"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})

    # Get image data from form
    image_data = request.form.get('image_data')
    user_id = request.form.get('user_id')

    if not image_data:
        return jsonify({'success': False, 'message': 'No image data provided'})

    # Check if user_id is provided (for admin registration)
    if not user_id:
        user_id = session['user_id']

    # Get user data
    user = User.get_user_by_id(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'})

    try:
        # Remove header from the base64 string
        image_data = image_data.split(',')[1]

        # Decode base64 string to image
        image_bytes = base64.b64decode(image_data)

        # Create a temporary file to save the image
        temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{uuid.uuid4().hex}.jpg")
        with open(temp_filepath, 'wb') as f:
            f.write(image_bytes)

        # Process the image for face detection
        image = face_recognition.load_image_file(temp_filepath)
        face_locations = face_recognition.face_locations(image)

        if not face_locations:
            os.remove(temp_filepath)
            return jsonify({'success': False, 'message': 'No face detected in the image. Please try again.'})

        if len(face_locations) > 1:
            os.remove(temp_filepath)
            return jsonify({'success': False,
                            'message': 'Multiple faces detected in the image. Please ensure only one face is visible.'})

        # Extract face encoding
        face_encoding = face_recognition.face_encodings(image, face_locations)[0]

        # Save face encoding to database
        encoding_id = FaceEncoding.save_face_encoding(user_id, face_encoding)

        if encoding_id:
            # Save the processed image with a proper filename
            final_filename = secure_filename(f"{user['student_id']}_{uuid.uuid4().hex}.jpg")
            final_filepath = os.path.join(app.config['UPLOAD_FOLDER'], final_filename)
            shutil.copy(temp_filepath, final_filepath)

            # Remove temporary file
            os.remove(temp_filepath)

            return jsonify({'success': True, 'message': 'Face registered successfully!'})
        else:
            os.remove(temp_filepath)
            return jsonify({'success': False, 'message': 'Failed to register face. Please try again.'})

    except Exception as e:
        # Clean up if there was an error
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'})


@app.route('/attendance', methods=['GET'])
def attendance():
    """View attendance records"""
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

    attendance_records = Attendance.get_attendance_by_date(date)

    return render_template('attendance.html',
                           attendance_records=attendance_records,
                           selected_date=date)


@app.route('/check-in', methods=['GET'])
def check_in():
    """Manual check-in page"""
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    return render_template('check_in.html')


@app.route('/process-check-in', methods=['POST'])
def process_check_in():
    """Process manual check-in"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})

    user_id = session['user_id']

    # Record check-in
    attendance_id = Attendance.record_check_in(user_id)

    if attendance_id:
        return jsonify({'success': True, 'message': 'Check-in successful!'})
    else:
        return jsonify({'success': False, 'message': 'You have already checked in today'})


@app.route('/check-out', methods=['POST'])
def check_out():
    """Process check-out"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})

    user_id = session['user_id']

    # Record check-out
    success = Attendance.record_check_out(user_id)

    if success:
        return jsonify({'success': True, 'message': 'Check-out successful!'})
    else:
        return jsonify({'success': False, 'message': 'No active check-in found for today'})


@app.route('/face-recognition-attendance', methods=['GET'])
def face_recognition_attendance():
    """Face recognition attendance page"""
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    return render_template('face_recognition_attendance.html')


@app.route('/process-face-attendance', methods=['POST'])
def process_face_attendance():
    """Process face recognition attendance"""
    image_data = request.form.get('image_data')
    if not image_data:
        return jsonify({'success': False, 'message': 'No image data received'})

    image_data = image_data.split(',')[1]
    image_bytes = base64.b64decode(image_data)
    temp_filename = f"temp_{uuid.uuid4().hex}.jpg"
    temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)

    with open(temp_filepath, 'wb') as f:
        f.write(image_bytes)

    try:
        image = face_recognition.load_image_file(temp_filepath)
        face_locations = face_recognition.face_locations(image)

        if not face_locations:
            return jsonify({'success': False, 'message': 'No face detected in the image. Please try again.'})
        if len(face_locations) > 1:
            return jsonify({'success': False, 'message': 'Multiple faces detected. Please ensure only one person is in the frame.'})

        face_encoding = face_recognition.face_encodings(image, face_locations)[0]

        # 获取所有人脸编码，确保包含user_id、student_id、name
        all_encodings = FaceEncoding.get_all_face_encodings()
        if not all_encodings:
            return jsonify({'success': False, 'message': 'No registered faces found in the database.'})

        known_encodings = [enc['encoding'] for enc in all_encodings]
        matches = face_recognition.compare_faces(known_encodings, face_encoding)
        face_distances = face_recognition.face_distance(known_encodings, face_encoding)

        # 找到最佳匹配（距离最小且匹配成功）
        best_match_index = None
        min_distance = 1.0
        for i, match in enumerate(matches):
            if match and face_distances[i] < min_distance:
                min_distance = face_distances[i]
                best_match_index = i

        matched_users = []
        if best_match_index is not None:
            confidence = 1 - face_distances[best_match_index]
            matched_user = {
                'user_id': all_encodings[best_match_index]['user_id'],
                'student_id': all_encodings[best_match_index]['student_id'],
                'name': all_encodings[best_match_index]['name'],
                'confidence': confidence
            }
            matched_users.append(matched_user)

            # 用 user_id 进行考勤
            matched_user_id = matched_user['user_id']
            attendance_id = Attendance.record_check_in(matched_user_id)

            if attendance_id:
                return jsonify({
                    'success': True,
                    'message': 'Face recognized successfully!',
                    'matched_users': matched_users
                })
            else:
                return jsonify({
                    'success': True,
                    'message': 'Attendance already recorded for today.',
                    'matched_users': matched_users
                })
        else:
            return jsonify({'success': False, 'message': 'Face not recognized. Please register your face or try again.'})

    finally:
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)


@app.route('/user-management', methods=['GET'])
def user_management():
    """User management route for admins"""
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    # Check if user is admin (in a real app, you would check user role)
    # For demo purposes, we'll allow all logged-in users to access this page

    # Get search query and pagination parameters
    search_query = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    per_page = 10

    # Get users based on search query
    if search_query:
        users = User.search_users(search_query, page, per_page)
        total_users = User.count_search_results(search_query)
    else:
        users = User.get_all_users(page, per_page)
        total_users = User.count_all_users()

    # Calculate total pages
    total_pages = (total_users + per_page - 1) // per_page

    # Check if each user has face data
    for user in users:
        face_encodings = FaceEncoding.get_face_encodings_by_user_id(user['id'])
        user['has_face_data'] = len(face_encodings) > 0

    return render_template('user_management.html',
                           users=users,
                           search_query=search_query,
                           current_page=page,
                           total_pages=total_pages)


@app.route('/edit-user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    """Edit user route"""
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    # Check if user is admin (in a real app, you would check user role)
    # For demo purposes, we'll allow all logged-in users to access this page

    # Get user data
    user = User.get_user_by_id(user_id)
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('user_management'))

    # Check if user has face data
    face_encodings = FaceEncoding.get_face_encodings_by_user_id(user_id)
    user['has_face_data'] = len(face_encodings) > 0

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        is_active = 'is_active' in request.form

        # Update user
        success = User.update_user(user_id, student_id, name, email, password, role, is_active)

        if success:
            flash('User updated successfully', 'success')
            return redirect(url_for('user_management'))
        else:
            flash('Failed to update user', 'danger')

    return render_template('edit_user.html', user=user)


@app.route('/delete-user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    """Delete user route"""
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    # Check if user is admin (in a real app, you would check user role)
    # For demo purposes, we'll allow all logged-in users to access this page

    # Delete user
    success = User.delete_user(user_id)

    if success:
        flash('User deleted successfully', 'success')
    else:
        flash('Failed to delete user', 'danger')

    return redirect(url_for('user_management'))


@app.route('/reset-face-data/<int:user_id>', methods=['POST'])
def reset_face_data(user_id):
    """Reset user's face data"""
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    # Check if user is admin (in a real app, you would check user role)
    # For demo purposes, we'll allow all logged-in users to access this page

    # Delete face encodings
    success = FaceEncoding.delete_face_encodings_by_user_id(user_id)

    if success:
        flash('Face data reset successfully', 'success')
    else:
        flash('Failed to reset face data', 'danger')

    return redirect(url_for('edit_user', user_id=user_id))


@app.route('/face-registration-admin/<int:user_id>', methods=['GET', 'POST'])
def face_registration_admin(user_id):
    """Face registration for admin to register user's face"""
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))

    # Check if user is admin (in a real app, you would check user role)
    # For demo purposes, we'll allow all logged-in users to access this page

    # Get user data
    if session.get('student_id') != 'admin':
        flash('Access denied: Admins only', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.get_user_by_id(user_id)
    if not user:
        flash('danger')
        return redirect(url_for('user_management'))

    if request.method == 'POST':
        # Check if the post request has the file part
        if 'face_image' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)

        file = request.files['face_image']

        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            # Generate a unique filename
            filename = secure_filename(f"{user['student_id']}_{uuid.uuid4().hex}.jpg")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Process the image for face detection
            image = face_recognition.load_image_file(filepath)
            face_locations = face_recognition.face_locations(image)

            if not face_locations:
                os.remove(filepath)  # Remove the file if no face is detected
                flash('No face detected in the image. Please try again.', 'danger')
                return redirect(request.url)

            if len(face_locations) > 1:
                os.remove(filepath)  # Remove the file if multiple faces are detected
                flash('Multiple faces detected in the image. Please upload an image with only one face.', 'danger')
                return redirect(request.url)

            # Extract face encoding
            face_encoding = face_recognition.face_encodings(image, face_locations)[0]

            # Save face encoding to database
            encoding_id = FaceEncoding.save_face_encoding(user_id, face_encoding)

            if encoding_id:
                flash('Face registered successfully!', 'success')
                return redirect(url_for('edit_user', user_id=user_id))
            else:
                flash('Failed to register face. Please try again.', 'danger')
        else:
            flash('Invalid file type. Please upload a JPG, JPEG or PNG image.', 'danger')

    return render_template('face_registration_admin.html', user=user)


@app.route('/detect-face', methods=['POST'])
def detect_face():
    """检测人脸API"""
    if 'image_data' not in request.form:
        return jsonify({'success': False, 'message': '未提供图像数据'})

    # 获取图像数据
    image_data = request.form.get('image_data')

    try:
        # 移除base64头部
        if ',' in image_data:
            image_data = image_data.split(',')[1]

        # 解码base64图像
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # 转换为RGB（OpenCV使用BGR）
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # 检测人脸
        face_locations = face_recognition.face_locations(rgb_image)

        return jsonify({
            'success': True,
            'message': '人脸检测完成',
            'face_count': len(face_locations)
        })

    except Exception as e:
        app.logger.error(f"人脸检测错误: {str(e)}")
        return jsonify({'success': False, 'message': f'处理图像时出错: {str(e)}'})


@app.route('/recognize-face', methods=['POST'])
def recognize_face():
    """识别人脸API"""
    if 'image_data' not in request.form:
        return jsonify({'success': False, 'message': '未提供图像数据'})

    # 获取图像数据
    image_data = request.form.get('image_data')

    try:
        # 移除base64头部
        if ',' in image_data:
            image_data = image_data.split(',')[1]

        # 解码base64图像
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # 转换为RGB（OpenCV使用BGR）
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # 检测人脸
        face_locations = face_recognition.face_locations(rgb_image)

        if not face_locations:
            return jsonify({'success': False, 'message': '未检测到人脸，请确保脸部清晰可见'})

        if len(face_locations) > 1:
            return jsonify({'success': False, 'message': '检测到多个人脸，请确保画面中只有一个人脸'})

        # 提取人脸特征
        face_encoding = face_recognition.face_encodings(rgb_image, face_locations)[0]

        # 加载所有已知人脸编码
        known_faces = FaceEncoding.get_all_face_encodings()

        if not known_faces:
            return jsonify({'success': False, 'message': '数据库中没有注册的人脸'})

        # 比较人脸
        known_encodings = [face['encoding'] for face in known_faces]
        matches = face_recognition.compare_faces(known_encodings, face_encoding)
        face_distances = face_recognition.face_distance(known_encodings, face_encoding)

        if True in matches:
            # 找到最佳匹配
            best_match_index = np.argmin(face_distances)
            confidence = 1 - face_distances[best_match_index]

            if confidence >= 0.6:  # 置信度阈值
                matched_user = known_faces[best_match_index]

                # 返回识别结果
                return jsonify({
                    'success': True,
                    'message': f'成功识别为 {matched_user["name"]}',
                    'user': {
                        'user_id': matched_user['user_id'],
                        'student_id': matched_user['student_id'],
                        'name': matched_user['name']
                    },
                    'confidence': float(confidence)
                })
            else:
                return jsonify({'success': False, 'message': '识别置信度过低，请重新尝试'})
        else:
            return jsonify({'success': False, 'message': '无法识别您的身份，请确保您已注册人脸数据'})

    except Exception as e:
        app.logger.error(f"人脸识别错误: {str(e)}")
        return jsonify({'success': False, 'message': f'处理图像时出错: {str(e)}'})


@app.route('/record-attendance', methods=['POST'])
def record_attendance():
    """记录考勤API"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '���先登录'})

    # 获取请求数据
    data = request.get_json()

    if not data or 'user_id' not in data:
        return jsonify({'success': False, 'message': '无效的请求数据'})

    user_id = data.get('user_id')
    confidence = data.get('confidence', 0)

    # 验证用户身份（确保当前登录用户只能为自己签到）
    if int(session['user_id']) != int(user_id) and session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '无权为其他用户签到'})

    # 检查是否已经签到
    today_attendance = Attendance.get_today_attendance(user_id)
    if today_attendance:
        return jsonify({'success': False, 'message': '今天已经签到，无需重复签到'})

    # 记录考勤
    attendance_id = Attendance.record_check_in(user_id)

    if attendance_id:
        # 获取用户信息
        user = User.get_user_by_id(user_id)

        return jsonify({
            'success': True,
            'message': f'签到成功！欢迎 {user["name"]}',
            'attendance_id': attendance_id,
            'check_in_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    else:
        return jsonify({'success': False, 'message': '签到失败，请稍后重试'})


@app.route('/get-recent-attendance', methods=['GET'])
def get_recent_attendance():
    """获取最近考勤记录API"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})

    # 获取最近的考勤记录（默认10条）
    limit = request.args.get('limit', 10, type=int)
    records = Attendance.get_recent_attendance(limit)

    return jsonify({
        'success': True,
        'records': records
    })


if __name__ == '__main__':
    app.run(debug=True)

