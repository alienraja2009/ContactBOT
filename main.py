import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import config
import database

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = """🌟 Welcome! 🌟
💬 Send me a message, and I’ll instantly forward it to the admins.
🔒 Don’t worry — your identity will remain private and secure.
✨ Think of me as your messenger bird 🕊️ carrying your words safely to the team.
✅ /help for Available commands
"""
    await update.message.reply_text(welcome)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message
    chat = update.effective_chat

    if database.is_blocked(user.id):
        return  # Ignore blocked users

    # Handle replies in group
    if chat.id == config.GROUP_CHAT_ID and message.reply_to_message:
        if message.reply_to_message.from_user.id == context.bot.id:
            text = message.reply_to_message.text or message.reply_to_message.caption or ""
            if '[MSG_ID:' in text:
                msg_id_str = text.split('[MSG_ID:')[1].split(']')[0]
                try:
                    msg_id = int(msg_id_str)
                    msg = database.get_message_by_id(msg_id)
                    if msg:
                        user_id = msg[0]
                        reply_text = message.text or "Media reply"
                        await context.bot.send_message(chat_id=user_id, text=f"Reply from admin:\n{reply_text}")
                        database.mark_replied(msg_id)
                        await update.message.reply_text("Reply sent.")
                    else:
                        await update.message.reply_text("Message not found.")
                except ValueError:
                    pass
        return

    # Handle replies in private
    if chat.type == 'private' and (user.id == config.OWNER_ID or database.is_promoted(user.id)) and message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id:
        text = message.reply_to_message.text or ""
        if '[MSG_ID:' in text:
            msg_id_str = text.split('[MSG_ID:')[1].split(']')[0]
            try:
                msg_id = int(msg_id_str)
                msg = database.get_message_by_id(msg_id)
                if msg:
                    user_id = msg[0]
                    reply_text = message.text or "Media reply"
                    await context.bot.send_message(chat_id=user_id, text=f"Reply from admin:\n{reply_text}")
                    database.mark_replied(msg_id)
                    await update.message.reply_text("Reply sent.")
                else:
                    await update.message.reply_text("Message not found.")
            except ValueError:
                pass
        return

    if user.id == config.OWNER_ID or database.is_promoted(user.id):
        await update.message.reply_text("As owner, use /list to see messages, /set_welcome, /block, /unblock, /stats.")
        return

    user_name = f"@{user.username}" if user.username else (user.first_name if user.first_name else "Unknown")

    text = ""
    photo = None
    doc = None
    if message.text:
        text = message.text
    elif message.photo:
        photo = message.photo[-1]
        text = "Photo sent"
    elif message.document:
        doc = message.document
        text = f"Document: {doc.file_name}"
    else:
        text = "Unsupported message type"

    msg_id = database.save_message(user.id, user_name, text)

    forward_text = f"📩 Incoming Message\n\n👤 User: {user_name} ({user.id})\n💬 Message: {text}\n\n━━━━━━━━━━━━━━━━━━\n🔖 Message ID: {msg_id}"

    if config.GROUP_CHAT_ID:
        if photo:
            await context.bot.send_photo(chat_id=config.GROUP_CHAT_ID, photo=photo.file_id, caption=forward_text)
        elif doc:
            await context.bot.send_document(chat_id=config.GROUP_CHAT_ID, document=doc.file_id, caption=forward_text)
        else:
            await context.bot.send_message(chat_id=config.GROUP_CHAT_ID, text=forward_text)
    else:
        await context.bot.send_message(chat_id=config.OWNER_ID, text=forward_text)

    await update.message.reply_text("✅ Message Sent!\n📨 Your message has been successfully forwarded to the admins.\n⏳ Please wait — they’ll reply to you shortly.\n\n✨ Thank you for reaching out!")

