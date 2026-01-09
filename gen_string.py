import asyncio
from pyrogram import Client

API_ID = int(input("\nEnter Your API_ID:\n > "))
API_HASH = input("\nEnter Your API_HASH:\n > ")

app = Client(
    "session_android", 
    api_id=API_ID, 
    api_hash=API_HASH,
    device_model="Samsung Galaxy S24 Ultra",
    system_version="Android 14",
    app_version="10.11.1"
)

async def main():
    await app.start()
    ss = await app.export_session_string()
    
    text = (
        "**BERHASIL MEMBUAT STRING SESSION**\n\n"
        "**Device:** `Android (Samsung S24)`\n"
        f"**String:**\n`{ss}`"
    )
    
    await app.send_message("me", text)
    print(f"\nBERHASIL!\n\n{ss}\n")

if __name__ == "__main__":
    asyncio.run(main())
