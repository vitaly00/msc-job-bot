import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, ConversationHandler

TOKEN = "INSERISCI_IL_TUO_TOKEN"

# DB setup
conn = sqlite3.connect("jobs.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    location TEXT,
    terminal TEXT,
    start TEXT,
    end TEXT,
    status TEXT
)
""")
conn.commit()

# Stati conversazione
NAME, LOCATION, TERMINAL, START, END = range(5)

# START MENU
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Crea lavoro", callback_data="create")],
        [InlineKeyboardButton("📊 Lavori in corso", callback_data="list")],
        [InlineKeyboardButton("📄 Lista nomi", callback_data="names")]
    ]
    await update.message.reply_text("Menu", reply_markup=InlineKeyboardMarkup(keyboard))

# CREA LAVORO
async def create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Nome nave (es: MSC ANNA):")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.upper()
    if not name.startswith("MSC"):
        await update.message.reply_text("Deve iniziare con MSC")
        return NAME
    context.user_data["name"] = name

    keyboard = [
        [InlineKeyboardButton("VLC", callback_data="VLC"),
         InlineKeyboardButton("BNC", callback_data="BNC")]
    ]
    await update.message.reply_text("Location:", reply_markup=InlineKeyboardMarkup(keyboard))
    return LOCATION

async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data["location"] = update.callback_query.data

    keyboard = [
        [InlineKeyboardButton("MSC", callback_data="MSC"),
         InlineKeyboardButton("CSP", callback_data="CSP")]
    ]
    await update.callback_query.message.reply_text("Terminal:", reply_markup=InlineKeyboardMarkup(keyboard))
    return TERMINAL

async def get_terminal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data["terminal"] = update.callback_query.data
    await update.callback_query.message.reply_text("Data inizio (es: 01/05 10:00):")
    return START

async def get_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["start"] = update.message.text
    await update.message.reply_text("Data fine:")
    return END

async def get_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["end"] = update.message.text

    cursor.execute("""
    INSERT INTO jobs (name, location, terminal, start, end, status)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        context.user_data["name"],
        context.user_data["location"],
        context.user_data["terminal"],
        context.user_data["start"],
        context.user_data["end"],
        "in_progress"
    ))
    conn.commit()

    await update.message.reply_text("✔️ Lavoro creato")
    return ConversationHandler.END

# LISTA LAVORI
async def list_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    cursor.execute("SELECT name, start FROM jobs WHERE status='in_progress' ORDER BY start ASC")
    jobs = cursor.fetchall()

    if not jobs:
        text = "Nessun lavoro"
    else:
        text = "\n".join([f"{j[0]} - {j[1]}" for j in jobs])

    await update.callback_query.message.reply_text(text)

# LISTA NOMI
async def list_names(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    cursor.execute("SELECT name FROM jobs")
    names = cursor.fetchall()

    text = "\n".join([n[0] for n in names]) if names else "Vuoto"

    await update.callback_query.message.reply_text(text)

# MAIN
app = ApplicationBuilder().token(TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(create, pattern="create")],
    states={
        NAME: [MessageHandler(filters.TEXT, get_name)],
        LOCATION: [CallbackQueryHandler(get_location)],
        TERMINAL: [CallbackQueryHandler(get_terminal)],
        START: [MessageHandler(filters.TEXT, get_start)],
        END: [MessageHandler(filters.TEXT, get_end)],
    },
    fallbacks=[]
)

app.add_handler(CommandHandler("start", start))
app.add_handler(conv_handler)
app.add_handler(CallbackQueryHandler(list_jobs, pattern="list"))
app.add_handler(CallbackQueryHandler(list_names, pattern="names"))

app.run_polling()