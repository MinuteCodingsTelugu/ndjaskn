import os, asyncio, humanize, logging
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode, ChatMemberStatus
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, UserNotParticipant, Forbidden, PeerIdInvalid, ChatAdminRequired
from bot import Bot
from config import *
from database.database import *
from pyrogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from helper_func import encode, decode, get_messages


# Basic logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


app = Client("force_sub_bot", api_id=APP_ID, api_hash=API_HASH, bot_token=TG_BOT_TOKEN)


# Function to handle file deletion
async def delete_files(messages, client, k, enter):
    auto_del = get_auto_del()
    del_timer = get_file_del_timer()
    if auto_del == True:
        await asyncio.sleep(del_timer)  # Wait for the specified duration in config.py

        for msg in messages:
            if msg and msg.chat:  # Ensure msg and chat are not None
                try:
                    await client.delete_messages(chat_id=msg.chat.id, message_ids=[msg.id])
                except Exception as e:
                    print(f"The attempt to delete the media {getattr(msg, 'id', 'Unknown')} was unsuccessful: {e}")
            else:
                print("Encountered an empty or deleted message.")

        # Safeguard against k.command being None or having insufficient parts
        
        command = enter.split(" ")
        command_part = command[1] if len(command) > 1 else None
        
        
        if command_part:
            button_url = f"https://t.me/{client.username}?start={command_part}"
            keyboard = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Get Your File Again!", url=button_url)]
                ]
            )
        else:
            keyboard = None

    # Edit message with the button
    await k.edit_text(
        "<blockquote><b>ᴀʟʟ ᴛʜᴇ ғɪʟᴇ(s) ʜᴀᴠᴇ ʙᴇᴇɴ ᴅᴇʟᴇᴛᴇᴅ ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs 📂</b></blockquote>",
        reply_markup=keyboard
    )


async def get_invite_link(channel_id):
    """Generate an invite link for the channel."""
    if not app.is_connected:
        await app.start()  # Ensures client is started if it isn't

    try:
        # Attempt to create a new invite link
        invite_link_obj = await app.create_chat_invite_link(chat_id=channel_id, creates_join_request=True)
        if invite_link_obj and invite_link_obj.invite_link:
            return invite_link_obj.invite_link
        logger.error(f"No invite link created for channel {channel_id}.")
        return None
    except Exception as e:
        logger.error(f"Could not create invite link for channel {channel_id}: {e}")
        return None


async def check_subscription(client, user_id):
    """Check if a user is subscribed to all required channels."""
    statuses = {}
    fsubs = load_fsubs()
    channel_ids = [fsub['_id'] for fsub in fsubs if isinstance(fsub, dict)]  # Type check added

    for channel_id in channel_ids:
        try:
            user = await client.get_chat_member(channel_id, user_id)
            statuses[channel_id] = user.status
            logger.info(f"User {user_id} status in channel {channel_id}: {user.status}")
        except UserNotParticipant:
            statuses[channel_id] = ChatMemberStatus.BANNED
            logger.info(f"User {user_id} is not a participant of channel {channel_id}.")
        except Forbidden:
            logger.error(f"Bot does not have permission to access channel {channel_id}.")
            statuses[channel_id] = None
        except Exception as e:
            logger.error(f"Error checking subscription status for user {user_id} in channel {channel_id}: {e}")
            statuses[channel_id] = None

    return statuses

def is_user_subscribed(statuses):
    """Determine if the user is subscribed based on their statuses."""
    return all(
        status in {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER} 
        for status in statuses.values() if status is not None
    ) and len(statuses) > 0  # Ensure at least one channel was checked

