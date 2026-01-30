from flask import Flask, request, jsonify
from count_toycars import count_toy_cars
import os
import uuid
import requests
app = Flask(__name__)
TARGET_API_URL = "http://127.0.0.1:8000/setg/"  
@app.route('/upload', methods=['POST'])
def count():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    file = request.files['image']
    stopageid = request.form.get('stopageid')
    roadid = request.form.get('roadid')
    # Create uploads folder if it doesn't exist
    UPLOAD_DIR = 'uploads'
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    # Get the list of existing files and extract numbers
    existing_files = os.listdir(UPLOAD_DIR)
    existing_numbers = [
        int(f.split('.')[0]) for f in existing_files if f.split('.')[0].isdigit()
    ]
    # Determine the next number
    next_number = max(existing_numbers, default=0) + 1
    # Get the file extension (e.g., .pdf, .jpg)
    _, ext = os.path.splitext(file.filename)
    # New numbered filename
    new_filename = f"{next_number}{ext}"
    filepath = os.path.join(UPLOAD_DIR, new_filename)

    # Save the uploaded file
    file.save(filepath)
    count, _ = count_toy_cars(filepath)
    # os.remove(filepath)  # Clean up after counting
    # Clean up image file
    # os.remove(filepath)
    # Prepare data to send to your Django API
    data = {
        "stopageid": stopageid,
        "roadid": roadid,
        "val": count
    }
    try:
        response = requests.post(TARGET_API_URL, data=data)
        response_data = response.json()
    except Exception as e:
        return jsonify({'error': 'Failed to send data to API', 'details': str(e)}), 500
    response_data = {
        "status": "success",
        "message": f"Counted {count} toy cars",
        "data": data
    }
    return jsonify({
        'toy_car_count': count,
        'api_response': response_data
    })
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
