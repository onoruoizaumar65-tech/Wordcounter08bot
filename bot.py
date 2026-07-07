import os
import logging
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    filters, 
    ContextTypes
)

# ==================== CONFIGURATION ====================
# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from environment variables
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set!")

# Store user data in memory (for Railway deployment)
# Note: This resets on restart. For production with persistent data,
# consider adding a database like PostgreSQL
user_stats = {}

# ==================== HELPER FUNCTIONS ====================
def count_text_statistics(text):
    """Count words, characters, sentences, and other metrics."""
    # Remove extra spaces for accurate counting
    text_cleaned = ' '.join(text.split())
    
    # Word count
    word_count = len(text_cleaned.split()) if text_cleaned else 0
    
    # Character counts
    char_with_spaces = len(text)
    char_without_spaces = len(text.replace(' ', ''))
    
    # Sentence count (split by ., !, ?)
    sentences = re.split(r'[.!?]+', text)
    sentence_count = len([s for s in sentences if s.strip()])
    
    # Paragraph count (split by double newline or multiple spaces)
    paragraphs = [p for p in text.split('\n\n') if p.strip()]
    paragraph_count = len(paragraphs) if paragraphs else 0
    
    # Count digits
    digit_count = sum(1 for char in text if char.isdigit())
    
    # Count special characters (non-alphanumeric, non-space)
    special_count = sum(1 for char in text if not char.isalnum() and not char.isspace())
    
    # Average word length
    avg_word_length = sum(len(word) for word in text_cleaned.split()) / word_count if word_count > 0 else 0
    
    return {
        'word_count': word_count,
        'char_with_spaces': char_with_spaces,
        'char_without_spaces': char_without_spaces,
        'sentence_count': sentence_count,
        'paragraph_count': paragraph_count,
        'digit_count': digit_count,
        'special_count': special_count,
        'avg_word_length': round(avg_word_length, 1)
    }

def format_response(stats, text):
    """Format the response message with emojis and proper formatting."""
    response = (
        f"📊 **Text Analysis Results**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📚 **Words:** {stats['word_count']}\n"
        f"🔤 **Characters (with spaces):** {stats['char_with_spaces']}\n"
        f"📏 **Characters (without spaces):** {stats['char_without_spaces']}\n"
        f"📖 **Sentences:** {stats['sentence_count']}\n"
        f"📑 **Paragraphs:** {stats['paragraph_count']}\n"
        f"🔢 **Digits:** {stats['digit_count']}\n"
        f"✨ **Special Characters:** {stats['special_count']}\n"
        f"📐 **Avg Word Length:** {stats['avg_word_length']} characters\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 **Preview:** {text[:50]}{'...' if len(text) > 50 else ''}"
    )
    
    # Add fun facts based on text length
    if stats['word_count'] == 0:
        response += "\n\n🤔 Empty message! Send me some text to analyze."
    elif stats['word_count'] < 5:
        response += "\n\n✏️ That's a very short message!"
    elif stats['word_count'] < 20:
        response += "\n\n📝 Nice and concise!"
    elif stats['word_count'] < 50:
        response += "\n\n📄 That's a good paragraph!"
    elif stats['word_count'] < 100:
        response += "\n\n📑 That's quite a bit of text!"
    else:
        response += "\n\n📚 Wow, that's a long text! Great job!"
    
    return response

