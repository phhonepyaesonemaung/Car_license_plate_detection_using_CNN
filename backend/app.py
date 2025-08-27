from flask import Flask, request, jsonify, render_template, send_from_directory
import mysql.connector
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import uuid

app = Flask(__name__, template_folder='../frontend/templates')

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# MySQL config
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'ppsmisZzz23@!',
    'database': 'parking_db'
}

def get_db():
    try:
        return mysql.connector.connect(**db_config)
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def mock_plate_recognition(image_path):
    """Mock function to simulate license plate recognition"""
    # In a real system, this would use OCR/ML to extract plate number
    # For demo purposes, generate a random plate
    import random
    import string
    letters = ''.join(random.choices(string.ascii_uppercase, k=3))
    numbers = ''.join(random.choices(string.digits, k=3))
    return f"{letters}-{numbers}"

# Fare calculation constants
BASE_FARE = 20
RATE_PER_MIN = 1

# Database initialization
def init_db():
    """Initialize database with required tables"""
    db = get_db()
    if not db:
        return False
    
    try:
        cursor = db.cursor()
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create parking_logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parking_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                plate VARCHAR(20) NOT NULL,
                entry_time DATETIME NOT NULL,
                exit_time DATETIME NULL,
                fare DECIMAL(10,2) NULL,
                image_path VARCHAR(255) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_plate (plate),
                INDEX idx_entry_time (entry_time)
            )
        """)
        
        # Create default admin user if not exists
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            admin_hash = generate_password_hash('admin123')
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                ('admin', admin_hash)
            )
        
        db.commit()
        cursor.close()
        return True
        
    except mysql.connector.Error as err:
        print(f"Database initialization error: {err}")
        return False
    finally:
        db.close()

# Routes
@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login.html')
def login_page():
    return render_template('login.html')

@app.route('/file_upload.html')
def file_upload_page():
    return render_template('file_upload.html')

@app.route('/logs.html')
def logs_page():
    return render_template('logs.html')

# Serve static files
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('frontend/static', filename)

# API Routes
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        return jsonify({
            'success': False,
            'message': 'Username and password are required'
        })
    
    db = get_db()
    if not db:
        return jsonify({
            'success': False,
            'message': 'Database connection error'
        })
    
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id, username, password_hash FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        cursor.close()
        
        if user and check_password_hash(user['password_hash'], password):
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'redirect': '/file_upload.html'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid username or password'
            })
    
    except mysql.connector.Error as err:
        print(f"Login error: {err}")
        return jsonify({
            'success': False,
            'message': 'Database error'
        })
    finally:
        db.close()

@app.route('/upload-entry', methods=['POST'])
def upload_entry():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file was provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file was selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed types are: JPG, PNG, GIF'}), 400
        
        try:
            # Save uploaded file
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
        except Exception as e:
            return jsonify({'error': 'Failed to save uploaded file. Please try again.'}), 500
        
        # Mock plate recognition
        try:
            plate = mock_plate_recognition(file_path)
        except Exception as e:
            return jsonify({'error': 'Failed to process image. Please ensure image is clear.'}), 422

        entry_time = datetime.now()
        
        try:
            db = get_db()
            if not db:
                return jsonify({'error': 'Database connection failed. Please try again later.'}), 503
            
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO parking_logs (plate, entry_time, image_path) VALUES (%s, %s, %s)",
                (plate, entry_time, unique_filename)
            )
            db.commit()
            cursor.close()
            
            return jsonify({
                'plate': plate,
                'status': 'Entry recorded successfully',
                'timestamp': entry_time.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        except Exception as e:
            return jsonify({'error': 'Database error. Please try again later.'}), 503
            
    except Exception as e:
        app.logger.error(f"Entry upload error: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred. Please try again.'}), 500
    
    finally:
        if 'db' in locals():
            db.close()

@app.route('/upload-exit', methods=['POST'])
def upload_exit():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Mock plate recognition
        plate = mock_plate_recognition(file_path)
        exit_time = datetime.now()
        
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection error'}), 500
        
        cursor = db.cursor(dictionary=True)
        
        # Find the most recent entry without exit
        cursor.execute(
            "SELECT id, entry_time FROM parking_logs WHERE plate=%s AND exit_time IS NULL ORDER BY entry_time DESC LIMIT 1",
            (plate,)
        )
        log = cursor.fetchone()
        
        if not log:
            cursor.close()
            return jsonify({
                'plate': plate,
                'status': 'No matching entry found',
                'error': 'Vehicle entry not recorded'
            }), 404
        
        # Calculate duration and fare
        entry_time = log['entry_time']
        duration_seconds = (exit_time - entry_time).total_seconds()
        duration_minutes = duration_seconds / 60
        fare = BASE_FARE + (RATE_PER_MIN * duration_minutes)
        
        # Update the log with exit information
        cursor.execute(
            "UPDATE parking_logs SET exit_time=%s, fare=%s WHERE id=%s",
            (exit_time, round(fare, 2), log['id'])
        )
        db.commit()
        cursor.close()
        
        return jsonify({
            'plate': plate,
            'duration(mins)': round(duration_minutes, 2),
            'fare': round(fare, 2),
            'status': 'Exit processed successfully'
        })
    
    except Exception as e:
        print(f"Exit upload error: {e}")
        return jsonify({'error': 'Failed to process exit'}), 500
    finally:
        if 'db' in locals():
            db.close()

@app.route('/get-logs', methods=['GET'])
def get_logs():
    db = get_db()
    if not db:
        return jsonify([]), 500
    
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT plate, entry_time, exit_time, 
                   TIMESTAMPDIFF(MINUTE, entry_time, exit_time) AS duration, 
                   fare 
            FROM parking_logs 
            ORDER BY entry_time DESC 
            LIMIT 100
        """)
        logs = cursor.fetchall()
        cursor.close()
        
        # Format the data for frontend
        formatted_logs = []
        for log in logs:
            formatted_log = {
                'plate': log['plate'],
                'entry': log['entry_time'].strftime('%Y-%m-%d %H:%M:%S') if log['entry_time'] else '-',
                'exit': log['exit_time'].strftime('%Y-%m-%d %H:%M:%S') if log['exit_time'] else '-',
                'duration': f"{log['duration']} min" if log['duration'] else '-',
                'fare': f"${log['fare']}" if log['fare'] else '-'
            }
            formatted_logs.append(formatted_log)
        
        return jsonify(formatted_logs)
    
    except mysql.connector.Error as err:
        print(f"Get logs error: {err}")
        return jsonify([]), 500
    finally:
        db.close()

