import io
import sys
import traceback
from datetime import datetime

from pyrogram import filters
from Yumeko import app
from config import config
from Yumeko.decorator.errors import error
from Yumeko.decorator.save import save


# -------------------- Async Exec Function --------------------
async def aexec(code, client, message):
    exec(
        "async def __aexec(client, message): "
        + "".join(f"\n {line}" for line in code.split("\n"))
    )
    return await locals()["__aexec"](client, message)


# -------------------- EVAL COMMAND --------------------
@app.on_message(filters.command("eval", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def eval(client, message):

    # -------- PERMISSION CHECK --------
    if message.from_user.id != config.OWNER_ID:
        return await message.reply_text("GAND DE APNI SUPPORT GC ME AAKE")

    # -------- NO INPUT CHECK --------
    if len(message.text.split()) < 2:
        return await message.reply_text("`𝖨𝗇𝗉𝗎𝗍 𝖭𝗈𝗍 𝖥𝗈𝗎𝗇𝖽!`")

    status_message = await message.reply_text("𝖯𝗋𝗈𝖼𝖾𝗌𝗌𝗂𝗇𝗀...")
    cmd = message.text.split(None, 1)[1]
    start = datetime.now()

    reply_to_ = message.reply_to_message or message

    # Redirect stdout & stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    redirected_output = sys.stdout = io.StringIO()
    redirected_error = sys.stderr = io.StringIO()

    exc = None

    # -------- EXECUTION --------
    try:
        await aexec(cmd, client, message)
    except Exception:
        exc = traceback.format_exc()

    stdout = redirected_output.getvalue()
    stderr = redirected_error.getvalue()

    # Restore stdout & stderr
    sys.stdout = old_stdout
    sys.stderr = old_stderr

    # -------- BUILD OUTPUT --------
    if exc:
        evaluation = exc
    elif stderr:
        evaluation = stderr
    elif stdout:
        evaluation = stdout
    else:
        evaluation = "Success"

    end = datetime.now()
    ping = (end - start).microseconds / 1000

    final_output = (
        f"<b>📎 Input</b>: <code>{cmd}</code>\n\n"
        f"<b>📒 Output</b>:\n<code>{evaluation.strip()}</code>\n\n"
        f"<b>✨ Taken Time</b>: {ping}ms</b>"
    )

    # -------- SEND RESULT --------
    if len(final_output) > 4096:
        with io.BytesIO(final_output.encode()) as out_file:
            out_file.name = "eval.txt"
            await reply_to_.reply_document(
                document=out_file, caption=cmd, disable_notification=True
            )
    else:
        await status_message.edit_text(final_output) 