# ==================== COMMAND HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    welcome_text = (
        f"👋 **Hello! I'm Word Counter Bot**\n\n"
        f"I analyze your text and provide detailed statistics.\n\n"
        f"📊 **What I count:**\n"
        f"• Words\n"
        f"• Characters (with & without spaces)\n"
        f"• Sentences\n"
        f"• Paragraphs\n"
        f"• Digits & Special Characters\n"
        f"• Average Word Length\n\n"
        f"📌 **Commands:**\n"
        f"/start - Show this message\n"
        f"/help - Get detailed help\n"
        f"/stats - View your usage statistics\n"
        f"/about - About this bot\n\n"
        f"🚀 **Just send me any text to get started!**"
    )
    
    keyboard = [
        [InlineKeyboardButton("📊 My Stats", callback_data="show_stats")],
        [InlineKeyboardButton("ℹ️ About", callback_data="show_about")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text, 
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = (
        f"❓ **How to Use Word Counter Bot**\n\n"
        f"1️⃣ **Send any text message**\n"
        f"   - I'll automatically analyze it\n"
        f"   - Get detailed statistics instantly\n\n"
        f"2️⃣ **Use Commands**\n"
        f"   • /start - Start the bot\n"
        f"   • /help - Show this help\n"
        f"   • /stats - View your statistics\n"
        f"   • /about - About the bot\n\n"
        f"3️⃣ **Pro Tips**\n"
        f"   • Send long texts for detailed analysis\n"
        f"   • Use the inline buttons for quick actions\n"
        f"   • Check your stats to see total usage\n\n"
        f"💡 **Example:**\n"
        f"Send: `The quick brown fox jumps over the lazy dog.`\n"
        f"I'll count words, characters, sentences, and more!"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command."""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Anonymous"
    
    if user_id not in user_stats:
        user_stats[user_id] = {
            'total_messages': 0,
            'total_words': 0,
            'total_chars': 0,
            'first_use': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
    
    stats = user_stats[user_id]
    
    stats_text = (
        f"📊 **Your Statistics**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **User:** @{username}\n"
        f"📝 **Messages Analyzed:** {stats['total_messages']}\n"
        f"📚 **Total Words:** {stats['total_words']:,}\n"
        f"🔤 **Total Characters:** {stats['total_chars']:,}\n"
        f"📊 **Avg Words/Message:** {stats['total_words'] / stats['total_messages'] if stats['total_messages'] > 0 else 0:.1f}\n"
        f"📅 **First Used:** {stats['first_use']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💪 Keep sending texts to improve your stats!"
    )
    
    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="show_stats")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        stats_text, 
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /about command."""
    about_text = (
        f"ℹ️ **About Word Counter Bot**\n\n"
        f"🤖 **Bot:** @Wordcounter08Bot\n"
        f"📝 **Version:** 2.0.0\n"
        f"⚙️ **Language:** Python 3.11\n"
        f"📦 **Framework:** python-telegram-bot 20.7\n"
        f"🚀 **Hosting:** Railway\n"
        f"💻 **Source Code:** GitHub\n\n"
        f"✨ **Features:**\n"
        f"• Real-time text analysis\n"
        f"• Multiple metrics\n"
        f"• User statistics\n"
        f"• Interactive buttons\n"
        f"• High performance\n\n"
        f"💡 **Created for:** Word counting project\n"
        f"📅 **Last Updated:** July 2026\n\n"
        f"🔗 **Support:** @Wordcounter08Bot on Telegram"
    )
    await update.message.reply_text(about_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages and count words."""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Update user statistics
    if user_id not in user_stats:
        user_stats[user_id] = {
            'total_messages': 0,
            'total_words': 0,
            'total_chars': 0,
            'first_use': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
    
    # Process the text
    stats = count_text_statistics(text)
    
    # Update user stats
    user_stats[user_id]['total_messages'] += 1
    user_stats[user_id]['total_words'] += stats['word_count']
    user_stats[user_id]['total_chars'] += stats['char_without_spaces']
    
    # Format response
    response = format_response(stats, text)
    
    # Add inline buttons for additional actions
    keyboard = [
        [InlineKeyboardButton("📊 My Stats", callback_data="show_stats")],
        [InlineKeyboardButton("🔄 Analyze Another", callback_data="show_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        response, 
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

# ==================== CALLBACK HANDLERS ====================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "show_stats":
        # Show stats
        user_id = query.from_user.id
        username = query.from_user.username or "Anonymous"
        
        if user_id not in user_stats:
            user_stats[user_id] = {
                'total_messages': 0,
                'total_words': 0,
                'total_chars': 0,
                'first_use': datetime.now().strftime('%Y-%m-%d %H:%M')
            }
        
        stats = user_stats[user_id]
        
        stats_text = (
            f"📊 **Your Statistics**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **User:** @{username}\n"
            f"📝 **Messages Analyzed:** {stats['total_messages']}\n"
            f"📚 **Total Words:** {stats['total_words']:,}\n"
            f"🔤 **Total Characters:** {stats['total_chars']:,}\n"
            f"📊 **Avg Words/Message:** {stats['total_words'] / stats['total_messages'] if stats['total_messages'] > 0 else 0:.1f}\n"
            f"📅 **First Used:** {stats['first_use']}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        
        await query.edit_message_text(
            stats_text,
            parse_mode='Markdown'
        )
        
    elif query.data == "show_about":
        about_text = (
            f"ℹ️ **About Word Counter Bot**\n\n"
            f"🤖 **Bot:** @Wordcounter08Bot\n"
            f"📝 **Version:** 2.0.0\n"
            f"⚙️ **Language:** Python 3.11\n"
            f"🚀 **Hosting:** Railway\n"
            f"💻 **Source Code:** GitHub\n\n"
            f"✨ **Features:**\n"
            f"• Real-time text analysis\n"
            f"• Multiple metrics\n"
            f"• User statistics\n"
            f"• Interactive buttons\n\n"
            f"💡 **Send any text to start analyzing!**"
        )
        await query.edit_message_text(
            about_text,
            parse_mode='Markdown'
        )
        
    elif query.data == "show_start":
        welcome_text = (
            f"👋 **Ready to analyze text!**\n\n"
            f"Send me any message and I'll count:\n"
            f"• Words\n"
            f"• Characters\n"
            f"• Sentences\n"
            f"• Paragraphs\n"
            f"• And more!\n\n"
            f"📌 **Commands:** /start, /help, /stats, /about"
        )
        await query.edit_message_text(
            welcome_text,
            parse_mode='Markdown'
        )

# ==================== ERROR HANDLER ====================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors and send a message to the user."""
    logger.error(f"Update {update} caused error: {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Oops! Something went wrong. Please try again later."
            )
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")

# ==================== MAIN FUNCTION ====================
def main():
    """Start the bot."""
    try:
        # Create application
        application = ApplicationBuilder().token(TOKEN).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("about", about_command))
        
        # Add message handler
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Add callback handler
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        # Start bot
        logger.info("🚀 Starting Word Counter Bot...")
        logger.info("🤖 Bot: @Wordcounter08Bot")
        logger.info("📊 Ready to count words!")
        
        # Run the bot
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == '__main__':
    main()