def force_sub(func):
    """Implement Force Subs using @force_sub before any command function."""
    async def wrapper(client, message):
        SPOILER = get_spoiler()
        msg = await message.reply_photo(caption="<code>Connecting!</code>", photo="plugins/image/fsub.jpg", has_spoiler=SPOILER)
        user_id = message.from_user.id
        
        try:
            fsubs = load_fsubs()  # Load channels from database
            logger.debug(f"Loaded fsubs: {fsubs}")
            await msg.edit_text("<code>Connecting!!</code>")
            await msg.edit_text("<code>Connecting!!!</code>")
            logger.debug(f"Loaded spoiler: {SPOILER}")
            await msg.edit_text("<code>Connecting!</code>")
            logger.info(f"User {user_id} invoked {message.command[0]} command")
            await msg.edit_text("<code>Loading!</code>")
            statuses = await check_subscription(client, user_id)
            logger.debug(f"Subscription statuses for user {user_id}: {statuses}")

            if is_user_subscribed(statuses):
                logger.debug(f"User {user_id} passed the subscription check.")
                await msg.edit_text("<code>Subscription Status: Passed</code>")
                await msg.delete()
                await func(client, message)  # Added await
            else:
                logger.debug(f"User {user_id} failed the subscription check.")
                channels_list = []
                buttons = []
                await msg.edit_text("<code>Loading!!</code>")
                # Collect channels user is not subscribed to and prepare buttons
                for channel in fsubs:
                    channel_id = channel['_id']
                    channel_name = channel['CHANNEL_NAME']

                    if statuses.get(channel_id) in {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}:
                        t = (str(channel_name), "Joined ✅")
                        channels_list.append(t)
                    else:
                        t = (str(channel_name), "Not Joined ❌")
                        channels_list.append(t)
                        link = await get_invite_link(channel_id)  # Attempt to get the invite link
                        if link:
                            buttons.append(InlineKeyboardButton(channel_name, url=link))
                        else:
                            buttons.append(InlineKeyboardButton("Error creating invite link", url="https://t.me/Animes2u"))
                    
                from_link = message.text.split(" ")
                if len(from_link) > 1:
                    try_again_link = f"https://t.me/{client.username}/?start={from_link[1]}"
                    buttons.append(InlineKeyboardButton("Try Again!", url=try_again_link))
                await msg.edit_text("<code>Loading!!!</code>")
                channels_message = (
                "<blockquote><b>Jᴏɪɴ Tʜᴇsᴇ Cʜᴀɴɴᴇʟ(s) ᴛᴏ Aᴄᴄᴇss ᴛʜɪs Bᴏᴛ!</b></blockquote>\n\n" +
                "\n".join(f"<b>{i+1}. {name}</b>\n<b>Status:</b> <code>{userstatus}</code>\n" for i, (name, userstatus) in enumerate(channels_list)) +
                "\n<blockquote><b>Aғᴛᴇʀ ᴊᴏɪɴɪɴɢ ᴀʟʟ ᴄʜᴀɴɴᴇʟs, ᴄʟɪᴄᴋ ᴏɴ ᴛʜᴇ 'Tʀʏ Aɢᴀɪɴ!' ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ.</b></blockquote>"
                )
                logger.debug(f"Channels message: {channels_message}")

                n = 2  # Adjust number of buttons per row
                buttons = [buttons[i:i + n] for i in range(0, len(buttons), n)]
                await msg.edit_text("<code>Subscription Status: Failed</code>")
                if buttons:
                    try:
                        await msg.edit_text(
                            text=channels_message,
                            reply_markup=InlineKeyboardMarkup(buttons)
                        )
                    except Exception as e:
                        logger.error(f"Error editing message with buttons: {e}")
                else:
                    logger.error("No buttons to send. Check the button generation.")
        
        except Exception as e:
            logger.error(f"Error in force_sub decorator: {e}")

    return wrapper


#Commands
@Bot.on_message(filters.command("fsubs") & filters.private)
async def fsublist(client, message):
    user_id = message.from_user.id
    admin_ids = await get_admin_ids()
    
    if user_id in admin_ids:
        fsubs = load_fsubs()
        channel_ids = [fsub['_id'] if isinstance(fsub, dict) else fsub for fsub in fsubs]
        fsublist = str(channel_ids)
        await message.reply(fsublist)

# Variable to keep track of the current operation
current_operation = {}

