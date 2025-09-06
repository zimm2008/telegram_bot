#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import time
import random
from datetime import datetime, timedelta, timezone
import telebot  # pyTelegramBotAPI
from telebot.types import Message
import threading

# ============================ CONFIG ============================
BOT_TOKEN = os.getenv("BOT_TOKEN", "7613091959:AAGrY_9XeZNda1GnbBFA_prDQG_Zoa2_7K8").strip()
if not BOT_TOKEN:
    raise RuntimeError("Please set BOT_TOKEN environment variable with your Telegram Bot token.")

# লাইসেন্স
LICENSE_KEY = "2025"

# Channel requirement
CHANNEL_USERNAME = "@JuniorEMON02"  # তোমার channel username

# ===============================================================
# Fancy (Mathematical Sans-Serif Bold) mapping
normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
fancy = (
    "𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉"
    "𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚟𝚛𝚜𝚝𝚞𝚟𝚝𝚡𝚢𝚣"
    "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"
)
fancy_dict = {n: f for n, f in zip(normal, fancy)}

def to_fancy(text: str) -> str:
    return ''.join(fancy_dict.get(c, c) for c in text)

# ===============================================================
# Available pairs
PAIRS = [
    "AUDCAD_OTC", "AUDCHF_OTC", "AUDJPY_OTC", "AUDNZD_OTC", "AUDUSD_OTC",
    "CADCHF_OTC", "CADJPY_OTC", "CHFJPY_OTC", "EURAUD_OTC", "EURCAD_OTC",
    "EURCHF_OTC", "EURGBP_OTC", "EURJPY_OTC", "EURUSD_OTC", "GBPAUD_OTC",
    "GBPCAD_OTC", "GBPCHF_OTC", "GBPJPY_OTC", "GBPNZD_OTC", "GBPUSD_OTC",
    "NZDCAD_OTC", "NZDCHF_OTC", "NZDJPY_OTC", "USDBDT_OTC", "USDBRL_OTC",
    "USDCAD_OTC", "USDCOP_OTC", "USDEGP_OTC", "USDIDR_OTC", "USDINR_OTC",
    "USDJPY_OTC", "USDMXN_OTC", "USDNGN_OTC", "USDPHP_OTC", "USDPKR_OTC",
    "USDTRY_OTC", "USDZAR_OTC", "USDDZD_OTC", "USDARS_OTC", "UKBRNT_OTC",
    "USCRUD_OTC", "XAGUSD_OTC", "XAUUSD_OTC", "BTCUSD_OTC", "ETHUSD_OTC",
    "AXPSTK_OTC", "FABSTK_OTC", "INTSTK_OTC", "MCDSTK_OTC", "MSFSTK_OTC", "PFESTK_OTC"
]

# ===============================================================
# Signal generation logic
def generate_signal(trend="All"):
    if trend == "CALL":
        return "CALL"
    elif trend == "PUT":
        return "PUT"
    else:
        return random.choice(["CALL", "PUT"])

def generate_signals_for_multiple_pairs(total_signals, start_datetime, selected_pairs, trend, backtest_day):
    seed_value = f"{total_signals}{start_datetime}{','.join(selected_pairs)}{trend}{backtest_day}"
    random.seed(seed_value)

    current_time = datetime.strptime(start_datetime, "%Y-%m-%d %H:%M") + timedelta(minutes=random.randint(3, 6))
    signals = []
    for _ in range(total_signals):
        for pair in random.choices(selected_pairs, k=1):
            signal_time = current_time.strftime("%H:%M")
            direction = generate_signal("All" if trend == "BOTH" else trend)
            signals.append(f"{pair} - {signal_time} ➪ {direction}")

            # Adjust time intervals based on the backtest day
            if 1 <= backtest_day <= 5:
                current_time += timedelta(minutes=random.randint(1, 5))
            elif 6 <= backtest_day <= 10:
                current_time += timedelta(minutes=random.randint(2, 7))
            elif 11 <= backtest_day <= 16:
                current_time += timedelta(minutes=random.randint(3, 13))
            elif 17 <= backtest_day <= 21:
                current_time += timedelta(minutes=random.randint(6, 12))
            elif backtest_day == 22:
                current_time += timedelta(minutes=random.randint(2, 30))
            elif 23 <= backtest_day <= 30:
                current_time += timedelta(minutes=random.randint(19, 90))
            else:
                print("Invalid Backtest Day!")
                return []
    return signals

