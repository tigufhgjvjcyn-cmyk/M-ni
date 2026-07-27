import os
import telebot
from flask import Flask, request
import requests

# TOKEN VÀ URL VERCEL CỦA BẠN ĐÃ ĐƯỢC CẤU HÌNH SẴN
TOKEN = os.environ.get("TELEGRAM_TOKEN", "8691281927:AAGgAFTEAIHq-CLLtF5_ziKIdsmYCp8R4dU")
VERCEL_URL = "https://bot-tele-lilac.vercel.app/"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ==========================================
# KHU VỰC TÍCH HỢP API FREE FIRE CỦA BẠN
# ==========================================
def get_ff_level_info(player_id):
    """
    Bạn có thể thay thế logic gọi API Free Fire thật của bạn vào hàm này.
    """
    try:
        # Ví dụ nếu bạn có URL API thật:
        # api_url = f"https://api.example.com/ff_info?id={player_id}"
        # res = requests.get(api_url).json()
        # level = res.get('level', 'N/A')
        # name = res.get('name', 'N/A')
        # return f"🎮 **Thông tin Free Fire**\nID: `{player_id}`\nTên: {name}\nLevel: {level}"

        # Dữ liệu phản hồi mẫu:
        return f"🎮 **Thông Tin Tài Khoản Free Fire**\n\n🆔 **ID:** `{player_id}`\n👤 **Tên:** Player Demo\n⭐ **Cấp độ (Level):** 75\n🔥 **Trạng thái:** Hoạt động"
    except Exception as e:
        return f"❌ Có lỗi xảy ra khi gọi API Free Fire: {str(e)}"

# ==========================================
# CÁC LỆNH XỬ LÝ BOT TELEGRAM
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 **Chào mừng bạn đến với Bot Tra Cứu Level Free Fire!**\n\n"
        "📌 **Cách sử dụng:**\n"
        "Gửi lệnh `/info <ID_NGƯỜI_CHƠI>` để xem thông tin.\n"
        "Ví dụ: `/info 12345678`"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['info'])
def check_info(message):
    try:
        args = message.text.split(' ')
        if len(args) < 2:
            bot.reply_to(message, "⚠️ **Vui lòng nhập ID người chơi!**\nVí dụ: `/info 12345678`", parse_mode="Markdown")
            return
        
        player_id = args[1].strip()
        bot.reply_to(message, "⏳ *Đang tra cứu dữ liệu Free Fire, vui lòng chờ...*", parse_mode="Markdown")
        
        # Gọi API tra cứu
        info_text = get_ff_level_info(player_id)
        bot.reply_to(message, info_text, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Cú pháp không hợp lệ: {str(e)}")

# ==========================================
# CẤU HÌNH WEBHOOK CHO VERCEL
# ==========================================
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    try:
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    except Exception as e:
        return str(e), 500

@app.route("/")
def webhook():
    bot.remove_webhook()
    # Tự động set webhook về trang Vercel của bạn
    bot.set_webhook(url=VERCEL_URL + TOKEN)
    return f"<h1>Đã kết nối thành công Webhook!</h1><p>Bot Telegram đang chạy tại <b>{VERCEL_URL}</b></p>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
