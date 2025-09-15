
# Car License Plate Detection using CNN


## 🚀 Quick Start (Development & Production)

You only need **Docker Desktop** and the provided `docker-compose.yml` file to start both the backend and the MySQL database.

### 1. Prerequisites
- Install [Docker Desktop](https://www.docker.com/products/docker-desktop) (includes Docker Compose)

### 2. Start the Project (Development)
Open a terminal in the project root (where `docker-compose.yml` is located) and run:

```sh
docker compose up --build
```

This will:
- Build the backend image
- Start a MySQL database and initialize it with the provided SQL file
- Start the backend, which connects to the database automatically

The backend will be available at [http://localhost:5000](http://localhost:5000)

**Default Admin Login:**
- Username: `admin`
- Password: `admin123`

### 3. Build a Standalone Docker Image (Production/Sharing)
After development, you can build a standalone Docker image for the backend:

```sh
docker build -t car-license-plate-backend .
```

#### (Optional) Push to Docker Hub
1. Log in to Docker Hub:
	```sh
	docker login
	```
2. Tag your image (replace <your-username> with your Docker Hub username):
	```sh
	docker tag car-license-plate-backend <your-username>/car-license-plate-backend:latest
	```
3. Push the image:
	```sh
	docker push <your-username>/car-license-plate-backend:latest
	```

### 4. Stopping the Project
Press `Ctrl+C` in the terminal, or run:
```sh
docker compose down
```

## Project Structure
- `backend/` - Python backend code (Flask app)
- `frontend/` - (Optional) Frontend files (HTML, CSS)
- `uploads/` - Uploaded images (not included in Docker image)
- `special_project.session.sql` - MySQL database schema and initial data
- `docker-compose.yml` - Multi-service orchestration (backend + MySQL)
- `Dockerfile` - Backend image build instructions

---
For advanced usage or troubleshooting, see the backend code, Dockerfile, and docker-compose.yml.
