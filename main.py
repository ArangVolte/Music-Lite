import os
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from unidecode import unidecode
import textwrap
import aiohttp
from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait, MessageNotModified, UserNotParticipant, ChatAdminRequired
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.enums import ParseMode, ChatType, ChatMemberStatus
from pytgcalls import PyTgCalls, filters as fl
from yt_dlp import YoutubeDL
from pytgcalls.types import MediaStream, StreamEnded
from youtubesearchpython import VideosSearch
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

API_ID = int(os.getenv("API_ID")) 
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_STRING = os.getenv("SESSION_STRING")


bot = Client(
    name="music_bot",
    bot_token=BOT_TOKEN,
    in_memory=True,
    workers=4,
    parse_mode=ParseMode.HTML
)

ubot = Client(
    name="user_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True,
    workers=4,
    device_model="Huawei P60 Pro",
    system_version="Android 12",
    app_version="10.5.0"
)

bot.is_bot = True
ubot.is_bot = False
call_py = PyTgCalls(ubot)


queues: Dict[int, List[Dict]] = {}
current_playing: Dict[int, Dict] = {}
search_cache: Dict[int, Dict] = {}
loop_mode: Dict[int, str] = {}
now_playing_msgs: Dict[int, Dict] = {}
progress_tasks: Dict[int, asyncio.Task] = {}
start_times: Dict[int, datetime] = {}
channel_connections: Dict[int, int] = {}
active_cplay: Dict[int, int] = {}  
muted_chats: Dict[int, bool] = {}  


async def is_admin(chat_id: int, user_id: int) -> bool:
    """Check if user is admin in group"""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False

async def gen_thumb(
    title: str, 
    duration: str, 
    requester: str, 
    thumbnail_url: str,
    **kwargs
) -> BytesIO:
    requester = unidecode(requester)
    width, height = 1280, 720
    
    background_raw = None
    if thumbnail_url:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(thumbnail_url, timeout=10) as resp:
                    if resp.status == 200:
                        background_raw = Image.open(BytesIO(await resp.read()))
        except: pass

    if not background_raw:
        background_raw = Image.new('RGB', (width, height), color=(30, 30, 30))

    bg = background_raw.resize((width, height), Image.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=10))
    
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 160))
    bg = bg.convert('RGBA')
    bg = Image.alpha_composite(bg, overlay)
    draw = ImageDraw.Draw(bg)

    def load_font(size):
        try:
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            return ImageFont.load_default()

    font_title = load_font(75)
    font_sub = load_font(35)
    font_time = load_font(30)

    art_size = 400
    album_art = ImageOps.fit(background_raw, (art_size, art_size), centering=(0.5, 0.5))
    
    mask = Image.new('L', (art_size, art_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, art_size, art_size), fill=255)
    
    art_x, art_y = 100, (height - art_size) // 2
    
    bg.paste(album_art, (art_x, art_y), mask)
    draw.ellipse((art_x, art_y, art_x + art_size, art_y + art_size), outline="white", width=10)

    text_x = art_x + art_size + 70
    current_y = 180 
    
    lines = textwrap.wrap(title, width=18)
    for line in lines[:2]:
        draw.text((text_x, current_y), line, fill="white", font=font_title)
        current_y += 85
    
    draw.text((text_x, current_y + 10), f"Requested by {requester}", fill=(200, 200, 200), font=font_sub)

    bar_y = 470
    bar_width = 500
    draw.line((text_x, bar_y, text_x + bar_width, bar_y), fill=(255, 255, 255, 60), width=8)
    draw.line((text_x, bar_y, text_x + 300, bar_y), fill="#FF0000", width=8)
    draw.ellipse((text_x + 300 - 10, bar_y - 10, text_x + 300 + 10, bar_y + 10), fill="#FF0000")
    
    draw.text((text_x, bar_y + 25), "00:00", fill="white", font=font_time)
    draw.text((text_x + bar_width - 70, bar_y + 25), duration, fill="white", font=font_time)

    ctrl_y = 560
    draw.polygon([(text_x + 110, ctrl_y + 20), (text_x + 140, ctrl_y + 5), (text_x + 140, ctrl_y + 35)], fill="white")
    draw.rectangle([text_x + 100, ctrl_y + 5, text_x + 106, ctrl_y + 35], fill="white")

    draw.ellipse((text_x + 190, ctrl_y - 10, text_x + 250, ctrl_y + 50), fill="white")
    draw.polygon([(text_x + 215, ctrl_y + 5), (text_x + 215, ctrl_y + 35), (text_x + 235, ctrl_y + 20)], fill="black")

    draw.polygon([(text_x + 300, ctrl_y + 5), (text_x + 300, ctrl_y + 35), (text_x + 330, ctrl_y + 20)], fill="white")
    draw.rectangle([text_x + 333, ctrl_y + 5, text_x + 339, ctrl_y + 35], fill="white")

    img_byte_arr = BytesIO()
    bg.convert('RGB').save(img_byte_arr, format='JPEG', quality=95)
    img_byte_arr.seek(0)
    return img_byte_arr

async def create_invite_link(chat_id: int) -> Optional[str]:
    try:
        chat = await bot.get_chat(chat_id)
        if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            try:
                return await bot.export_chat_invite_link(chat_id)
            except ChatAdminRequired:
                return None
        return None
    except Exception as e:
        logger.error(f"Error creating invite link: {e}")
        return None


async def auto_join_chat(chat_id: int) -> bool:
    try:
        chat = await ubot.get_chat(chat_id)
        if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            try:
                await ubot.get_chat_member(chat_id, ubot.me.id)
                return True
            except UserNotParticipant:
                invite_link = await create_invite_link(chat_id)
                if invite_link:
                    try:
                        await ubot.join_chat(invite_link)
                        return True
                    except Exception:
                        return False
                return False
        return True
    except Exception as e:
        logger.error(f"Error auto_join_chat: {e}")
        return False


def get_active_chat_id(group_id: int) -> int:
    """Get active chat ID (channel if cplay, group if normal play)"""
    if group_id in active_cplay:
        return active_cplay[group_id]
    return group_id


