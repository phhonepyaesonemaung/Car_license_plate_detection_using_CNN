-- Create database
CREATE DATABASE IF NOT EXISTS parking_db;
USE parking_db;

-- Users table (only admin, no role, no email)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Parking logs table (no image_path, fare calculated in backend)
CREATE TABLE IF NOT EXISTS parking_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plate VARCHAR(20) NOT NULL,
    entry_time DATETIME NOT NULL,
    exit_time DATETIME NULL,
    fare DECIMAL(10,2) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_plate (plate),
    INDEX idx_entry_time (entry_time)
);

-- Dashboard view
CREATE OR REPLACE VIEW parking_stats AS
SELECT 
    COUNT(*) as total_records,
    COUNT(CASE WHEN exit_time IS NULL THEN 1 END) as active_parkings,
    COUNT(CASE WHEN exit_time IS NOT NULL THEN 1 END) as completed_parkings,
    COALESCE(AVG(TIMESTAMPDIFF(MINUTE, entry_time, exit_time)), 0) as avg_duration_minutes,
    COALESCE(SUM(fare), 0) as total_revenue,
    COUNT(CASE WHEN DATE(entry_time) = CURDATE() THEN 1 END) as today_entries
FROM parking_logs;