async def list_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (update.effective_user.id == config.OWNER_ID or database.is_promoted(update.effective_user.id)):
        await update.message.reply_text("This command is only for owner and admin.")
        return
    messages = database.get_unreplied_messages()
    if not messages:
        text = "No unreplied messages."
    else:
        text = "Unreplied messages:\n"
        for msg in messages:
            username = f"@{msg[2]}" if msg[2] != "Unknown" else msg[2]
            text += f"ID: {msg[0]}\nUser: {username} ({msg[1]})\nTime: {msg[4]}\nMessage: {msg[3]}\n\n"
    
    if config.GROUP_CHAT_ID:
        await context.bot.send_document(chat_id=config.GROUP_CHAT_ID, document=bytes(text, 'utf-8'), filename='unreplied_messages.txt')
        await update.message.reply_text("List sent to the group as txt file.")
    else:
        await context.bot.send_document(chat_id=update.effective_chat.id, document=bytes(text, 'utf-8'), filename='unreplied_messages.txt')

async def reset_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (update.effective_user.id == config.OWNER_ID or database.is_promoted(update.effective_user.id)):
        await update.message.reply_text("This command is only for owner and admin.")
        return
    # Mark all unreplied messages as replied (reset)
    messages = database.get_unreplied_messages()
    for msg in messages:
        database.mark_replied(msg[0])
    await update.message.reply_text("All unreplied messages have been marked as replied (reset).")

async def reply_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (update.effective_user.id == config.OWNER_ID or database.is_promoted(update.effective_user.id)):
        await update.message.reply_text("This command is only for owner and admin.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /reply <message_id> <reply_text>")
        return
    message_id = int(context.args[0])
    reply_text = ' '.join(context.args[1:])
    msg = database.get_message_by_id(message_id)
    if not msg:
        await update.message.reply_text("Message not found.")
        return
    user_id = msg[0]
    await context.bot.send_message(chat_id=user_id, text=f"Reply from owner:\n{reply_text}")
    database.mark_replied(message_id)
    await update.message.reply_text("Reply sent.")

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (update.effective_user.id == config.OWNER_ID or database.is_promoted(update.effective_user.id)):
        await update.message.reply_text("This command is only for owner and admin.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /set_welcome <welcome message>")
        return
    welcome_text = ' '.join(context.args)
    database.set_setting('welcome_message', welcome_text)
    await update.message.reply_text("Welcome message updated.")

async def block_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (update.effective_user.id == config.OWNER_ID or database.is_promoted(update.effective_user.id)):
        await update.message.reply_text("This command is only for owner and admin.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /block <user_id>")
        return
    try:
        user_id = int(context.args[0])
        database.block_user(user_id)
        await update.message.reply_text(f"User {user_id} blocked.")
    except ValueError:
        await update.message.reply_text("Invalid user ID.")