@call_py.on_update(fl.stream_end())
async def stream_end_handler(_: PyTgCalls, update: StreamEnded):
    chat_id = update.chat_id
    logger.info(f"Stream ended in chat: {chat_id}")
    
    if chat_id in progress_tasks:
        progress_tasks[chat_id].cancel()
        progress_tasks.pop(chat_id, None)
    
    start_times.pop(chat_id, None)
    
    playing_data = current_playing.pop(chat_id, None)
    if playing_data:
        file_path = playing_data.get("url")
        if file_path and os.path.exists(file_path) and not str(file_path).startswith("http"):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Failed to delete file: {e}")
    
    if chat_id in now_playing_msgs:
        try:
            msg_data = now_playing_msgs[chat_id]
            await bot.delete_messages(msg_data['group_id'], msg_data['message_id'])
        except Exception:
            pass
        finally:
            now_playing_msgs.pop(chat_id, None)
    
    await asyncio.sleep(1.5)
    
    if chat_id in queues and len(queues[chat_id]) > 0:
        try:
            await play_next(chat_id)
        except Exception as e:
            logger.error(f"Failed play_next: {e}")
            try:
                await call_py.leave_call(chat_id)
            except Exception:
                pass
    else:
        try:
            await call_py.leave_call(chat_id)
            
            for group_id, channel_id in list(active_cplay.items()):
                if channel_id == chat_id:
                    active_cplay.pop(group_id, None)
        except Exception as e:
            logger.error(f"Error leave_call: {e}")


async def search_youtube(query: str, limit: int = 10) -> List[Dict]:
    try:
        search = VideosSearch(query, limit=limit)
        results = search.result().get("result", [])
        
        videos = []
        for video in results:
            videos.append({
                "title": video.get("title", "ᴛᴀɴᴘᴀ ᴊᴜᴅᴜʟ"),
                "duration": video.get("duration", "ᴛɪᴅᴀᴋ ᴅɪᴋᴇᴛᴀʜᴜɪ"),
                "thumbnail": video.get("thumbnails", [{}])[0].get("url", "") if video.get("thumbnails") else "",
                "link": video.get("link", "")
            })
        return videos
    except Exception as e:
        logger.error(f"Error searching YouTube: {e}")
        return []


def get_search_text(chat_id: int, query: str, page: int = 0) -> str:
    results = search_cache[chat_id]['results']
    items_per_page = 5
    start_idx = page * items_per_page
    current_list = results[start_idx:start_idx + items_per_page]
    
    text = f"🔍 <b>ʜᴀsɪʟ ᴜɴᴛᴜᴋ:</b> <code>{query}</code>\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, res in enumerate(current_list, start=1):
        link = res.get('link', '#')
        title = res['title'][:45]
        text += f"<b>{i}.</b> <a href='{link}'>{title}...</a>\n"
    
    text += f"\n📖 ʜᴀʟᴀᴍᴀɴ: {page + 1}"
    return text


def get_search_keyboard(chat_id: int, page: int = 0) -> InlineKeyboardMarkup:
    results = search_cache[chat_id]['results']
    items_per_page = 5
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    current_list = results[start_idx:end_idx]
    
    keyboard = []
    
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    number_row = []
    for i, _ in enumerate(current_list):
        btn = InlineKeyboardButton(emojis[i], callback_data=f"sel_{start_idx + i}")
        number_row.append(btn)
    
    if number_row:
        keyboard.append(number_row)
    
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ sᴇʙᴇʟᴜᴍɴʏᴀ", callback_data=f"spage_{page-1}"))
    if end_idx < len(results):
        nav.append(InlineKeyboardButton("ʙᴇʀɪᴋᴜᴛɴʏᴀ ➡️", callback_data=f"spage_{page+1}"))
    
    if nav:
        keyboard.append(nav)
    
    keyboard.append([InlineKeyboardButton("❌ ᴛᴜᴛᴜᴘ", callback_data="close_search")])
    
    return InlineKeyboardMarkup(keyboard)


def get_now_playing_keyboard(current_seconds: float, total_seconds: float, active_chat_id: int) -> InlineKeyboardMarkup:
    """Generate now playing control keyboard with progress bar."""
    bar_len = 10
    
    if total_seconds <= 0:
        bar_text = "--:-- ━━━━━━━━━━━━ --:--"
    else:
        progress = min(current_seconds / total_seconds, 1.0)
        filled = int(bar_len * progress)
        
        if filled == 0:
            bar = "🔘" + "━" * (bar_len - 1)
        elif filled == bar_len:
            bar = "━" * (bar_len - 1) + "🔘"
        else:
            bar = "━" * filled + "🔘" + "━" * (bar_len - filled - 1)
        
        def format_time(seconds: float) -> str:
            if seconds < 0:
                return "--:--"
            m, s = divmod(int(seconds), 60)
            h, m = divmod(m, 60)
            if h > 0:
                return f"{h}:{m:02d}:{s:02d}"
            return f"{m:02d}:{s:02d}"
        
        current_time = format_time(current_seconds)
        total_time = format_time(total_seconds)
        bar_text = f"{current_time} {bar} {total_time}"
    
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text=bar_text, callback_data=f"progress_{active_chat_id}")],
        [
            InlineKeyboardButton("⏸ ᴊᴇᴅᴀ", callback_data=f"pause_{active_chat_id}"),
            InlineKeyboardButton("▶️ ʟᴀɴᴊᴜᴛ", callback_data=f"resume_{active_chat_id}"),
            InlineKeyboardButton("⏭ sᴋɪᴘ", callback_data=f"skip_{active_chat_id}")
        ],
        [InlineKeyboardButton("⏹ ʙᴇʀʜᴇɴᴛɪ", callback_data=f"stop_{active_chat_id}")]
    ])


async def update_progress_bar(group_id: int, message_id: int, active_chat_id: int):
    """Task untuk update progress bar di keyboard."""
    try:
        interval = 8
        
        while True:
            await asyncio.sleep(interval)
            
            if active_chat_id not in start_times or active_chat_id not in current_playing:
                break
            
            song_data = current_playing[active_chat_id]
            duration = song_data.get('duration', 0)
            total_seconds = 0
            
            try:
                if isinstance(duration, (int, float)):
                    total_seconds = float(duration)
                elif isinstance(duration, str):
                    parts = duration.split(':')
                    if len(parts) == 3:
                        total_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    elif len(parts) == 2:
                        total_seconds = int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 1:
                        total_seconds = int(parts[0])
            except Exception:
                total_seconds = 0
            
            elapsed = (datetime.now() - start_times[active_chat_id]).total_seconds()
            
            if elapsed >= total_seconds:
                break
            
            try:
                await bot.edit_message_reply_markup(
                    group_id,
                    message_id,
                    reply_markup=get_now_playing_keyboard(elapsed, total_seconds, active_chat_id)
                )
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except MessageNotModified:
                continue
            except Exception as e:
                if "MESSAGE_ID_INVALID" in str(e) or "message to edit not found" in str(e):
                    break
                
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error in update_progress_bar: {e}")


