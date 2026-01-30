# Jamnai Bus Management System

## Project Overview
Jamnai Bus is an intelligent bus management and tracking system that combines IoT hardware integration with web-based management. The system provides real-time bus tracking, automated passenger counting using computer vision, and comprehensive trip management capabilities.

## Key Features
- 🚌 **Real-time Bus Tracking** - Monitor bus locations and routes
- 🎫 **Digital Ticketing System** - Card-based fare collection
- 📊 **Analytics Dashboard** - Trip statistics and passenger insights
- 🤖 **AI-Powered Passenger Counting** - YOLOv5-based vehicle detection
- 🔧 **Hardware Integration** - Raspberry Pi support for IoT devices
- 👥 **Multi-role Management** - Admin, Owner, Bus, and Passenger roles

## Project Structure

### 📁 **Jamnai/** (Main Django Application)
The core web application built with Django framework.

**Key Components:**
- **app/** - Main Django app containing:
  - `models.py` - Database models (User, Route, Stopage, Trip, Schedule, Card, Ticket, Road, ImgNow, Owner)
  - `views.py` - Business logic and API endpoints
  - `analytics_views.py` - Analytics and reporting functionality
  - `enhanced_analytics.py` - Advanced data analysis
  - `forms.py` - Django forms for data input
  - `templates/` - HTML templates
  - `static/` - CSS, JS, and static assets
  
- **Jamnai/** - Django project settings
  - `settings.py` - Configuration with CORS, REST framework setup
  - `urls.py` - URL routing
  - `wsgi.py` / `asgi.py` - Server configurations

- **manage.py** - Django management script
- **db.sqlite3** - SQLite database
- **requirements.txt** - Python dependencies

### 📁 **Model/** (AI/ML Service)
Flask-based microservice for passenger counting using computer vision.

**Files:**
- `app.py` - Flask API server that:
  - Receives bus images via POST requests
  - Counts passengers/vehicles using YOLOv5
  - Sends results to Django backend
  - Manages image uploads with auto-numbering
  
- `count_toycars.py` - YOLOv5 model integration:
  - Custom trained model (`best_one.pt`)
  - Image processing and detection
  - Returns vehicle count and detection results

### 📁 **Pi Code/** (Raspberry Pi Hardware Control)
Python scripts for IoT device control on Raspberry Pi.

**Files:**
- `app.py` - Basic Flask server for image processing
- `servo.py` - Servo motor control (PWM, GPIO)
- `flight.py` - Additional hardware control
- `text.py` / `text2.py` - Text/data processing utilities

## Installation

### Prerequisites
- Python 3.8+
- pip (Python package manager)
- Virtual environment (recommended)
- Raspberry Pi (for hardware features)
- Webcam/Camera (for image capture)

### 1. Clone the Repository
```bash
git clone <repository-url>
cd Jamnai_bus
```

### 2. Set Up Django Application

```bash
cd Jamnai

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser (admin account)
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

The Django app will be available at `http://127.0.0.1:8000/`

### 3. Set Up AI Model Service

```bash
cd ../Model

# Activate virtual environment (create if needed)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install flask torch torchvision pillow requests
pip install yolov5  # or clone ultralytics/yolov5

# Place your trained model
# Ensure 'best_one.pt' is in the Model/ directory

# Run Flask server
python app.py
```

The model service will run on `http://127.0.0.1:5000/`

### 4. Set Up Raspberry Pi Code (Optional)

```bash
cd "../Pi Code"

# On Raspberry Pi, install dependencies
pip install flask pillow RPi.GPIO

# Run the appropriate script
python app.py
# or
python servo.py  # For hardware testing
```

## Configuration

### Django Settings
Edit `Jamnai/Jamnai/settings.py`:
- Update `SECRET_KEY` for production
- Configure `ALLOWED_HOSTS`
- Set up database (default: SQLite)
- Configure CORS settings

### Model API Connection
Edit `Model/app.py`:
```python
TARGET_API_URL = "http://127.0.0.1:8000/setg/"  # Update with your Django URL
```

### Hardware GPIO Pins
Edit `Pi Code/servo.py`:
```python
servo_pin = 17  # Change to your GPIO pin
```

## API Endpoints

### Django Backend
- `/admin/` - Admin dashboard
- `/api/` - REST API endpoints
- `/analytics/` - Analytics views
- `/setg/` - Receive passenger count data

### Model Service
- `POST /upload` - Upload image for counting
  - Form data: `image`, `stopageid`, `roadid`
  - Returns: `{"status": "success", "message": "Counted X toy cars"}`

## Database Models

- **User** - Custom user with roles (Admin/Owner/Bus/Passenger)
- **Stopage** - Bus stop locations
- **Route** - Bus routes with start/end stopages
- **RouteStopage** - Intermediate stops with distances
- **Trip** - Individual bus trips with seat availability
- **Schedule** - Trip timetables
- **Card** - Digital payment cards with balance
- **Ticket** - Journey records with pricing
- **Road** - Road identifiers
- **ImgNow** - Real-time image data with vehicle counts
- **Owner** - Bus ownership relationships

## Technology Stack

- **Backend:** Django 5.0.2, Django REST Framework
- **AI/ML:** PyTorch, YOLOv5, Flask
- **Hardware:** Raspberry Pi, GPIO, PWM (Servo control)
- **Database:** SQLite (development), PostgreSQL (recommended for production)
- **Frontend:** HTML, CSS, JavaScript (templates in Django)

## Usage

1. **Start Django server** (Terminal 1):
   ```bash
   cd Jamnai
   python manage.py runserver
   ```

2. **Start Model service** (Terminal 2):
   ```bash
   cd Model
   python app.py
   ```

3. **Access the application:**
   - Admin: `http://127.0.0.1:8000/admin/`
   - Main app: `http://127.0.0.1:8000/`

4. **Upload images for counting:**
   ```bash
   curl -X POST http://127.0.0.1:5000/upload \
     -F "image=@path/to/image.jpg" \
     -F "stopageid=1" \
     -F "roadid=R001"
   ```

## Development Notes

- The YOLOv5 model requires a GitHub token (configured in `count_toycars.py`)
- Image uploads are stored in `Model/uploads/` with auto-incrementing names
- Servo control uses BCM pin numbering
- CSRF protection is disabled for API endpoints using `@csrf_exempt`

## Security Considerations

⚠️ **For Production:**
- Change `SECRET_KEY` in Django settings
- Set `DEBUG = False`
- Remove hardcoded GitHub tokens
- Use environment variables for sensitive data
- Enable HTTPS
- Configure proper CORS settings
- Use production-grade database (PostgreSQL)

## Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## License

[Specify your license here]

## Support

For issues and questions, please open an issue in the repository.

---

**Last Updated:** January 2026