@Bot.on_message(filters.command("add_fsub") & filters.private)
async def start_add_fsub(client, message):
    user_id = message.from_user.id
    admin_ids = await get_admin_ids()
    
    if user_id in admin_ids:    
        # Start the process by asking for the channel ID
        await message.reply("What is the ID of the channel?")
        
        # Set the current operation for adding a channel
        current_operation[user_id] = {"action": "add_fsub", "step": "awaiting_channel_id"}

@Bot.on_message(filters.command("rm_fsub") & filters.private)
async def start_rm_fsub(client, message):
    user_id = message.from_user.id
    admin_ids = await get_admin_ids()
    
    if user_id in admin_ids:
    
        # Start the process by asking for the channel ID to remove
        await message.reply("What is the ID of the channel to remove?")
        
        # Set the current operation for removing a channel
        current_operation[user_id] = {"action": "rm_fsub", "step": "awaiting_channel_id"}

@Bot.on_message(filters.command("cancel") & filters.private)
async def cancel_command(client, message):
    
    user_id = message.from_user.id
    admin_ids = await get_admin_ids()
    
    if user_id in admin_ids:
    
    # Check if the user is in an active operation
        if user_id in current_operation:
            # Remove the user's operation and send a cancellation message
            del current_operation[user_id]
            await message.reply("The operation has been canceled.")
        else:
            await message.reply("No operation is in progress to cancel.")


@Bot.on_message(filters.private & ~filters.command(['start','users','broadcast','b_link','g_link','ping','my_id','add_sticker','spoiler','add_fsub','rm_fsub','cancel','ban','unban','banlist','s_img','del_timer','f_img','add_admin','rm_admin','auto_del','pbroadcast','sudo','fsubs']))
async def channel_post(client: Client, message: Message):
    user_id = message.from_user.id
    fsubs = load_fsubs()
    channel_ids = [fsub['_id'] for fsub in fsubs]
    admin_ids = await get_admin_ids()
    ban_ids = await get_banned_ids()
    
    if user_id in ban_ids:
        await client.send_message(chat_id=user_id, text="You have been banned from using the bot.")

    elif user_id in admin_ids:
        # Check if the user has an active operation
        if user_id in current_operation:
            action = current_operation[user_id]["action"]
            step = current_operation[user_id]["step"]
            
            # Process for /add_fsub
            if action == "add_fsub":
                if step == "awaiting_channel_id":
                    try:
                        # Convert the input to an integer for the channel ID
                        channel_id = int(message.text)
    
                        # Check if the bot is an admin in the channel
                        bot_user = await client.get_me()
                        bot_status = await client.get_chat_member(channel_id, bot_user.id)
    
                        if bot_status.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}:
                            # Store the channel ID temporarily and move to the next step
                            current_operation[user_id]["channel_id"] = channel_id
                            current_operation[user_id]["step"] = "awaiting_channel_name"
                            await message.reply("Name of the channel?")
                        else:
                            await message.reply("The bot must be an admin in this channel to add it to the fsub list.")
                            del current_operation[user_id]  # Clear the user's operation
                            return
    
                    except ValueError:
                        await message.reply("Please provide a valid integer for the channel ID.")
                
                elif step == "awaiting_channel_name":
                    # Retrieve the channel ID and set the channel name
                    channel_id = current_operation[user_id]["channel_id"]
                    channel_name = message.text
                    
                    # Add the channel ID and name to the FSUBS dictionary
                    #FSUBS[channel_id] = channel_name
                    add_fsub(channel_id, channel_name)
                    
                    # Confirm to the user
                    await message.reply(f"Channel '{channel_name}' (ID: {channel_id}) has been added to the fsub list.")
                    
                    # Clear the user's operation
                    del current_operation[user_id]
                    
                    # Process for /rm_fsub
            elif action == "rm_fsub" and step == "awaiting_channel_id":
                try:
                    # Convert the input to an integer for the channel ID
                    channel_id = int(message.text)
                    
                    # Check if the channel ID exists in FSUBS
                    if channel_id in channel_ids:
                        # Remove the channel from the dictionary
                        #del FSUBS[channel_id]
                        del_fsub(channel_id)
                        await message.reply(f"Channel (ID: {channel_id}) has been removed from the fsub list.")
                    else:
                        await message.reply("The fsub list does not contain that channel ID.")
                    
                    # Clear the user's operation
                    del current_operation[user_id]
                
                except ValueError:
                    await message.reply("Please provide a valid integer for the channel ID.")
                    
        elif user_id in waiting_for_image:
            try:
                img_type = waiting_for_image[user_id]
                
                # Determine the correct file path based on the image type
                if img_type == "start":
                    image_path = "plugins/image/start.jpg"
                elif img_type == "fsub":
                    image_path = "plugins/image/fsub.jpg"
                
                # Delete existing image if it exists
                if os.path.exists(image_path):
                    os.remove(image_path)
        
                # Download the new image
                file_path = await client.download_media(message.photo, file_name="temp_image.jpg")
        
                # Check if the file was successfully downloaded
                if file_path:
                    os.rename(file_path, image_path)  # Rename downloaded file
                    await message.reply("Image received, saved successfully!", quote=True)
                else:
                    await message.reply("Failed to save the image. Please try again.", quote=True)
                
                # Remove user from waiting list
                del waiting_for_image[user_id]
            except:
                # If the user sends a photo without a prompt
                await message.reply("Please use the /s_img or /f_img command first to set an image.")
        
            

        else:
            reply_text = await message.reply_text("Please Wait...!", quote = True)
            try:
                post_message = await message.copy(chat_id = client.db_channel.id, disable_notification=True)
            except FloodWait as e:
                await asyncio.sleep(e.x)
                post_message = await message.copy(chat_id = client.db_channel.id, disable_notification=True)
            except Exception as e:
                print(e)
                await reply_text.edit_text("Something went Wrong..!")
                return
            converted_id = post_message.id * abs(client.db_channel.id)
            string = f"get-{converted_id}"
            base64_string = await encode(string)
            link = f"https://t.me/{client.username}?start={base64_string}"
        
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("📬 Share Link", url=f'https://telegram.me/share/url?url={link}')]])
        
            await reply_text.edit(f"<b>Here is your link</b>\n\n{link}", reply_markup=reply_markup, disable_web_page_preview = True)
        
            if not DISABLE_CHANNEL_BUTTON:
                await post_message.edit_reply_markup(reply_markup)
        
        



