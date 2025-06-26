import os
import json
import asyncio
import httpx
from aiohttp import web


BRIDGE_THREAD_ID = int(os.environ.get("BRIDGE_THREAD_ID"))
TELEGRAM_CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID"))
TELEGRAM_CHAT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

async def handle_get(request):
    return web.Response(text="Hello")

async def handle_post(request):
    try:
        body = await request.read()
        if not body:
            return web.Response(text="Bad Request: No body", status=400)
        
        loaded = json.loads(body)
    except json.JSONDecodeError:
        return web.Response(text="Bad Request: Invalid JSON", status=400)
    
    print(f"Received JSON: {loaded}")
    nickname = loaded.get("sender", {}).get("nickname")
    message = loaded.get("raw_message", None)
    
    if not nickname or not message:
        print(f"Missing nickname or message in the JSON payload: {loaded}")
        return web.Response(text="Bad Request: Missing nickname or message", status=400)
    
    async with httpx.AsyncClient() as client:
        token = TELEGRAM_CHAT_TOKEN
        chat_id = TELEGRAM_CHAT_ID
        
        payload = {
            "chat_id": chat_id,
            "text": f"[{nickname}]: {message}",
            "reply_to_message_id": BRIDGE_THREAD_ID,
        }
        
        response = await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json=payload
        )
        
        print(f"Telegram API response: {response.status_code} {response.reason_phrase}")
    
    return web.Response(text="OK")


async def run(port=int(os.environ.get("PORT", 8881))):
    app = web.Application()
    app.router.add_get('/onebot/v11', handle_get)
    app.router.add_post('/onebot/v11', handle_post)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '', port)
    await site.start()
    
    print(f"Server running on port {port}")
    try:
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        print("Shutting down server...")
    finally:
        await runner.cleanup()


def main():
    asyncio.run(run())