async def play_next(active_chat_id: int):
    try:
        if active_chat_id not in queues or not queues[active_chat_id]:
            
            for group_id, channel_id in list(active_cplay.items()):
                if channel_id == active_chat_id:
                    active_cplay.pop(group_id, None)
            
            if active_chat_id in current_playing:
                del current_playing[active_chat_id]
            if active_chat_id in now_playing_msgs:
                del now_playing_msgs[active_chat_id]
            if active_chat_id in progress_tasks:
                progress_tasks[active_chat_id].cancel()
                del progress_tasks[active_chat_id]
            if active_chat_id in start_times:
                del start_times[active_chat_id]
            
            return
        
        song_data = queues[active_chat_id].pop(0)
        current_playing[active_chat_id] = song_data
        
        group_id = song_data.get('group_id', active_chat_id)
        
        
        duration = song_data.get('duration', 0)
        total_seconds = 0
        
        try:
            if isinstance(duration, (int, float)):
                total_seconds = float(duration)
            elif isinstance(duration, str):
                parts = duration.split(':')
                if len(parts) == 3:
                    total_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                elif len(parts) == 2:
                    total_seconds = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 1:
                    total_seconds = int(parts[0])
        except Exception:
            total_seconds = 0
        
        
        if group_id in muted_chats and muted_chats[group_id]:
            return await play_next(active_chat_id)
        
        
        try:
            stream = MediaStream(
                song_data['url'],
                video_flags=MediaStream.Flags.IGNORE if song_data['stream_type'] == 'audio' else None
            )
            await call_py.play(active_chat_id, stream)
        except Exception as e:
            logger.warning(f"Stream failed: {e}")
            
            if song_data['url'].startswith("http"):
                try:
                    await handle_stream_fallback(active_chat_id, song_data)
                    stream = MediaStream(
                        song_data['url'],
                        video_flags=MediaStream.Flags.IGNORE if song_data['stream_type'] == 'audio' else None
                    )
                    await call_py.play(active_chat_id, stream)
                except Exception as fallback_error:
                    await bot.send_message(group_id, f"❌ ɢᴀɢᴀʟ ᴍᴇᴍᴜᴛᴀʀ: {str(fallback_error)[:100]}")
                    return await play_next(active_chat_id)
            else:
                await bot.send_message(group_id, f"❌ ɢᴀɢᴀʟ ᴍᴇᴍᴜᴛᴀʀ: {str(e)[:100]}")
                return await play_next(active_chat_id)
        
        start_times[active_chat_id] = datetime.now()
        
        
        caption = (
            f"<b>🎵 sᴇᴅᴀɴɢ ᴅɪᴘᴜᴛᴀʀ</b>\n\n"
            f"📌 <b>ᴊᴜᴅᴜʟ:</b> <a href='{song_data['url']}'>{song_data['title']}</a>\n"
            f"👤 <b>ᴘᴇʀᴍɪɴᴛᴀᴀɴ:</b> {song_data['requester']}\n"
            f"🎵 <b>ᴛɪᴘᴇ:</b> {song_data['stream_type'].upper()}"
        )
        
        if active_chat_id in now_playing_msgs:
            try:
                msg_data = now_playing_msgs[active_chat_id]
                await bot.delete_messages(msg_data['group_id'], msg_data['message_id'])
            except Exception:
                pass
        
        if active_chat_id in progress_tasks:
            progress_tasks[active_chat_id].cancel()
        
        status_msg = None
        reply_id = song_data.get('reply_to_message_id')
        
        thumb = await gen_thumb(
            title=song_data['title'],
            duration=str(song_data.get('duration', '0:00')),
            requester=song_data['requester'],
            thumbnail_url=song_data['thumbnail']
            )

        status_msg = await bot.send_photo(
            group_id,
            photo=thumb,
            caption=caption,
            reply_markup=get_now_playing_keyboard(0, total_seconds, active_chat_id),
            reply_to_message_id=reply_id,
            parse_mode=ParseMode.HTML
        )
        """except Exception:
            status_msg = await bot.send_message(
                group_id,
                text=caption,
                reply_markup=get_now_playing_keyboard(0, total_seconds, active_chat_id),
                reply_to_message_id=reply_id,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )"""
        
        now_playing_msgs[active_chat_id] = {
            'message_id': status_msg.id,
            'group_id': group_id,
            'total_seconds': total_seconds,
        }

        progress_tasks[active_chat_id] = asyncio.create_task(
            update_progress_bar(group_id, status_msg.id, active_chat_id)
        )

    except Exception as e:
        logger.error(f"Fatal error in play_next: {e}")


async def handle_stream_fallback(active_chat_id: int, song_data: Dict):
    try:
        url = song_data['url']
        if url.startswith("http"):
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f'downloads/%(id)s.%(ext)s',
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 30,
                'retries': 10,
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
                song_data['url'] = file_path
    except Exception as e:
        logger.error(f"Failed fallback download: {e}")
        raise e


@bot.on_message(filters.command("start") & filters.private)
async def start_private(_, message: Message):
    nama = message.from_user.first_name
    teks = (
        f"ʜᴀʟᴏ <b>{nama}</b>! 👋\n\n"
        "sᴀʏᴀ ᴀᴅᴀʟᴀʜ ʙᴏᴛ ᴍᴜsɪᴋ ʏᴀɴɢ ʙɪsᴀ ᴍᴇᴍᴜᴛᴀʀ ʟᴀɢᴜ ᴅɪ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ɢʀᴜᴘ.\n\n"
        "<b>ᴄᴀʀᴀ ᴘᴇɴɢɢᴜɴᴀᴀɴ:</b>\n"
        "1. ᴛᴀᴍʙᴀʜᴋᴀɴ sᴀʏᴀ ᴋᴇ ɢʀᴜᴘ ᴀɴᴅᴀ.\n"
        "2. ᴊᴀᴅɪᴋᴀɴ sᴀʏᴀ sᴇʙᴀɢᴀɪ ᴀᴅᴍɪɴ.\n"
        "3. ᴋɪʀɪᴍ <code>/play [ᴊᴜᴅᴜʟ ʟᴀɢᴜ]</code> ᴅɪ ɢʀᴜᴘ.\n\n"
        "ᴀɴᴅᴀ ᴊᴜɢᴀ ʙɪsᴀ ʀᴇᴘʟʏ ᴍᴇᴅɪᴀ ᴀᴜᴅɪᴏ ᴅɪ sɪɴɪ ᴜɴᴛᴜᴋ sᴀʏᴀ ᴘʀᴏsᴇs."
    )
    
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ ᴛᴀᴍʙᴀʜᴋᴀɴ ᴋᴇ ɢʀᴜᴘ", url=f"https://t.me/{bot.me.username}?startgroup=true"),
        ],
        [
            InlineKeyboardButton("📖 ᴅᴀғᴛᴀʀ ᴘᴇʀɪɴᴛᴀʜ", callback_data="help_command")
        ]
    ])
    
    await message.reply(
        teks,
        reply_markup=kb,
        parse_mode=ParseMode.HTML
    )


