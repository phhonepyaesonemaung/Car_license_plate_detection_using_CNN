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

# Fare calculation constants
BASE_FARE = 20
RATE_PER_MIN = 1

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
        
        # Create parking_stats view for dashboard
        cursor.execute("""
            CREATE OR REPLACE VIEW parking_stats AS
            SELECT 
                COUNT(*) as total_records,
                SUM(CASE WHEN exit_time IS NULL THEN 1 ELSE 0 END) as active_parkings,
                SUM(CASE WHEN exit_time IS NOT NULL THEN 1 ELSE 0 END) as completed_parkings,
                COALESCE(SUM(fare), 0) as total_revenue,
                COALESCE(AVG(TIMESTAMPDIFF(MINUTE, entry_time, exit_time)), 0) as avg_duration_minutes,
                SUM(CASE WHEN DATE(entry_time) = CURDATE() THEN 1 ELSE 0 END) as today_entries
            FROM parking_logs
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

    # Run ML plate recognition using process_image_file
    try:
        from LPD2 import process_image_file
        plate = process_image_file(file_path)
        if not plate:
            return jsonify({'error': 'Plate could not be detected.'}), 422
    except Exception as e:
        return jsonify({'error': f'Plate recognition error: {str(e)}'}), 422

    entry_time = datetime.now()
    db = get_db()
    if not db:
        return jsonify({'error': 'Database connection failed. Please try again later.'}), 503

    try:
        cursor = db.cursor(dictionary=True)
        # Check for active parking log for this plate
        cursor.execute("SELECT id FROM parking_logs WHERE plate=%s AND exit_time IS NULL", (plate,))
        existing = cursor.fetchone()
        if existing:
            cursor.close()
            db.close()
            return jsonify({'error': 'This car is already parked and has not exited yet.'}), 409

        # Insert new entry
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

# Vehicle exit endpoint
@app.route('/upload-exit', methods=['POST'])
def upload_exit():
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

    # Run ML plate recognition using process_image_file
    try:
        from LPD2 import process_image_file
        plate = process_image_file(file_path)
        if not plate:
            return jsonify({'error': 'Plate could not be detected.'}), 422
    except Exception as e:
        return jsonify({'error': f'Plate recognition error: {str(e)}'}), 422

    exit_time = datetime.now()
    db = get_db()
    if not db:
        return jsonify({'error': 'Database connection failed. Please try again later.'}), 503

    try:
        cursor = db.cursor(dictionary=True)
        # Find the latest entry for this plate with no exit_time
        cursor.execute("SELECT id, entry_time FROM parking_logs WHERE plate=%s AND exit_time IS NULL ORDER BY entry_time DESC LIMIT 1", (plate,))
        log = cursor.fetchone()
        if not log:
            cursor.close()
            db.close()
            return jsonify({'error': 'No car found for this plate number.'}), 404

        entry_time = log['entry_time']
        duration_min = int((exit_time - entry_time).total_seconds() // 60)
        # Fare logic: under 30 min is free, 30 min or more costs 1000 MMK
        if duration_min < 30:
            fare = 0
        else:
            fare = 1000

        # Update log with exit_time and fare
        cursor.execute("UPDATE parking_logs SET exit_time=%s, fare=%s WHERE id=%s", (exit_time, fare, log['id']))
        db.commit()
        cursor.close()
        db.close()
        return jsonify({
            'plate': plate,
            'status': 'Exit recorded successfully',
            'timestamp': exit_time.strftime('%Y-%m-%d %H:%M:%S'),
            'duration_min': duration_min,
            'fare': f'{fare} MMK'
        })
    except Exception as e:
        return jsonify({'error': 'Database error. Please try again later.'}), 503
    finally:
        try:
            if 'cursor' in locals():
                cursor.close()
            if 'db' in locals():
                db.close()
        except:
            pass

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
                # For active parkings, set exit to null (not '-')
                'exit': log['exit_time'].strftime('%Y-%m-%d %H:%M:%S') if log['exit_time'] else None,
                'duration': f"{log['duration']} min" if log['duration'] else '-',
                'fare': f"{log['fare']} MMK" if log['fare'] is not None else '-'
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