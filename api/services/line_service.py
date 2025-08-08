# api/services/line_service.py

import httpx
import os

class LineService:
    def __init__(self):
        self.channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

    async def push_text(self, user_id: str, text: str):
        headers = {
            "Authorization": f"Bearer {self.channel_access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "to": user_id,
            "messages": [{
                "type": "text",
                "text": text
            }]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post("https://api.line.me/v2/bot/message/push", headers=headers, json=payload)
            response.raise_for_status()
