import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from PIL import Image
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# Configurations
BOT_TOKEN = "7577285779:AAGcrtYL_2YaifSPZz9d-O2vKjEY_jSGzpA"
PASSCODE = "ciaociao"
authenticated_users = set()

async def show_commands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message with reply keyboard buttons."""
    keyboard = [
        ["/current_status"],
        ["/stats_last_hour", "/stats_last_day"],
        ["/stats_last_month"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Choose a command:", reply_markup=reply_markup)


async def authenticate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if len(context.args) > 0 and context.args[0] == PASSCODE:
        authenticated_users.add(user_id)
        await update.message.reply_text("Authentication successful!")
    else:
        await update.message.reply_text("Invalid passcode.")

def is_authenticated(update: Update) -> bool:
    return update.effective_user.id in authenticated_users

def require_authentication(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_authenticated(update):
            await update.message.reply_text("You must authenticate first. Use /start <passcode>.")
            return
        await func(update, context)
    return wrapper

def get_data(period: timedelta):
    """Fetch data from the SQLite database for the given time period."""
    conn = sqlite3.connect('battery_data.db')
    cursor = conn.cursor()

    end_time = datetime.now()
    start_time = end_time - period
    query = ("SELECT timestamp, voltage, current, soc FROM battery_data "
             "WHERE timestamp BETWEEN ? AND ?")
    cursor.execute(query, (start_time, end_time))
    data = cursor.fetchall()
    conn.close()

    return data

def generate_plot(data, title):
    """Generate a plot from the data and save it as an image."""
    if not data:
        return None

    timestamps, voltages, currents, socs = zip(*data)
    plt.figure(figsize=(12, 8))
    plt.plot(timestamps, voltages, label='Voltage (V)', color='blue')
    plt.plot(timestamps, currents, label='Current (A)', color='green')
    plt.plot(timestamps, socs, label='State of Charge (%)', color='orange')
    plt.xlabel('Timestamp')
    plt.ylabel('Values')
    plt.title(title)
    plt.legend()
    plt.grid()
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    filename = 'battery_plot.png'
    plt.savefig(filename)
    plt.close()

    return filename

@require_authentication
async def current_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch and display the current battery status."""
    data = get_data(timedelta(minutes=1))  # Last 1 minute for the latest status
    if data:
        timestamp, voltage, current, soc = data[-1]
        await update.message.reply_text(f"Current Status:\n"
                                        f"Timestamp: {timestamp}\n"
                                        f"Voltage: {voltage} V\n"
                                        f"Current: {current} A\n"
                                        f"State of Charge: {soc}%")
    else:
        await update.message.reply_text("No data available.")
    await show_commands(update, context)

@require_authentication
async def stats_last_hour(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send stats for the last hour."""
    data = get_data(timedelta(hours=1))
    filename = generate_plot(data, 'Battery Stats (Last Hour)')
    if filename:
        await update.message.reply_photo(photo=open(filename, 'rb'))    
    else:
        await update.message.reply_text("No data available for the last hour.")
    await show_commands(update, context)

@require_authentication
async def stats_last_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send stats for the last day."""
    data = get_data(timedelta(days=1))
    filename = generate_plot(data, 'Battery Stats (Last Day)')
    if filename:
        await update.message.reply_photo(photo=open(filename, 'rb'))
    else:
        await update.message.reply_text("No data available for the last day.")
    await show_commands(update, context)

@require_authentication
async def stats_last_month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send stats for the last month."""
    data = get_data(timedelta(days=30))
    filename = generate_plot(data, 'Battery Stats (Last Month)')
    if filename:
        await update.message.reply_photo(photo=open(filename, 'rb'))
    else:
        await update.message.reply_text("No data available for the last month.")
    await show_commands(update, context)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await authenticate(update, context)
    await show_commands(update, context)

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    # Command Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('current_status', current_status))
    application.add_handler(CommandHandler('stats_last_hour', stats_last_hour))
    application.add_handler(CommandHandler('stats_last_day', stats_last_day))
    application.add_handler(CommandHandler('stats_last_month', stats_last_month))
    application.add_handler(CommandHandler('commands', show_commands))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