@Bot.on_message(filters.command('start') & filters.private)
@force_sub
async def start_command(client: Client, message: Message):
    load_settings()
    SPOILER = get_spoiler()
    auto_del = get_auto_del()
    del_timer = get_file_del_timer()
    get_sticker = get_sticker_id()
    id = message.from_user.id
    ban_ids = await get_banned_ids()
    user_id = message.from_user.id
    
    if not present_user(id):
        try:
            await add_user(id)
        except Exception as e:
            print(f"Error adding user: {e}")
            pass
    
    text = message.text
    if user_id in ban_ids:
        await client.send_message(chat_id=user_id, text="You have been banned from using the bot.")

    elif len(text) > 7:
        try:
            base64_string = text.split(" ", 1)[1]
        except IndexError:
            return

        string = await decode(base64_string)
        argument = string.split("-")
        
        ids = []
        if len(argument) == 3:
            try:
                start = int(int(argument[1]) / abs(client.db_channel.id))
                end = int(int(argument[2]) / abs(client.db_channel.id))
                ids = range(start, end + 1) if start <= end else list(range(start, end - 1, -1))
            except Exception as e:
                print(f"Error decoding IDs: {e}")
                return

        elif len(argument) == 2:
            try:
                ids = [int(int(argument[1]) / abs(client.db_channel.id))]
            except Exception as e:
                print(f"Error decoding ID: {e}")
                return

        temp_msg = await message.reply("Wait A Sec..")
        try:
            messages = await get_messages(client, ids)
        except Exception as e:
            await message.reply_text("Something Went Wrong..!")
            print(f"Error getting messages: {e}")
            return
        finally:
            await temp_msg.delete()

        yugen_msgs = []  # List to keep track of sent messages

        for msg in messages:
            caption = (CUSTOM_CAPTION.format(previouscaption=msg.caption.html if msg.caption else msg.document.file_name) if bool(CUSTOM_CAPTION) and bool(msg.document)
                       else ("" if not msg.caption else msg.caption.html))


            reply_markup = msg.reply_markup if DISABLE_CHANNEL_BUTTON else None

            try:
                copied_msg = await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML, 
                                            reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                yugen_msgs.append(copied_msg)
            except FloodWait as e:
                await asyncio.sleep(e.x)
                copied_msg = await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML, 
                                            reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                yugen_msgs.append(copied_msg)
            except Exception as e:
                print(f"Failed to send message: {e}")
                pass
        
        
        if auto_del == True:
            enter = text
            k = await client.send_message(chat_id=message.from_user.id, 
                                      text=f'<blockquote><b>The file(s) will be deleted in {humanize.naturaldelta(del_timer)}. Forward them to your Saved Messages and start downloading!</b></blockquote>')

        # Schedule the file deletion
            asyncio.create_task(delete_files(yugen_msgs, client, k, enter))
            return

        
    elif id in await get_admins():
        reply_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton('- Mᴀɪɴ Cʜᴀɴɴᴇʟ -', url='https://t.me/Animes2u')
                ],
                [
                    InlineKeyboardButton('- Oɴɢᴏɪɴɢ Aɴɪᴍᴇ -', url='https://t.me/Animes3u')
                ],
                [
                   InlineKeyboardButton("◇ ᴘᴀɪᴅ ᴘʀᴏᴍᴏᴛɪᴏɴs ◇", url='https://t.me/Animes2u_Professor_Bot')
                ],
                [
                   InlineKeyboardButton("⚡ ᴀʙᴏᴜᴛ ᴍᴇ", callback_data = "about"),
                   InlineKeyboardButton("🍁 ᴄʟᴏꜱᴇ", callback_data = "close")
                ]
            ]
        )
        start_sticker = await client.send_sticker(chat_id=message.chat.id, sticker=get_sticker)
        
        
        await client.send_photo(
            chat_id=message.chat.id,
            photo="plugins/image/start.jpg",
            caption=START_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
                    
            ),
            has_spoiler=SPOILER,
            reply_markup=reply_markup
        )
        await asyncio.sleep(settings["stk_del_timer"])
        
        await start_sticker.delete()
        
        return
    else:
        reply_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton('- Mᴀɪɴ Cʜᴀɴɴᴇʟ -', url='https://t.me/Animes2u')
                ],
                [
                   InlineKeyboardButton("⚡ ᴀʙᴏᴜᴛ ᴍᴇ", callback_data = "about"),
                   InlineKeyboardButton("🍁 ᴄʟᴏꜱᴇ", callback_data = "close")
                ]
            ]
        )
        start_sticker = await client.send_sticker(chat_id=message.chat.id, sticker=get_sticker)
        await asyncio.sleep(settings["stk_del_timer"])
        
        
        await client.send_photo(
            chat_id=message.chat.id,
            photo="plugins/image/start.jpg",
            caption=START_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
                    
            ),
            has_spoiler=SPOILER,
            reply_markup=reply_markup
        )
        await start_sticker.delete()
        
        return
        
    

# Assuming ADMINS and SUDO are defined elsewhere
# Dictionary to keep track of users waiting for image input
waiting_for_image = {}

@Bot.on_message(filters.command("s_img") & filters.private)
async def change_start_img(client, message):
    admin_ids = await get_admin_ids()
    user_id = message.from_user.id
    
    if user_id in admin_ids:
        # Prompt the user to send a photo
        await message.reply("Send me any photo to set as the start image.")
        waiting_for_image[message.from_user.id] = "start"  # Mark user as waiting for start image

@Bot.on_message(filters.command("f_img") & filters.private)
async def change_force_img(client, message):
    admin_ids = await get_admin_ids()
    user_id = message.from_user.id
    
    if user_id in admin_ids:
        # Prompt the user to send a photo
        await message.reply("Send me any photo to set as the force image.")
        waiting_for_image[message.from_user.id] = "fsub"  # Mark user as waiting for force image
        
        
if __name__=='__main__':
    asyncio.run(main())
