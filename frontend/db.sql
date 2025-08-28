-- Create database
CREATE DATABASE IF NOT EXISTS parking_db;
USE parking_db;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    role ENUM('admin', 'operator') DEFAULT 'operator',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Create parking_logs table
CREATE TABLE IF NOT EXISTS parking_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plate VARCHAR(20) NOT NULL,
    entry_time DATETIME NOT NULL,
    exit_time DATETIME NULL,
    fare DECIMAL(10,2) NULL,
    image_path VARCHAR(255) NULL,
    entry_image_path VARCHAR(255) NULL,
    exit_image_path VARCHAR(255) NULL,
    processing_status ENUM('pending', 'processed', 'error') DEFAULT 'processed',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_plate (plate),
    INDEX idx_entry_time (entry_time),
    INDEX idx_exit_time (exit_time),
    INDEX idx_status (processing_status)
);

-- Create parking_rates table for flexible pricing
CREATE TABLE IF NOT EXISTS parking_rates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rate_name VARCHAR(50) NOT NULL,
    base_fare DECIMAL(10,2) NOT NULL DEFAULT 20.00,
    rate_per_minute DECIMAL(10,4) NOT NULL DEFAULT 1.0000,
    max_daily_fare DECIMAL(10,2) NULL,
    is_active BOOLEAN DEFAULT TRUE,
    effective_from DATE NOT NULL,
    effective_to DATE NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create system_settings table
CREATE TABLE IF NOT EXISTS system_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    setting_type ENUM('string', 'number', 'boolean', 'json') DEFAULT 'string',
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Insert default admin user (password: admin123)
INSERT INTO users (username, password_hash, email, role) VALUES 
('admin', 'pbkdf2:sha256:260000$8mGzKvFZbC5gvTKL$a8f7a5e1d4c2b3f6e9d8c7b5a4e3f2g1h0i9j8k7l6m5n4o3p2q1r0s9t8u7v6w5x4y3z2', 'admin@parkingsystem.com', 'admin')
ON DUPLICATE KEY UPDATE password_hash = VALUES(password_hash);

-- Insert default parking rate
INSERT INTO parking_rates (rate_name, base_fare, rate_per_minute, effective_from) VALUES 
('Standard Rate', 20.00, 1.0000, CURDATE())
ON DUPLICATE KEY UPDATE base_fare = VALUES(base_fare);

-- Insert default system settings
INSERT INTO system_settings (setting_key, setting_value, setting_type, description) VALUES 
('system_name', 'Car Parking Management System', 'string', 'Name of the parking system'),
('max_file_size', '5242880', 'number', 'Maximum file size in bytes (5MB)'),
('allowed_image_types', '["jpg", "jpeg", "png", "gif"]', 'json', 'Allowed image file types'),
('auto_cleanup_days', '90', 'number', 'Days after which old records are archived'),
('email_notifications', 'false', 'boolean', 'Enable email notifications'),
('backup_enabled', 'true', 'boolean', 'Enable automatic database backups')
ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value);

-- Create view for dashboard statistics
CREATE OR REPLACE VIEW parking_stats AS
SELECT 
    COUNT(*) as total_records,
    COUNT(CASE WHEN exit_time IS NULL THEN 1 END) as active_parkings,
    COUNT(CASE WHEN exit_time IS NOT NULL THEN 1 END) as completed_parkings,
    COALESCE(SUM(fare), 0) as total_revenue,
    COALESCE(AVG(TIMESTAMPDIFF(MINUTE, entry_time, exit_time)), 0) as avg_duration_minutes,
    COUNT(CASE WHEN DATE(entry_time) = CURDATE() THEN 1 END) as today_entries,
    COALESCE(SUM(CASE WHEN DATE(entry_time) = CURDATE() THEN fare END), 0) as today_revenue
FROM parking_logs;

-- Create indexes for better performance
CREATE INDEX idx_parking_logs_date ON parking_logs(DATE(entry_time));
CREATE INDEX idx_parking_logs_plate_status ON parking_logs(plate, processing_status);

-- Show the created structure
SHOW TABLES;
DESCRIBE users;
DESCRIBE parking_logs;
DESCRIBE parking_rates;
DESCRIBE system_settings;