@bot.on_message(filters.command("start") & filters.group)
async def start_group(_, message: Message):
    teks = (
        "✨ <b>ʙᴏᴛ ᴍᴜsɪᴋ ᴀᴋᴛɪғ!</b>\n\n"
        "ɢᴜɴᴀᴋᴀɴ ᴘᴇʀɪɴᴛᴀʜ <code>/play</code> ᴅɪɪᴋᴜᴛɪ ᴊᴜᴅᴜʟ ʟᴀɢᴜ ᴀᴛᴀᴜ ʀᴇᴘʟʏ ᴋᴇ ғɪʟᴇ ᴀᴜᴅɪᴏ ᴜɴᴛᴜᴋ ᴍᴜʟᴀɪ ᴍᴇᴍᴜᴛᴀʀ ᴍᴜsɪᴋ ᴅɪ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ."
    )
    
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📖 ᴅᴀғᴛᴀʀ ᴘᴇʀɪɴᴛᴀʜ", callback_data="help_command")
        ]
    ])
    
    await message.reply(teks, reply_markup=kb, parse_mode=ParseMode.HTML)


@bot.on_message(filters.group & filters.command(["play", "cplay"]))
async def play_command(client, message: Message):
    chat_id = message.chat.id
    req = message.from_user.first_name if message.from_user else "ᴀᴅᴍɪɴ"
    
    is_cplay = message.command[0].lower() == "cplay"
    
    
    if is_cplay:
        linked_channel = channel_connections.get(chat_id)
        if linked_channel:
            active_chat_id = linked_channel
            active_cplay[chat_id] = linked_channel
        else:
            await message.reply_text(
                "❌ <b>ᴛɪᴅᴀᴋ ᴀᴅᴀ ᴄʜᴀɴɴᴇʟ ʏᴀɴɢ ᴛᴇʀʜᴜʙᴜɴɢ.</b>\n"
                "ɢᴜɴᴀᴋᴀɴ /connect [ᴄʜᴀɴɴᴇʟ_ɪᴅ]",
                parse_mode=ParseMode.HTML
            )
            return
    else:
        active_chat_id = chat_id
        active_cplay.pop(chat_id, None)
    
    
    if not await auto_join_chat(active_chat_id):
        await message.reply_text(
            f"❌ <b>ᴜʙᴏᴛ ɢᴀɢᴀʟ ᴊᴏɪɴ.</b>\n"
            f"ᴍᴏʜᴏɴ ᴛᴀᴍʙᴀʜᴋᴀɴ @{ubot.me.username}",
            parse_mode=ParseMode.HTML
        )
        return
    
    if message.reply_to_message:
        target = message.reply_to_message
        if target.audio or target.voice or target.video:
            loading_msg = await message.reply("⏳ <b>ᴍᴇᴍᴘʀᴏsᴇs ᴍᴇᴅɪᴀ...</b>")
            try:
                file_path = await client.download_media(target)
                if target.audio:
                    title = target.audio.title or target.audio.file_name or "ᴀᴜᴅɪᴏ ᴛᴇʟᴇɢʀᴀᴍ"
                    duration = target.audio.duration
                elif target.video:
                    title = target.video.file_name or "ᴠɪᴅᴇᴏ ᴛᴇʟᴇɢʀᴀᴍ"
                    duration = target.video.duration
                else:
                    title = "ᴠᴏɪᴄᴇ ᴍᴇssᴀɢᴇ"
                    duration = target.voice.duration if target.voice else 0
                
                duration = duration or 0
                song_data = {
                    "title": title,
                    "url": file_path,
                    "stream_type": "audio" if not target.video else "video",
                    "requester": req,
                    "duration": duration,
                    "reply_to_message_id": message.id,
                    "group_id": chat_id
                }

                if active_chat_id not in queues:
                    queues[active_chat_id] = []
                queues[active_chat_id].append(song_data)

                if active_chat_id in current_playing:
                    await loading_msg.edit_text(f"✅ <b>ᴅɪᴛᴀᴍʙᴀʜᴋᴀɴ ᴋᴇ ᴀɴᴛʀɪᴀɴ:</b>\n└ {title}")
                else:
                    await loading_msg.edit_text(f"🎵 <b>ᴍᴇᴍᴜʟᴀɪ ᴘᴇᴍᴜᴛᴀʀᴀɴ...</b>")
                    await play_next(active_chat_id)
                return
            except Exception as e:
                await loading_msg.edit_text(f"❌ ɢᴀɢᴀʟ: {e}")
                return
    
    if len(message.command) < 2:
        return await message.reply("❌ ᴍᴀsᴜᴋᴋᴀɴ ᴊᴜᴅᴜʟ ᴀᴛᴀᴜ ʀᴇᴘʟʏ ᴍᴇᴅɪᴀ!")
    
    loading_msg = await message.reply("⏳ <b>ᴍᴇᴍᴘʀᴏsᴇs ᴘᴇʀᴍɪɴᴛᴀᴀɴ...</b>")
    query = " ".join(message.command[1:])
    
    if "youtube.com" in query or "youtu.be" in query:
        try:
            with YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl:
                info = ydl.extract_info(query, download=False)
            search_cache[chat_id] = {
                'direct': info.get("webpage_url", query),
                'title': info.get("title", "ʏᴏᴜᴛᴜʙᴇ"),
                'req': req,
                'duration': info.get("duration_string", "00:00"),
                'thumbnail': info.get("thumbnail", ""),
                'active_chat_id': active_chat_id,
                'group_id': chat_id
            }
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("🎵 ᴀᴜᴅɪᴏ", callback_data="type_audio_direct"),
                InlineKeyboardButton("🎬 ᴠɪᴅᴇᴏ", callback_data="type_video_direct")
            ]])
            await loading_msg.edit_text(f"✅ <b>ʟɪɴᴋ ᴛᴇʀᴅᴇᴛᴇᴋsɪ</b>\n└ <code>{search_cache[chat_id]['title']}</code>", reply_markup=kb)
        except Exception as e:
            await loading_msg.edit_text(f"❌ ɢᴀɢᴀʟ: {e}")
    else:
        results = await search_youtube(query)
        if not results:
            return await loading_msg.edit_text("❌ ᴛɪᴅᴀᴋ ᴅɪᴛᴇᴍᴜᴋᴀɴ.")
        search_cache[chat_id] = {
            'results': results, 
            'req': req, 
            'query': query,
            'active_chat_id': active_chat_id,
            'group_id': chat_id
        }
        await loading_msg.edit_text(
            get_search_text(chat_id, query, 0), 
            reply_markup=get_search_keyboard(chat_id, 0), 
            disable_web_page_preview=True
        )