# ===============================================================
# Simple per-user state
STATE = {}

def reset_state(user_id: int):
    STATE[user_id] = {
        "step": "license",
        "license": None,
        "date": None,
        "pairs": None,
        "start_time": None,
        "num_signals": None,
        "backtest_day": None,
        "direction": None,
    }

# ===============================================================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
WELCOME = "❤️ Welcome to Peradox Future Signal. Unmute the channel and pin it to the top. 💯"

# ===============================================================
# Channel membership checker
def is_user_in_channel(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

def require_channel(func):
    def wrapper(message: Message):
        if not is_user_in_channel(message.from_user.id):
            bot.send_message(
                message.chat.id,
                f"Please join our channel first:\n{CHANNEL_USERNAME}\n\nThen type /start again."
            )
            return
        return func(message)
    return wrapper

# ===============================================================
@bot.message_handler(commands=['start', '/'])
@require_channel
def handle_start(message: Message):
    user_id = message.chat.id
    reset_state(user_id)
    bot.send_message(message.chat.id, WELCOME)
    ask_license(message.chat.id)

@bot.message_handler(func=lambda m: m.text and m.text.strip() == "/")
def handle_slash_plain(message: Message):
    handle_start(message)

# ===============================================================
# Ask functions
def ask_license(chat_id):
    bot.send_message(chat_id, "🔗 Input your license:")

def ask_date(chat_id):
    bot.send_message(chat_id, "📅 Enter the signal date (YYYY-MM-DD):")

def ask_pairs(chat_id):
    bot.send_message(chat_id, "📊 Select pairs (XXXXXX_OTC):")

def ask_start_time(chat_id):
    bot.send_message(chat_id, "⏰ Enter the start time (HH:MM, 24-hour):")

def ask_num_signals(chat_id):
    bot.send_message(chat_id, "📌 How many signals do you want:")

def ask_backtest_day(chat_id):
    bot.send_message(chat_id, "⚒️ Enter the Backtest Day (1 to 30):")

def ask_direction(chat_id):
    bot.send_message(chat_id, "🎯 Enter the signal direction (CALL/PUT/BOTH):")

# ===============================================================
# Conversation handler
@bot.message_handler(func=lambda m: True, content_types=['text'])
@require_channel
def conversation(message: Message):
    user_id = message.from_user.id
    text = (message.text or "").strip()
    if user_id not in STATE:
        reset_state(user_id)

    step = STATE[user_id]["step"]

    try:
        if step == "license":
            if text == LICENSE_KEY:
                STATE[user_id]["license"] = text
                bot.send_message(message.chat.id, "License verified ✅")
                ask_date(message.chat.id)
                STATE[user_id]["step"] = "date"
            else:
                bot.send_message(message.chat.id, "Invalid license. Try again:")
                return

        elif step == "date":
            try:
                datetime.strptime(text, "%Y-%m-%d")
                STATE[user_id]["date"] = text
                ask_pairs(message.chat.id)
                STATE[user_id]["step"] = "pairs"
            except ValueError:
                bot.send_message(message.chat.id, "Invalid date! Use YYYY-MM-DD")
                return

        elif step == "pairs":
            raw_pairs = [p.strip().upper() for p in text.split(",") if p.strip()]
            if not raw_pairs:
                bot.send_message(message.chat.id, "Please enter at least one pair like USDMXN_OTC")
                return
            not_found = [p for p in raw_pairs if p not in PAIRS]
            if not_found:
                bot.send_message(message.chat.id, f"These pairs are not available: {', '.join(not_found)}")
                return
            STATE[user_id]["pairs"] = raw_pairs
            ask_start_time(message.chat.id)
            STATE[user_id]["step"] = "start_time"

        elif step == "start_time":
            try:
                datetime.strptime(text, "%H:%M")
                STATE[user_id]["start_time"] = text
                ask_num_signals(message.chat.id)
                STATE[user_id]["step"] = "num_signals"
            except ValueError:
                bot.send_message(message.chat.id, "Invalid time! Use HH:MM (24-hour)")
                return

        elif step == "num_signals":
            if not text.isdigit() or int(text) <= 0:
                bot.send_message(message.chat.id, "Enter a positive number for signals")
                return
            STATE[user_id]["num_signals"] = int(text)
            ask_backtest_day(message.chat.id)
            STATE[user_id]["step"] = "backtest_day"

        elif step == "backtest_day":
            if not text.isdigit() or not (1 <= int(text) <= 30):
                bot.send_message(message.chat.id, "Backtest Day must be 1–30")
                return
            STATE[user_id]["backtest_day"] = int(text)
            ask_direction(message.chat.id)
            STATE[user_id]["step"] = "direction"

        elif step == "direction":
            direction = text.upper()
            if direction not in ["CALL", "PUT", "BOTH"]:
                bot.send_message(message.chat.id, "Direction must be CALL / PUT / BOTH")
                return
            STATE[user_id]["direction"] = direction

            wait_msg = bot.send_message(message.chat.id, "Wait few moments... getting data from API")
            time.sleep(3)
            try:
                bot.delete_message(chat_id=wait_msg.chat.id, message_id=wait_msg.message_id)
            except Exception:
                pass

            date_str = STATE[user_id]["date"]
            start_time_str = STATE[user_id]["start_time"]
            start_dt = f"{date_str} {start_time_str}"
            total_signals = STATE[user_id]["num_signals"]
            selected_pairs = STATE[user_id]["pairs"]
            backtest_day = STATE[user_id]["backtest_day"]

            signals = generate_signals_for_multiple_pairs(
                total_signals, start_dt, selected_pairs, direction, backtest_day
            )

            tz = timezone(timedelta(hours=6))
            now_bd = datetime.now(tz)

            header_message = (
                f"╔═════════════════════════════╗\n"
                f"║⏰ TIMEZONE: UTC+6 [BANGLADESH]\n"
                f"║📅 DATE: {now_bd.strftime('%Y-%m-%d')}\n"
                f"║⌛ 1 MINUTE EXPIRY\n"
                f"║⚙️ 1 STEP MTG IF LOSS\n"
                f"╚═════════════════════════════╝"
            )

            signals_fancy = "\n".join(to_fancy(s) for s in signals)

            final_text = (
                f"<blockquote>==== PERADOX PREMIUM ====</blockquote>\n"
                f"<blockquote>{header_message}</blockquote>\n"
                f"<blockquote>{signals_fancy}</blockquote>\n"
                f"<blockquote>==== PERADOX PREMIUM ====</blockquote>"
            )

            bot.send_message(message.chat.id, final_text)
            reset_state(user_id)
            bot.send_message(message.chat.id, "You can start again. Type /start")

        else:
            reset_state(user_id)
            bot.send_message(message.chat.id, "Session reset. Type /start")

    except Exception as e:
        bot.send_message(message.chat.id, f"Error: {str(e)}")
        reset_state(user_id)
        bot.send_message(message.chat.id, "Session reset. Type /start")

# ===============================================================
if __name__ == "__main__":
    print("Peradox Signal Bot is running...")
    bot.infinity_polling(skip_pending=True, timeout=60)