async def unblock_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (update.effective_user.id == config.OWNER_ID or database.is_promoted(update.effective_user.id)):
        await update.message.reply_text("This command is only for owner and admin.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /unblock <user_id>")
        return
    try:
        user_id = int(context.args[0])
        database.unblock_user(user_id)
        await update.message.reply_text(f"User {user_id} unblocked.")
    except ValueError:
        await update.message.reply_text("Invalid user ID.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (update.effective_user.id == config.OWNER_ID or database.is_promoted(update.effective_user.id)):
        await update.message.reply_text("This command is only for owner and admin.")
        return
    total, unique, unreplied, blocked, admins = database.get_stats()
    text = f"Stats:\nTotal messages: {total}\nUnique users: {unique}\nUnreplied: {unreplied}\nBlocked users: {blocked}\nAdmins: {admins}"
    await update.message.reply_text(text)

async def link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.effective_user.id == config.OWNER_ID or database.is_promoted(update.effective_user.id):
        if not context.args:
            await update.message.reply_text("Usage: /link <user_id>")
            return
        try:
            user_id = int(context.args[0])
            username = database.get_username(user_id)
            if username and username.startswith("@") and username != "@Unknown":
                link = f"https://t.me/{username[1:]}"
            else:
                link = f"tg://user?id={user_id}"
            await update.message.reply_text(f"Profile link: {link}")
        except ValueError:
            await update.message.reply_text("Invalid user ID.")
    else:
        # For users, show their own link
        username = user.username
        if username:
            link = f"https://t.me/{username}"
        else:
            link = f"tg://user?id={user.id}"
            await update.message.reply_text("Please set a username in Telegram settings to get a proper link.")
        await update.message.reply_text(f"Your profile link: {link}")

async def gencode_promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.OWNER_ID:
        await update.message.reply_text("This command is only for owner.")
        return
    duration_days = None
    if context.args:
        try:
            duration_days = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Invalid duration. Usage: /gencode_promote [duration_days]")
            return
    code = database.generate_promo_code(update.effective_user.id, config.OWNER_ID, duration_days)
    if code.startswith("Error:"):
        await update.message.reply_text(code)
    else:
        await update.message.reply_text(f"Generated promo code: {code}")

async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args:
        await update.message.reply_text("Usage: /redeem <code>")
        return
    code = context.args[0]
    if database.redeem_promo_code(code, user.id):
        await update.message.reply_text("Code redeemed! You now have ADMIN✅ features.")
    else:
        await update.message.reply_text("Invalid or already used code.")

async def demote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.OWNER_ID:
        await update.message.reply_text("This command is only for owner.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /demote <user_id>")
        return
    try:
        user_id = int(context.args[0])
        database.demote_user(user_id)
        await update.message.reply_text(f"User {user_id} demoted.")
    except ValueError:
        await update.message.reply_text("Invalid user ID.")

async def mysubscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == config.OWNER_ID:
        status = "Owner"
    elif database.is_promoted(user.id):
        status = "Admin"
    else:
        status = "User"
    await update.message.reply_text(f"Your subscription status: {status}")

async def reset_ids_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.OWNER_ID:
        await update.message.reply_text("This command is only for owner.")
        return
    success = database.reset_message_ids()
    if success:
        await update.message.reply_text("Message IDs have been reset. Next message will start from ID 1.")
    else:
        await update.message.reply_text("Database is currently locked. Please try again later.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == config.OWNER_ID or database.is_promoted(user.id):
        help_text = """Available commands for owner and admin:

-/start - Start the bot
-/list - List unreplied messages (sent as txt file)
-/reset - Reset the list of unreplied messages
-/reply <message_id> <reply_text> - Reply to a message
-/set_welcome <message> - Set welcome message
-/block <user_id> - Block a user
-/unblock <user_id> - Unblock a user
-/stats - Show bot statistics
-/link <user_id> - Get user's profile link
-/redeem <code> Access admin commands
-/mysubscription - Check your subscription status
-/gencode_promote - Generate a promo code for promotion
-/demote <user_id> - Demote a promoted user (owner only)
-/reset_ids - Reset message IDs (owner only)
-/help - Show this help message"""
    else:
        help_text = """Available commands for users:

FOR FULL ACCESS OF COMMANDS REDEEM THE CODE ^_^
-/start - Start the bot
-/link - Get your profile link
-/redeem <code> - Redeem a promo code to access admin commands
-/mysubscription - Check your subscription status
-/help - Show this help message"""
    await update.message.reply_text(help_text)

def main():
    application = Application.builder().token(config.TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", list_messages))
    application.add_handler(CommandHandler("reset", reset_list))
    application.add_handler(CommandHandler("reply", reply_message))
    application.add_handler(CommandHandler("set_welcome", set_welcome))
    application.add_handler(CommandHandler("block", block_user_cmd))
    application.add_handler(CommandHandler("unblock", unblock_user_cmd))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("link", link))
    application.add_handler(CommandHandler("gencode_promote", gencode_promote))
    application.add_handler(CommandHandler("redeem", redeem))
    application.add_handler(CommandHandler("demote", demote_cmd))
    application.add_handler(CommandHandler("mysubscription", mysubscription))
    application.add_handler(CommandHandler("reset_ids", reset_ids_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.Document.ALL, handle_message))
    application.run_polling()

if __name__ == '__main__':
    database.init_db()
    main()
