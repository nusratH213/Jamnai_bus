import os
from channels.generic.websocket import AsyncWebsocketConsumer
from datetime import datetime

class VideoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def receive(self, bytes_data):
        filename = f"video_chunk_{datetime.now().strftime('%H%M%S%f')}.webm"
        with open(f"media/{filename}", "wb") as f:
            f.write(bytes_data)

    async def disconnect(self, close_code):
        pass
