import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from Yumeko import app
from config import config
from pyrogram.enums import ChatMembersFilter, ChatMemberStatus
from pyrogram.errors import UserNotParticipant

# ─── MongoDB ──────────────────────────────────────────────
fsubdb = MongoClient(config.MONGODB_URI)
forcesub_collection = fsubdb.status_db.status


# ─── SET FORCE SUB ────────────────────────────────────────
@app.on_message(filters.command(["fsub", "forcesub"]) & filters.group)
async def set_forcesub(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    member = await client.get_chat_member(chat_id, user_id)

    # Only group owner or bot owner
    if not (
        member.status == ChatMemberStatus.OWNER
        or user_id == config.OWNER_ID
    ):
        return await message.reply_text(
            "🚫 Only the group owner or bot owner can use this command."
        )

    # Disable force-sub
    if len(message.command) == 2 and message.command[1].lower() in ("off", "disable"):
        forcesub_collection.delete_one({"chat_id": chat_id})
        return await message.reply_text("✅ Force subscription disabled.")

    if len(message.command) != 2:
        return await message.reply_text(
            "Usage:\n`/fsub <channel username or id>`\n`/fsub off`"
        )

    channel_input = message.command[1]

    try:
        channel = await client.get_chat(channel_input)
        channel_id = channel.id
        channel_username = channel.username
        channel_title = channel.title

        # Check bot admin in channel
        bot_id = (await client.get_me()).id
        bot_is_admin = False

        async for m in app.get_chat_members(
            channel_id, filter=ChatMembersFilter.ADMINISTRATORS
        ):
            if m.user and m.user.id == bot_id:
                bot_is_admin = True
                break

        if not bot_is_admin:
            return await message.reply_text(
                "🚫 I must be admin in the channel with **Invite Users** permission."
            )

        # Save config
        forcesub_collection.update_one(
            {"chat_id": chat_id},
            {
                "$set": {
                    "channel_id": channel_id,
                    "channel_username": channel_username,
                }
            },
            upsert=True,
        )

        await message.reply_text(
            f"✅ Force subscription enabled\n\n"
            f"📢 Channel: {channel_title}\n"
            f"🆔 ID: `{channel_id}`"
        )

    except Exception:
        await message.reply_text("❌ Failed to set force subscription.")


# ─── FORCE SUB CHECK ──────────────────────────────────────
async def check_forcesub(client: Client, message: Message):
    data = forcesub_collection.find_one({"chat_id": message.chat.id})
    if not data:
        return True

    # Ignore admins & owner
    try:
        member = await client.get_chat_member(
            message.chat.id, message.from_user.id
        )
        if member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        ):
            return True
    except:
        return True

    # Check channel membership
    try:
        await client.get_chat_member(
            data["channel_id"], message.from_user.id
        )
        return True

    except UserNotParticipant:
        # Delete user message
        try:
            await message.delete()
        except:
            pass

        user_mention = message.from_user.mention
        username = data.get("channel_username")

        channel_mention = f"@{username}" if username else "the channel"

        join_url = (
            f"https://t.me/{username}"
            if username
            else await client.export_chat_invite_link(data["channel_id"])
        )

        warn = await message.reply_text(
            f"Hey {user_mention},\n\n"
            f"You need to join {channel_mention} to chat here.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("➕ Join Channel", url=join_url)]]
            ),
            disable_web_page_preview=True,
        )

        # Auto delete warning after 30 seconds
        await asyncio.sleep(30)
        try:
            await warn.delete()
        except:
            pass

        return False

    except Exception:
        # Never disable force-sub on unknown errors
        return True


# ─── ENFORCER ─────────────────────────────────────────────
@app.on_message(filters.group, group=30)
async def enforce_forcesub(client: Client, message: Message):
    await check_forcesub(client, message)


# ─── MODULE INFO ──────────────────────────────────────────
__MODULE__ = "fsᴜʙ"
__HELP__ = """
/fsub <channel username or id> – Enable force subscription
/fsub off – Disable force subscription
"""
