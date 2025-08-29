from flask import Flask, request, jsonify, render_template, send_from_directory
import mysql.connector
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import uuid
# Import ML plate recognition
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'model'))
from LPD2 import recognize_plate_trocr, remove_white_border
import cv2

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
    # For testing, always return the same plate so entry and exit match
    return "TEST-123"

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

    # Run ML plate recognition
    try:
        img_cv = cv2.imread(file_path)
        if img_cv is None:
            return jsonify({'error': 'Failed to read uploaded image for plate recognition.'}), 422
        # Remove white border (preprocessing)
        plate_crop = remove_white_border(img_cv)
        plate = recognize_plate_trocr(plate_crop)
        plate = plate.strip()
        if not plate:
            return jsonify({'error': 'Plate could not be detected.'}), 422
    except Exception as e:
        return jsonify({'error': f'Plate recognition error: {str(e)}'}), 422

    entry_time = datetime.now()
    db = get_db()
    if not db:
        return jsonify({'error': 'Database connection failed. Please try again later.'}), 503

    try:
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO parking_logs (plate, entry_time) VALUES (%s, %s)",
            (plate, entry_time)
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
    finally:
        db.close()
# Get dashboard statistics
@app.route('/get-stats', methods=['GET'])
def get_stats():
    db = get_db()
    if not db:
        return jsonify({'error': 'Database connection error'}), 500
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM parking_stats")
        stats = cursor.fetchone()
        cursor.close()
        if not stats:
            return jsonify({'error': 'No stats found'}), 404
        # Rename keys for frontend compatibility
        return jsonify({
            'total_vehicles': stats.get('total_records', 0),
            'active_parkings': stats.get('active_parkings', 0),
            'completed_parkings': stats.get('completed_parkings', 0),
            'total_revenue': float(stats.get('total_revenue', 0)),
            'avg_duration_minutes': float(stats.get('avg_duration_minutes', 0)),
            'today_entries': stats.get('today_entries', 0)
        })
    except Exception as e:
        print(f"Get stats error: {e}")
        return jsonify({'error': 'Database error'}), 500
    finally:
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