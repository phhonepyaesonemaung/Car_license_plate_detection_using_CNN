from flask import Flask, request, jsonify
import mysql.connector
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

app = Flask(__name__)

# MySQL config
db_config = {
	'host': 'localhost',
	'user': 'root',
	'password': 'ppsmisZzz23@!',
	'database': 'parking_db'
}

def get_db():
	return mysql.connector.connect(**db_config)

# Fare calculation constants
BASE_FARE = 20
RATE_PER_MIN = 1


# Secure login route
@app.route('/login', methods=['POST'])
def login():
	username = request.form.get('username')
	password = request.form.get('password')
	db = get_db()
	cursor = db.cursor(dictionary=True)
	cursor.execute("SELECT id, username, password_hash FROM users WHERE username=%s", (username,))
	user = cursor.fetchone()
	cursor.close()
	db.close()
	if user and check_password_hash(user['password_hash'], password):
		# Login successful
		return jsonify({
			'success': True,
			'message': 'Login successful',
			'redirect': '/file_upload.html'  # or '/admin.html' as needed
		})
	else:
		return jsonify({
			'success': False,
			'message': 'Invalid username or password'
		})

@app.route('/upload-entry', methods=['POST'])
def upload_entry():
	# Assume plate is extracted by char seg model
	plate = request.form.get('plate')
	entry_time = datetime.now()
	db = get_db()
	cursor = db.cursor()
	cursor.execute("INSERT INTO parking_logs (plate, entry_time) VALUES (%s, %s)", (plate, entry_time))
	db.commit()
	cursor.close()
	db.close()
	return jsonify({'plate': plate, 'status': 'Entry recorded'})

# Serve frontend HTML files
from flask import render_template

# Home route (redirect to login)
@app.route('/')
def home():
	return render_template('login.html')

# Login page
@app.route('/login.html')
def login_page():
	return render_template('login.html')

# File upload page
@app.route('/file_upload.html')
def file_upload_page():
	return render_template('file_upload.html')

# Logs page
@app.route('/logs.html')
def logs_page():
	return render_template('logs.html')

@app.route('/upload-exit', methods=['POST'])
def upload_exit():
	plate = request.form.get('plate')
	exit_time = datetime.now()
	db = get_db()
	cursor = db.cursor(dictionary=True)
	cursor.execute("SELECT entry_time FROM parking_logs WHERE plate=%s AND exit_time IS NULL ORDER BY entry_time DESC LIMIT 1", (plate,))
	log = cursor.fetchone()
	if not log:
		cursor.close()
		db.close()
		return jsonify({'plate': plate, 'status': 'No entry found'}), 404
	entry_time = log['entry_time']
	duration = (exit_time - entry_time).total_seconds() / 60
	fare = BASE_FARE + RATE_PER_MIN * duration
	cursor.execute("UPDATE parking_logs SET exit_time=%s, fare=%s WHERE plate=%s AND entry_time=%s", (exit_time, fare, plate, entry_time))
	db.commit()
	cursor.close()
	db.close()
	return jsonify({'plate': plate, 'duration(mins)': round(duration, 2), 'fare': round(fare, 2)})

@app.route('/get-logs', methods=['GET'])
def get_logs():
	db = get_db()
	cursor = db.cursor(dictionary=True)
	cursor.execute("SELECT plate, entry_time, exit_time, TIMESTAMPDIFF(MINUTE, entry_time, exit_time) AS duration, fare FROM parking_logs")
	logs = cursor.fetchall()
	cursor.close()
	db.close()
	# Format times for frontend
	for log in logs:
		log['entry'] = log.pop('entry_time').strftime('%Y-%m-%d %H:%M:%S') if log['entry_time'] else '-'
		log['exit'] = log.pop('exit_time').strftime('%Y-%m-%d %H:%M:%S') if log['exit_time'] else '-'
	return jsonify(logs)

@app.route('/search-car', methods=['GET'])
def search_car():
	plate = request.args.get('plate')
	db = get_db()
	cursor = db.cursor(dictionary=True)
	cursor.execute("SELECT plate, entry_time, exit_time, fare FROM parking_logs WHERE plate=%s", (plate,))
	logs = cursor.fetchall()
	cursor.close()
	db.close()
	for log in logs:
		log['entry'] = log.pop('entry_time').strftime('%Y-%m-%d %H:%M:%S') if log['entry_time'] else '-'
		log['exit'] = log.pop('exit_time').strftime('%Y-%m-%d %H:%M:%S') if log['exit_time'] else '-'
	return jsonify(logs)

if __name__ == '__main__':
	app.run(debug=True)