@bot.on_message(filters.group & filters.command("connect"))
async def connect_command(_, message: Message):
    
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("❌ <b>ʜᴀɴʏᴀ ᴀᴅᴍɪɴ ɢʀᴜᴘ ʏᴀɴɢ ʙɪsᴀ ᴍᴇɴɢɢᴜɴᴀᴋᴀɴ ᴘᴇʀɪɴᴛᴀʜ ɪɴɪ.</b>", parse_mode=ParseMode.HTML)
    
    if len(message.command) < 2:
        return await message.reply_text(
            "❌ <b>ᴘᴇɴɢɢᴜɴᴀᴀɴ:</b> /connect [ᴄʜᴀɴɴᴇʟ_ɪᴅ]\n"
            "ᴄᴏɴᴛᴏʜ: /connect -1001234567890",
            parse_mode=ParseMode.HTML
        )
    
    try:
        channel_id = int(message.command[1])
        channel_connections[message.chat.id] = channel_id
        
        try:
            await bot.get_chat_member(channel_id, bot.me.id)
        except UserNotParticipant:
            return await message.reply_text(
                "⚠️ <b>ʙᴏᴛ ʙᴇʟᴜᴍ ᴊᴏɪɴ ᴋᴇ ᴄʜᴀɴɴᴇʟ.</b>\n"
                "ᴍᴏʜᴏɴ ᴛᴀᴍʙᴀʜᴋᴀɴ ʙᴏᴛ ᴋᴇ ᴄʜᴀɴɴᴇʟ.",
                parse_mode=ParseMode.HTML
            )
        
        await message.reply_text(
            f"✅ <b>ɢʀᴏᴜᴘ ᴛᴇʟᴀʜ ᴛᴇʀʜᴜʙᴜɴɢ ᴋᴇ ᴄʜᴀɴɴᴇʟ:</b> {channel_id}\n"
            "ɢᴜɴᴀᴋᴀɴ /cplay ᴜɴᴛᴜᴋ ᴍᴇᴍᴜᴛᴀʀ ᴍᴜsɪᴋ ᴅɪ ᴄʜᴀɴɴᴇʟ.",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.reply_text(f"❌ ɢᴀɢᴀʟ: {str(e)[:100]}")


@bot.on_message(filters.group & filters.command("disconnect"))
async def disconnect_command(_, message: Message):
    
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("❌ <b>ʜᴀɴʏᴀ ᴀᴅᴍɪɴ ɢʀᴜᴘ ʏᴀɴɢ ʙɪsᴀ ᴍᴇɴɢɢᴜɴᴀᴋᴀɴ ᴘᴇʀɪɴᴛᴀʜ ɪɴɪ.</b>", parse_mode=ParseMode.HTML)
    
    chat_id = message.chat.id
    if chat_id in channel_connections:
        channel_id = channel_connections.pop(chat_id)
        active_cplay.pop(chat_id, None)
        await message.reply_text(
            f"✅ <b>ɢʀᴏᴜᴘ ᴛᴇʟᴀʜ ᴛᴇʀᴘᴜᴛᴜs ᴅᴀʀɪ ᴄʜᴀɴɴᴇʟ:</b> {channel_id}",
            parse_mode=ParseMode.HTML
        )
    else:
        await message.reply_text(
            "❌ <b>ɢʀᴏᴜᴘ ʙᴇʟᴜᴍ ᴛᴇʀʜᴜʙᴜɴɢ ᴋᴇ sᴇᴍʙᴀʀᴀɴɢ ᴄʜᴀɴɴᴇʟ.</b>",
            parse_mode=ParseMode.HTML
        )


@bot.on_message(filters.group & filters.command("skip"))
async def skip_command(_, message: Message):
    chat_id = message.chat.id
    
    
    if not await is_admin(chat_id, message.from_user.id):
        return await message.reply_text("❌ <b>ʜᴀɴʏᴀ ᴀᴅᴍɪɴ ɢʀᴜᴘ ʏᴀɴɢ ʙɪsᴀ ᴍᴇɴɢɢᴜɴᴀᴋᴀɴ ᴘᴇʀɪɴᴛᴀʜ ɪɴɪ.</b>", parse_mode=ParseMode.HTML)
    
    
    active_chat_id = get_active_chat_id(chat_id)
    
    if active_chat_id not in current_playing:
        return await message.reply_text("❌ ᴛɪᴅᴀᴋ ᴀᴅᴀ ʟᴀɢᴜ ʏᴀɴɢ sᴇᴅᴀɴɢ ᴅɪᴘᴜᴛᴀʀ.")
    
    if active_chat_id in progress_tasks:
        progress_tasks[active_chat_id].cancel()
        del progress_tasks[active_chat_id]
    
    if active_chat_id in start_times:
        del start_times[active_chat_id]
    
    if active_chat_id in now_playing_msgs:
        try:
            msg_data = now_playing_msgs[active_chat_id]
            await bot.delete_messages(msg_data['group_id'], msg_data['message_id'])
            del now_playing_msgs[active_chat_id]
        except:
            pass
    
    await asyncio.sleep(1)
    await play_next(active_chat_id)
    await message.reply_text("⏭ <b>ᴅɪʟᴇᴡᴀᴛɪ ᴋᴇ ʟᴀɢᴜ ʙᴇʀɪᴋᴜᴛɴʏᴀ.</b>")


@bot.on_message(filters.group & filters.command("stop"))
async def stop_command(_, message: Message):
    chat_id = message.chat.id
    
    
    if not await is_admin(chat_id, message.from_user.id):
        return await message.reply_text("❌ <b>ʜᴀɴʏᴀ ᴀᴅᴍɪɴ ɢʀᴜᴘ ʏᴀɴɢ ʙɪsᴀ ᴍᴇɴɢɢᴜɴᴀᴋᴀɴ ᴘᴇʀɪɴᴛᴀʜ ɪɴɪ.</b>", parse_mode=ParseMode.HTML)
    
    
    active_chat_id = get_active_chat_id(chat_id)
    
    if active_chat_id in progress_tasks:
        progress_tasks[active_chat_id].cancel()
        del progress_tasks[active_chat_id]
    
    if active_chat_id in start_times:
        del start_times[active_chat_id]
    
    if active_chat_id in queues:
        queues[active_chat_id].clear()
    if active_chat_id in current_playing:
        del current_playing[active_chat_id]
    
    if active_chat_id in now_playing_msgs:
        try:
            msg_data = now_playing_msgs[active_chat_id]
            await bot.delete_messages(msg_data['group_id'], msg_data['message_id'])
            del now_playing_msgs[active_chat_id]
        except:
            pass
    
    try:
        await call_py.leave_call(active_chat_id)
    except:
        pass
    
    await message.reply_text("⏹ <b>ᴅɪʜᴇɴᴛɪᴋᴀɴ ᴅᴀɴ ᴀɴᴛʀɪᴀɴ ᴅɪᴋᴏsᴏɴɢᴋᴀɴ.</b>")


@bot.on_message(filters.group & filters.command("pause"))
async def pause_command(_, message: Message):
    chat_id = message.chat.id
    
    
    if not await is_admin(chat_id, message.from_user.id):
        return await message.reply_text("❌ <b>ʜᴀɴʏᴀ ᴀᴅᴍɪɴ ɢʀᴜᴘ ʏᴀɴɢ ʙɪsᴀ ᴍᴇɴɢɢᴜɴᴀᴋᴀɴ ᴘᴇʀɪɴᴛᴀʜ ɪɴɪ.</b>", parse_mode=ParseMode.HTML)
    
    
    active_chat_id = get_active_chat_id(chat_id)
    
    try:
        await call_py.pause(active_chat_id)
        await message.reply_text("⏸ <b>ᴅɪᴊᴇᴅᴀ.</b>")
    except:
        await message.reply_text("❌ ᴛɪᴅᴀᴋ ᴀᴅᴀ ᴘᴇᴍᴜᴛᴀʀᴀɴ ʏᴀɴɢ ᴀᴋᴛɪғ.")


@bot.on_message(filters.group & filters.command("resume"))
async def resume_command(_, message: Message):
    chat_id = message.chat.id
    
    
    if not await is_admin(chat_id, message.from_user.id):
        return await message.reply_text("❌ <b>ʜᴀɴʏᴀ ᴀᴅᴍɪɴ ɢʀᴜᴘ ʏᴀɴɢ ʙɪsᴀ ᴍᴇɴɢɢᴜɴᴀᴋᴀɴ ᴘᴇʀɪɴᴛᴀʜ ɪɴɪ.</b>", parse_mode=ParseMode.HTML)
    
    
    active_chat_id = get_active_chat_id(chat_id)
    
    try:
        await call_py.resume(active_chat_id)
        await message.reply_text("▶️ <b>ᴅɪʟᴀɴᴊᴜᴛᴋᴀɴ.</b>")
    except:
        await message.reply_text("❌ ᴛɪᴅᴀᴋ ᴀᴅᴀ ᴘᴇᴍᴜᴛᴀʀᴀɴ ʏᴀɴɢ ᴅɪᴊᴇᴅᴀ.")


@bot.on_message(filters.group & filters.command("queue"))
async def queue_command(_, message: Message):
    chat_id = message.chat.id
    
    
    active_chat_id = get_active_chat_id(chat_id)
    
    if active_chat_id not in queues or not queues[active_chat_id]:
        return await message.reply_text("📭 <b>ᴀɴᴛʀɪᴀɴ ᴋᴏsᴏɴɢ.</b>")
    
    now_playing = ""
    if active_chat_id in current_playing:
        now_playing = f"▶️ <b>sᴇᴅᴀɴɢ ᴅɪᴘᴜᴛᴀʀ:</b> {current_playing[active_chat_id]['title']}\n\n"
    
    queue_text = now_playing + "📋 <b>ᴅᴀғᴛᴀʀ ᴀɴᴛʀɪᴀɴ:</b>\n"
    for i, song in enumerate(queues[active_chat_id][:10], 1):
        dur = song.get('duration', 0)
        if isinstance(dur, (int, float)):
            m, s = divmod(int(dur), 60)
            h, m = divmod(m, 60)
            if h > 0:
                dur_str = f"{h}:{m:02d}:{s:02d}"
            else:
                dur_str = f"{m:02d}:{s:02d}"
        else:
            dur_str = str(dur)
        
        queue_text += f"{i}. {song['title']} ({song['stream_type']}) [{dur_str}]\n"
    
    if len(queues[active_chat_id]) > 10:
        queue_text += f"\n...ᴅᴀɴ {len(queues[active_chat_id]) - 10} ʟᴀɢᴜ ʟᴀɪɴɴʏᴀ"
    
    await message.reply_text(queue_text)


@bot.on_message(filters.group & filters.command("volume"))
async def volume_command(_, message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("❌ <b>ʜᴀɴʏᴀ ᴀᴅᴍɪɴ ɢʀᴜᴘ ʏᴀɴɢ ʙɪsᴀ ᴍᴇɴɢɢᴜɴᴀᴋᴀɴ ᴘᴇʀɪɴᴛᴀʜ ɪɴɪ.</b>", parse_mode=ParseMode.HTML)
    
    if len(message.command) < 2:
        return await message.reply_text("ᴄᴏɴᴛᴏʜ: /volume 100")
    
    chat_id = message.chat.id
    active_chat_id = get_active_chat_id(chat_id)
    
    try:
        vol = int(message.command[1])
        if vol < 1 or vol > 200:
            return await message.reply_text("⚠️ <b>ᴠᴏʟᴜᴍᴇ ʜᴀʀᴜs ᴀɴᴛᴀʀᴀ 1-200.</b>", parse_mode=ParseMode.HTML)
        
        await call_py.change_volume_call(active_chat_id, vol)
        await message.reply_text(f"🔊 <b>ᴠᴏʟᴜᴍᴇ:</b> {vol}%")
    except:
        await message.reply_text("❌ ɢᴀɢᴀʟ ᴍᴇɴɢᴜʙᴀʜ ᴠᴏʟᴜᴍᴇ.")


@bot.on_message(filters.group & filters.command("mute"))
async def mute_command(_, message: Message):
    chat_id = message.chat.id
    if not await is_admin(chat_id, message.from_user.id):
        return await message.reply_text("❌ <b>ʜᴀɴʏᴀ ᴀᴅᴍɪɴ ɢʀᴜᴘ ʏᴀɴɢ ʙɪsᴀ ᴍᴇɴɢɢᴜɴᴀᴋᴀɴ ᴘᴇʀɪɴᴛᴀʜ ɪɴɪ.</b>", parse_mode=ParseMode.HTML)
    
    if chat_id in muted_chats and muted_chats[chat_id]:
        return await message.reply_text("🔇 <b>ᴍᴜsɪᴋ sᴜᴅᴀʜ ᴅɪᴍᴜᴛᴇ.</b>", parse_mode=ParseMode.HTML)
    
    muted_chats[chat_id] = True
    
    
    active_chat_id = get_active_chat_id(chat_id)
    try:
        await call_py.mute(active_chat_id)
    except:
        pass
    
    await message.reply_text("🔇 <b>ᴍᴜsɪᴋ ᴅɪᴍᴜᴛᴇ.</b>\nɢᴜɴᴀᴋᴀɴ /unmute ᴜɴᴛᴜᴋ ᴍᴇɴɢᴀᴋᴛɪғᴋᴀɴ ʟᴀɢɪ.", parse_mode=ParseMode.HTML)


@bot.on_message(filters.group & filters.command("unmute"))
async def unmute_command(_, message: Message):
    chat_id = message.chat.id
    if not await is_admin(chat_id, message.from_user.id):
        return await message.reply_text("❌ <b>ʜᴀɴʏᴀ ᴀᴅᴍɪɴ ɢʀᴜᴘ ʏᴀɴɢ ʙɪsᴀ ᴍᴇɴɢɢᴜɴᴀᴋᴀɴ ᴘᴇʀɪɴᴛᴀʜ ɪɴɪ.</b>", parse_mode=ParseMode.HTML)
    
    if chat_id not in muted_chats or not muted_chats[chat_id]:
        return await message.reply_text("🔊 <b>ᴍᴜsɪᴋ sᴜᴅᴀʜ ᴀᴋᴛɪғ.</b>", parse_mode=ParseMode.HTML)
    
    muted_chats[chat_id] = False
    
    
    active_chat_id = get_active_chat_id(chat_id)
    try:
        await call_py.unmute(active_chat_id)
    except:
        pass
    
    await message.reply_text("🔊 <b>ᴍᴜsɪᴋ ᴅɪᴀᴋᴛɪғᴋᴀɴ ʟᴀɢɪ.</b>", parse_mode=ParseMode.HTML)


@bot.on_message(filters.group & filters.command("now"))
async def now_command(_, message: Message):
    chat_id = message.chat.id
    active_chat_id = get_active_chat_id(chat_id)
    
    if active_chat_id not in current_playing:
        return await message.reply_text("❌ ᴛɪᴅᴀᴋ ᴀᴅᴀ ʟᴀɢᴜ ʏᴀɴɢ sᴇᴅᴀɴɢ ᴅɪᴘᴜᴛᴀʀ.")
    
    s = current_playing[active_chat_id]
    
    elapsed = 0
    if active_chat_id in start_times:
        elapsed = (datetime.now() - start_times[active_chat_id]).total_seconds()
    
    def format_time(seconds):
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"
    
    status_text = f"""
▶️ <b>sᴇᴅᴀɴɢ ᴅɪᴘᴜᴛᴀʀ:</b>

📌 <b>ᴊᴜᴅᴜʟ:</b> {s['title']}
🎵 <b>ᴛɪᴘᴇ:</b> {s['stream_type']}
👤 <b>ᴅɪᴍɪɴᴛᴀ ᴏʟᴇʜ:</b> {s['requester']}
⏱ <b>ᴘʀᴏɢʀᴇss:</b> {format_time(elapsed)}
🕐 <b>ᴡᴀᴋᴛᴜ:</b> {datetime.now().strftime('%H:%M:%S')}
"""
    await message.reply_text(status_text)


@bot.on_message(filters.group & filters.command("loop"))
async def loop_command(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("ɢᴜɴᴀᴋᴀɴ: /loop ɴᴏɴᴇ/sɪɴɢʟᴇ/ǫᴜᴇᴜᴇ")
    
    mode = message.command[1].lower()
    if mode not in ['none', 'single', 'queue']:
        return await message.reply_text("ᴍᴏᴅᴇ ᴛɪᴅᴀᴋ ᴠᴀʟɪᴅ. ɢᴜɴᴀᴋᴀɴ: ɴᴏɴᴇ, sɪɴɢʟᴇ, ᴀᴛᴀᴜ ǫᴜᴇᴜᴇ")
    
    loop_mode[message.chat.id] = mode
    await message.reply_text(f"🔄 <b>ᴍᴏᴅᴇ ʟᴏᴏᴘ ᴅɪᴀᴛᴜʀ ᴋᴇ:</b> {mode}")


@bot.on_callback_query()
async def cb_handler(_, cb: CallbackQuery):
    chat_id = cb.message.chat.id
    data = cb.data
    
    if data.startswith("spage_"):
        page = int(data.split("_")[1])
        query = search_cache[chat_id].get('query', '')
        
        try:
            await cb.message.edit_text(
                get_search_text(chat_id, query, page),
                reply_markup=get_search_keyboard(chat_id, page),
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Gagal edit search page: {e}")

    elif data.startswith("sel_"):
        idx = int(data.split("_")[1])
        search_cache[chat_id]['selected_idx'] = idx
        res = search_cache[chat_id]['results'][idx]
        
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🎵 ᴀᴜᴅɪᴏ", callback_data="type_audio"),
            InlineKeyboardButton("🎬 ᴠɪᴅᴇᴏ", callback_data="type_video")
        ]])
        
        try:
            await cb.message.edit_text(
                f"🎵 <b>ᴘɪʟɪʜᴀɴ:</b> {res['title'][:50]}\n\nᴘɪʟɪʜ ғᴏʀᴍᴀᴛ ᴘᴇᴍᴜᴛᴀʀᴀɴ:",
                reply_markup=kb
            )
        except Exception as e:
            logger.error(f"Gagal edit selection: {e}")

    elif data.startswith("type_"):
        m_type = data.split("_")[1]
        is_direct = "direct" in data
        
        if is_direct:
            url = search_cache[chat_id]['direct']
            title = search_cache[chat_id].get('title', 'ʏᴏᴜᴛᴜʙᴇ ʟɪɴᴋ')
            thumb = search_cache[chat_id].get('thumbnail')
            duration = search_cache[chat_id].get('duration', '00:00')
            active_chat_id = search_cache[chat_id].get('active_chat_id', chat_id)
            group_id = search_cache[chat_id].get('group_id', chat_id)
        else:
            idx = search_cache[chat_id].get('selected_idx', 0)
            res = search_cache[chat_id]['results'][idx]
            url = res['link']
            title = res['title']
            thumb = res.get('thumbnail')
            duration = res.get('duration', '00:00')
            active_chat_id = search_cache[chat_id].get('active_chat_id', chat_id)
            group_id = search_cache[chat_id].get('group_id', chat_id)

        song_data = {
            "title": title,
            "url": url,
            "thumbnail": thumb,
            "stream_type": m_type,
            "requester": search_cache[chat_id]['req'],
            "duration": duration,
            "reply_to_message_id": cb.message.reply_to_message.id if cb.message.reply_to_message else None,
            "group_id": group_id
        }

        if active_chat_id not in queues:
            queues[active_chat_id] = []
        queues[active_chat_id].append(song_data)
        
        if active_chat_id in current_playing:
            await cb.message.edit_text(f"✅ <b>ᴅɪᴛᴀᴍʙᴀʜᴋᴀɴ ᴋᴇ ᴀɴᴛʀᴇᴀɴ:</b> {title}")
            await cb.answer(f"✅ ᴅɪᴛᴀᴍʙᴀʜᴋᴀɴ: {title}")
        else:
            await cb.message.edit_text(f"🎵 <b>ᴍᴇᴍᴜʟᴀɪ ᴘᴇᴍᴜᴛᴀʀᴀɴ:</b> {title}")
            await cb.answer(f"🎵 ᴍᴇᴍᴜʟᴀɪ: {title}")
            await play_next(active_chat_id)

    elif data == "close_search":
        try:
            await cb.message.delete()
        except Exception as e:
            logger.error(f"Gagal hapus search message: {e}")
    elif data.startswith("progress_"):
        await cb.answer("⏸ ᴘʀᴏɢʀᴇss ʙᴀʀ ᴍᴜsɪᴋ", show_alert=False)
    elif data.startswith("pause_"):
        try:
            active_chat_id = int(data.split("_")[1])
            await call_py.pause(active_chat_id)
            await cb.answer("⏸ ʟᴀɢᴜ ᴅɪᴊᴇᴅᴀ")
        except Exception as e:
            await cb.answer(f"❌ ᴇʀʀᴏʀ: {str(e)[:50]}", show_alert=True)

    elif data.startswith("resume_"):
        try:
            active_chat_id = int(data.split("_")[1])
            await call_py.resume(active_chat_id)
            await cb.answer("▶️ ʟᴀɢᴜ ᴅɪʟᴀɴᴊᴜᴛᴋᴀɴ")
        except Exception as e:
            await cb.answer(f"❌ ᴇʀʀᴏʀ: {str(e)[:50]}", show_alert=True)

    elif data.startswith("skip_"):
        try:
            active_chat_id = int(data.split("_")[1])
            await cb.answer("⏭ ʟᴀɢᴜ ᴅɪʟᴇᴡᴀᴛɪ")
            
            if active_chat_id in now_playing_msgs:
                try:
                    msg_data = now_playing_msgs[active_chat_id]
                    await bot.delete_messages(msg_data['group_id'], msg_data['message_id'])
                except:
                    pass
                del now_playing_msgs[active_chat_id]
            
            
            class SkipMessage:
                def __init__(self, chat_id):
                    self.chat = type('obj', (object,), {'id': chat_id})
            
            skip_msg = SkipMessage(active_chat_id)
            await skip_command(_, skip_msg)
            
        except Exception as e:
            await cb.answer(f"❌ ᴇʀʀᴏʀ: {str(e)[:50]}", show_alert=True)

    elif data.startswith("stop_"):
        try:
            active_chat_id = int(data.split("_")[1])
            await cb.answer("⏹ ᴘᴇᴍᴜᴛᴀʀᴀɴ ʙᴇʀʜᴇɴᴛɪ")
            
            if active_chat_id in now_playing_msgs:
                try:
                    msg_data = now_playing_msgs[active_chat_id]
                    await bot.delete_messages(msg_data['group_id'], msg_data['message_id'])
                except:
                    pass
                del now_playing_msgs[active_chat_id]

            class StopMessage:
                def __init__(self, chat_id):
                    self.chat = type('obj', (object,), {'id': chat_id})
            
            stop_msg = StopMessage(active_chat_id)
            await stop_command(_, stop_msg)
            
        except Exception as e:
            await cb.answer(f"❌ ᴇʀʀᴏʀ: {str(e)[:50]}", show_alert=True)
    
    elif data == "help_command":
        help_text = (
            "📌 <b>ᴅᴀғᴛᴀʀ ᴘᴇʀɪɴᴛᴀʜ:</b>\n\n"
            "• <code>/play</code> - ᴘᴜᴛᴀʀ ᴍᴜsɪᴋ ᴠɪᴀ ᴊᴜᴅᴜʟ/ʟɪɴᴋ/ʀᴇᴘʟʏ\n"
            "• <code>/cplay</code> - ᴘᴜᴛᴀʀ ᴍᴜsɪᴋ ᴅɪ ᴄʜᴀɴɴᴇʟ ʏᴀɴɢ ᴛᴇʀʜᴜʙᴜɴɢ\n"
            "• <code>/connect</code> - ʜᴜʙᴜɴɢᴋᴀɴ ɢʀᴏᴜᴘ ᴋᴇ ᴄʜᴀɴɴᴇʟ\n"
            "• <code>/disconnect</code> - ᴘᴜᴛᴜs ʜᴜʙᴜɴɢᴀɴ ᴅᴇɴɢᴀɴ ᴄʜᴀɴɴᴇʟ\n"
            "• <code>/skip</code> - ʟᴇᴡᴀᴛɪ ʟᴀɢᴜ\n"
            "• <code>/stop</code> - ʜᴇɴᴛɪᴋᴀɴ ᴍᴜsɪᴋ\n"
            "• <code>/pause</code> - ᴊᴇᴅᴀ ᴍᴜsɪᴋ\n"
            "• <code>/resume</code> - ʟᴀɴᴊᴜᴛᴋᴀɴ ᴍᴜsɪᴋ\n"
            "• <code>/queue</code> - ʟɪʜᴀᴛ ᴀɴᴛʀᴇᴀɴ\n"
            "• <code>/now</code> - ʟɪʜᴀᴛ ʟᴀɢᴜ ʏᴀɴɢ sᴇᴅᴀɴɢ ᴅɪᴘᴜᴛᴀʀ\n"
            "• <code>/volume</code> - ᴀᴛᴜʀ ᴠᴏʟᴜᴍᴇ (1-200)\n"
            "• <code>/mute</code> - ᴍᴜᴛᴇ ᴍᴜsɪᴋ\n"
            "• <code>/unmute</code> - ᴜɴᴍᴜᴛᴇ ᴍᴜsɪᴋ\n"
            "• <code>/loop</code> - ᴀᴛᴜʀ ᴍᴏᴅᴇ ʟᴏᴏᴘ (ɴᴏɴᴇ/sɪɴɢʟᴇ/ǫᴜᴇᴜᴇ)"
        )
        try:
            await cb.message.edit_text(
                help_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ ᴛᴜᴛᴜᴘ", callback_data="close_search")]
                ])
            )
        except Exception as e:
            logger.error(f"Gagal edit help message: {e}")


async def main():
    try:
        await bot.start()
        await ubot.start()
        await call_py.start()
        
        logger.info("✅ Bot dan PyTgCalls sudah aktif")
        print("\n" + "="*50)
        print("🤖 Bot Music Berhasil Diaktifkan!")
        print(f"👤 Bot: @{bot.me.username}")
        print(f"👤 Userbot: @{ubot.me.username}")
        print("="*50 + "\n")
        
        await idle()
        
    except Exception as e:
        logger.error(f"Error utama: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if bot.is_connected:
            await bot.stop()
        if ubot.is_connected:
            await ubot.stop()
        

if __name__ == "__main__":
    if not all([API_ID, API_HASH, BOT_TOKEN, SESSION_STRING]):
        print("❌ Error: Mohon isi semua credential!")
        exit(1)
    
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
