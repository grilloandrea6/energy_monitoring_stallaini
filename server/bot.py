import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from PIL import Image
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

import config

authenticated_users = set()

def str_to_datetime(str) -> datetime:
    return datetime.strptime(str[:19], '%Y-%m-%d %H:%M:%S')

async def show_commands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message with reply keyboard buttons."""
    print(authenticated_users)
    print("user", update.effective_user)
    keyboard = [
        ["/current_status"],
        ["/stats_3_hours", "/stats_2_days"],
        ["/stats_last_month", "/uptime"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Choose a command:", reply_markup=reply_markup)


async def authenticate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if len(context.args) > 0 and context.args[0] == config.PASSCODE:
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
    query = ("SELECT timestamp, soc, current, temperature FROM battery_data "
             "WHERE timestamp BETWEEN ? AND ?")
    cursor.execute(query, (start_time, end_time))
    data = cursor.fetchall()
    conn.close()

    return data

def generate_plot(data, title):
    """Generate a plot from the data and save it as an image."""
    if not data:
        return None

    timestamps, socs, currents, temperatures = zip(*data)
    
    # Define a figure with 3 subplots
    fig, axes = plt.subplots(3, 1, figsize=(12, 12), sharex=True)

    # Plot Temperature
    axes[0].plot(timestamps, temperatures, label='Temperature (C°)', color='blue')
    axes[0].set_ylabel('Temperature (C°)')
    axes[0].legend()
    axes[0].grid()

    # Plot Current
    axes[1].plot(timestamps, currents, label='Current (A)', color='green')
    axes[1].set_ylabel('Current (A)')
    axes[1].legend()
    axes[1].grid()

    # Plot State of Charge
    axes[2].plot(timestamps, socs, label='State of Charge (%)', color='orange')
    axes[2].set_ylabel('State of Charge (%)')
    axes[2].legend()
    axes[2].grid()

    # Convert string timestamps to formatted strings
    timestamps_formatted = [ts[:16] for ts in timestamps]

    # Format the x-axis to show fewer timestamps
    x_ticks = range(0, len(timestamps_formatted), max(1, len(timestamps_formatted) // 10))  # Display every 1/10th of the points
    axes[2].set_xticks(x_ticks)
    axes[2].set_xticklabels([timestamps_formatted[i] for i in x_ticks], rotation=45, ha='right')

    # Add a common title and adjust layout
    fig.suptitle(title)
    plt.xlabel("Timestamp")
    plt.tight_layout(rect=[0, 0, 1, 0.96])  # Leave space for the suptitle

    # Save the figure
    filename = 'battery_plot.png'
    plt.savefig(filename)
    plt.close()

    return filename

@require_authentication
async def uptime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    timespan = timedelta(days    = 20)
    delta    = timedelta(minutes = 2 )

    data = get_data(timespan)

    ret = ""

    for i in range(len(data) - 1):
        time1 = str_to_datetime(data[i][0])
        time2 = str_to_datetime(data[i + 1][0])
        difference = time2 - time1
        if difference > delta:
            ret += f"No data from {time1} to {time2} ({difference})\n"

    total_time = (str_to_datetime(data[-1][0]) - str_to_datetime(data[0][0])).total_seconds() // 60
    uptime = (len(data) - 1) / total_time
    await update.message.reply_text(ret + f"Uptime: {uptime * 100:.2f}%")
    await show_commands(update, context)


@require_authentication
async def current_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch and display the current battery status."""
    data = get_data(timedelta(minutes=1))  # Last 1 minute for the latest status
    if data:
        timestamp, soc, current, temperature = data[-1]
        await update.message.reply_text(f"Current Status:\n"
                                        f"Timestamp: {timestamp[:16]}\n"
                                        f"State of Charge: {soc}%\n"
                                        f"Current: {current} A\n"
                                        f"Temperature: {temperature} C°")
    else:
        # If no data for the last minute, fetch the most recent data
        conn = sqlite3.connect('battery_data.db')
        cursor = conn.cursor()
        query = "SELECT timestamp, soc, current, temperature FROM battery_data ORDER BY timestamp DESC LIMIT 1"
        cursor.execute(query)
        last_data = cursor.fetchone()
        conn.close()
        
        if last_data:
            timestamp, soc, current, temperature = last_data
            await update.message.reply_text(f"⚠️ No updated data available.\n Displaying the latest available data instead:\n\n"
                                            f"Timestamp: {timestamp[:16]}\n"
                                            f"State of Charge: {soc}%\n"
                                            f"Current: {current} A\n"
                                            f"Temperature: {temperature} C°")
        else:
            await update.message.reply_text("No data available.")
    await show_commands(update, context)

@require_authentication
async def stats_3_hours(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send stats for the last hour."""
    data = get_data(timedelta(hours=3))
    print("len data",len(data))
    if len(data) < 58:
        await update.message.reply_text("⚠️ Some data is missing for the last 3 hours, generating plot with all data I have.")

    filename = generate_plot(data, 'Battery Stats (Last 3 Hours)')
    if filename:
        await update.message.reply_photo(photo=open(filename, 'rb'))    
    else:
        await update.message.reply_text("No data available for the last 3 hours.")
    await show_commands(update, context)

@require_authentication
async def stats_2_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send stats for the last day."""
    data = get_data(timedelta(days=2))
    if len(data) < (60*24)-10:
        await update.message.reply_text("⚠️ Some data is missing for the last 2 days, generating plot with all data I have.")

    filename = generate_plot(data, 'Battery Stats (Last 2 Days)')
    if filename:
        await update.message.reply_photo(photo=open(filename, 'rb'))
    else:
        await update.message.reply_text("No data available for the last 2 days.")
    await show_commands(update, context)

@require_authentication
async def stats_last_month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send stats for the last month."""
    data = get_data(timedelta(days=30))
    if len(data) < (30*60*24)-50:
        await update.message.reply_text("⚠️ Some data is missing for the last month, generating plot with all data I have.")

    filename = generate_plot(data, 'Battery Stats (Last Month)')
    if filename:
        await update.message.reply_photo(photo=open(filename, 'rb'))
    else:
        await update.message.reply_text("No data available for the last month.")
    await show_commands(update, context)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await authenticate(update, context)
    user_id = update.effective_user.id
    
    if user_id in authenticated_users:
        await show_commands(update, context)

def main() -> None:
    application = Application.builder().token(config.BOT_TOKEN).build()

    # Command Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('current_status', current_status))
    application.add_handler(CommandHandler('stats_3_hours', stats_3_hours))
    application.add_handler(CommandHandler('stats_2_days', stats_2_days))
    application.add_handler(CommandHandler('stats_last_month', stats_last_month))
    application.add_handler(CommandHandler('uptime', uptime))
    application.add_handler(CommandHandler('commands', show_commands))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
