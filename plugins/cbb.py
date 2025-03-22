# (©)Yugen_Bots

from pyrogram import __version__
from bot import Bot
from config import OWNER_ID, HELP_MSG, OWNER
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery


@Bot.on_callback_query()
async def cb_handler(client: Bot, query: CallbackQuery):
    data = query.data  # Fixed non-breaking space issue
    if data == "about":
        abt_msg = f'<b>⟦★⟧ Hi There {query.from_user.mention}</b>!\n' \
                  f'<b>┏━━━━━━━❪❂❫━━━━━━━━</b>\n' \
                  f'◈ <b>Dᴇᴠᴇʟᴏᴘᴇʀ</b>: <b><a href="https://t.me/LuffyDSunGodBot">sʀɪɴɪᴠᴀs</a></b>\n' \
                  f'◈ <b>Oɴɢᴏɪɴɢ Cʜᴀɴɴᴇʟ</b>: <b><a href="https://t.me/animes3u">Oɴɢᴏɪɴɢ Aɴɪᴍᴇ</a></b>\n' \
                  f'◈ <b>Mᴀɪɴ Cʜᴀɴɴᴇʟ</b>: <b><a href="https://t.me/animes2u">Mᴀɪɴ Cʜᴀɴɴᴇʟ</a></b>\n' \
                  f'<b>┗━━━━━━━❪❂❫━━━━━━━━</b>'
        await query.message.edit_text(
            text=abt_msg,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")
                    ]
                ]
            )
        )

    elif data == "help":
        await query.message.edit_text(
            text=HELP_MSG,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")
                    ]
                ]
            )
        )

    elif data == "close":
        await query.message.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
            pass