@app.route('/search-car', methods=['GET'])
def search_car():
    plate = request.args.get('plate')
    if not plate:
        return jsonify({'error': 'Plate parameter required'}), 400
    
    db = get_db()
    if not db:
        return jsonify({'error': 'Database connection error'}), 500
    
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT plate, entry_time, exit_time, fare FROM parking_logs WHERE plate LIKE %s ORDER BY entry_time DESC",
            (f"%{plate}%",)
        )
        logs = cursor.fetchall()
        cursor.close()
        
        if not logs:
            return jsonify([])
        
        # Format the results
        formatted_logs = []
        for log in logs:
            formatted_log = {
                'plate': log['plate'],
                'entry': log['entry_time'].strftime('%Y-%m-%d %H:%M:%S') if log['entry_time'] else '-',
                'exit': log['exit_time'].strftime('%Y-%m-%d %H:%M:%S') if log['exit_time'] else '-',
                'fare': f"${log['fare']}" if log['fare'] else '-'
            }
            formatted_logs.append(formatted_log)
        
        return jsonify(formatted_logs)
    
    except mysql.connector.Error as err:
        print(f"Search error: {err}")
        return jsonify({'error': 'Database error'}), 500
    finally:
        db.close()

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    db = get_db()
    if db:
        db.close()
        return jsonify({'status': 'healthy', 'database': 'connected'})
    else:
        return jsonify({'status': 'unhealthy', 'database': 'disconnected'}), 503

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(413)
def file_too_large(error):
    return jsonify({'error': 'File too large. Maximum size is 5MB.'}), 413

if __name__ == '__main__':
    # Initialize database on startup
    if init_db():
        print("Database initialized successfully")
        print("Default login: admin / admin123")
    else:
        print("Warning: Database initialization failed")
    
    app.run(debug=True, host='0.0.0.0', port=5000)