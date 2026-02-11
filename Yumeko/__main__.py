import os
import importlib
import asyncio
import shutil
import random
from asyncio import sleep

from pyrogram import idle, filters
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message,
)

from Yumeko import app, log, scheduler
from config import config
from Yumeko.helper.on_start import (
    edit_restart_message,
    clear_downloads_folder,
    notify_startup,
)
from Yumeko.admin.roleassign import ensure_owner_is_hokage
from Yumeko.helper.state import initialize_services
from Yumeko.database import init_db
from Yumeko.decorator.save import save
from Yumeko.decorator.errors import error


MODULES = ["modules", "watchers", "admin", "decorator"]
LOADED_MODULES = {}

STICKER_FILE_ID = random.choice(config.START_STICKER_FILE_ID)


def cleanup():
    for root, dirs, _ in os.walk("."):
        for dir_name in dirs:
            if dir_name == "__pycache__":
                try:
                    shutil.rmtree(os.path.join(root, dir_name))
                except Exception as e:
                    log.warning(f"Failed to delete pycache: {e}")


def load_modules_from_folder(folder_name):
    folder_path = os.path.join(os.path.dirname(__file__), folder_name)
    for filename in os.listdir(folder_path):
        if filename.endswith(".py") and filename != "__init__.py":
            module = importlib.import_module(f"Yumeko.{folder_name}.{filename[:-3]}")
            name = getattr(module, "__module__", None)
            help_text = getattr(module, "__help__", None)
            if name and help_text:
                LOADED_MODULES[name] = help_text


def load_all_modules():
    for folder in MODULES:
        load_modules_from_folder(folder)
    log.info(f"Loaded modules: {', '.join(LOADED_MODULES.keys())}")


# =======================
# Keyboards
# =======================

def get_paginated_buttons(page=1, items_per_page=15):
    modules = sorted(LOADED_MODULES.keys())
    total_pages = max(1, (len(modules) + items_per_page - 1) // items_per_page)

    page = max(1, min(page, total_pages))
    start = (page - 1) * items_per_page
    end = start + items_per_page

    rows = []
    current = modules[start:end]

    buttons = [
        InlineKeyboardButton(m, callback_data=f"help_{i}_{page}")
        for i, m in enumerate(current, start=start)
    ]

    rows.extend([buttons[i:i + 3] for i in range(0, len(buttons), 3)])

    rows.append([
        InlineKeyboardButton("‹", callback_data=f"area_{page - 1 if page > 1 else 1}"),
        InlineKeyboardButton("✖ Close", callback_data="delete"),
        InlineKeyboardButton("›", callback_data=f"area_{page + 1 if page < total_pages else total_pages}"),
    ])

    rows.append([InlineKeyboardButton("↩ Back", callback_data="st_back")])

    return InlineKeyboardMarkup(rows)


def get_main_menu_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ",
                               url=f"https://t.me/{app.me.username}?startgroup=true")],
        [
            InlineKeyboardButton("🤝 Sᴜᴘᴘᴏʀᴛ", url=config.SUPPORT_CHAT_LINK),
            InlineKeyboardButton("👑 ᴏᴡɴᴇʀ", user_id=config.OWNER_ID),
        ],
        [InlineKeyboardButton("Cᴏᴍᴍᴀɴᴅs", callback_data="yumeko_help")],
    ])


# =======================
# CALLBACKS
# =======================

@app.on_callback_query(filters.regex("^st_back$"))
@error
async def cb_start_back(_, q: CallbackQuery):
    await q.answer()
    await q.message.edit(
        text=f"**ʜᴇʏ, {q.from_user.mention(style='md')} [🫧]({config.START_IMG_URL})**\n\n"
             f"**ɪ ᴀᴍ {app.me.mention(style='md')}!**\n\n"
             "<blockquote>⌥ ᴀɴ ᴀᴅᴠᴀɴᴄᴇ & ꜰᴀꜱᴛ ɢʀᴏᴜᴘ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ ʙᴏᴛ ᴡɪᴛʜ ᴀɴɪᴍᴇ ꜰᴇᴀᴛᴜʀᴇꜱ</blockquote>",
        reply_markup=get_main_menu_buttons(),
        invert_media=True,
    )


@app.on_callback_query(filters.regex("^yumeko_help$"))
async def cb_help_menu(_, q: CallbackQuery):
    await q.answer()
    prefixes = " ".join(config.COMMAND_PREFIXES)
    await q.message.edit(
        text=f"**[❖]({config.HELP_IMG_URL})!**\n\n"
             f"🔹 **ᴀᴠᴀɪʟᴀʙʟᴇ ᴘʀᴇғɪxᴇs:** {prefixes}",
        reply_markup=get_paginated_buttons(),
        invert_media=True,
    )


@app.on_callback_query(filters.regex(r"^help_\d+_\d+$"))
async def cb_help_item(_, q: CallbackQuery):
    await q.answer()
    try:
        _, idx, page = q.data.split("_")
        idx = int(idx)
        page = int(page)
        module = sorted(LOADED_MODULES.keys())[idx]
        await q.message.edit(
            text=LOADED_MODULES[module],
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩ Back", callback_data=f"area_{page}")]
            ]),
        )
    except Exception:
        await q.answer("Invalid module", show_alert=True)


@app.on_callback_query(filters.regex(r"^area_\d+$"))
async def cb_pagination(_, q: CallbackQuery):
    await q.answer()
    page = int(q.data.split("_")[1])
    prefixes = " ".join(config.COMMAND_PREFIXES)
    await q.message.edit(
        text=f"**[❖]({config.HELP_IMG_URL})!**\n\n"
             f"🔹 **ᴀᴠᴀɪʟᴀʙʟᴇ ᴘʀᴇғɪxᴇs:** {prefixes}",
        reply_markup=get_paginated_buttons(page),
        invert_media=True,
    )


@app.on_callback_query(filters.regex("^delete$"))
async def cb_delete(_, q: CallbackQuery):
    await q.answer()
    await q.message.delete()


# =======================
# FALLBACK (CRITICAL)
# =======================

@app.on_callback_query()
async def cb_fallback(_, q: CallbackQuery):
    await q.answer("⚠ Button not implemented", show_alert=True)


# =======================
# COMMANDS
# =======================

@app.on_message(filters.command("start", config.COMMAND_PREFIXES) & filters.private)
@error
@save
async def start_cmd(_, m: Message):
    await m.reply_cached_media(STICKER_FILE_ID)
    await m.reply(
        text=f"**ʜᴇʏ, {m.from_user.mention(style='md')}!**",
        reply_markup=get_main_menu_buttons(),
        invert_media=True,
    )


@app.on_message(filters.command("help", config.COMMAND_PREFIXES) & filters.private)
@error
@save
async def help_cmd(_, m: Message):
    prefixes = " ".join(config.COMMAND_PREFIXES)
    await m.reply(
        text=f"**[❖]({config.HELP_IMG_URL})!**\n\n"
             f"🔹 **ᴀᴠᴀɪʟᴀʙʟᴇ ᴘʀᴇғɪxᴇs:** {prefixes}",
        reply_markup=get_paginated_buttons(),
        invert_media=True,
    )


# =======================
# STARTUP
# =======================

if __name__ == "__main__":
    load_all_modules()
    app.start()
    initialize_services()
    ensure_owner_is_hokage()
    edit_restart_message()
    clear_downloads_folder()
    notify_startup()

    asyncio.get_event_loop().run_until_complete(init_db())
    scheduler.start()

    log.info("Bot started successfully.")
    idle()
    cleanup()
    app.stop()
