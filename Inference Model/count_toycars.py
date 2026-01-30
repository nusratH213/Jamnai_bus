import os
# Set GitHub token from environment variable for security
# Usage: 
#   Linux/Mac: export GITHUB_TOKEN=your_token_here
#   Windows PowerShell: $env:GITHUB_TOKEN="your_token_here"
# The token is required for PyTorch hub to access YOLOv5 repository

import torch
from PIL import Image

model = torch.hub.load('ultralytics/yolov5', 'custom', path='best_one.pt', force_reload=True, trust_repo=True)
model.cpu()

def count_toy_cars(image_path):
    results = model(image_path)
    toy_cars = results.xyxy[0]
    return len(toy_cars), results
