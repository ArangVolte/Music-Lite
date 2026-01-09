import asyncio
from pyrogram import Client

API_ID = 23688933
API_HASH = " fb36db8f0482a909a320752f7d72abc6"

app = Client(
    ":memory:", 
    api_id=API_ID, 
    api_hash=API_HASH,
    device_model="Laptop (Windows 11)",
    system_version="Desktop/PC",
    app_version="Pyrogram mod"
)
app.is_bot = False

async def main():
    await app.start()
    ss = await app.export_session_string()
    
    text = (
        "**BERHASIL MEMBUAT STRING SESSION**\n\n"
        "**Device:** `Laptop (Windows 11)`\n"
        f"**String:**\n`{ss}`"
    )
    
    await app.send_message("me", text)
    print(f"\nBERHASIL!\n\n{ss}\n")

asyncio.run(main())
