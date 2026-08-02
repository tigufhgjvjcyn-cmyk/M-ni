#!/usr/bin/env python3
"""
Bot Telegram vượt link kiếm tiền — Tự động cộng điểm & Quản lý Admin.
Cài: pip install "python-telegram-bot>=20.7" aiosqlite httpx
"""

import asyncio
import logging
import re
import secrets
import time
from datetime import datetime, timezone

import aiosqlite
import httpx
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ConversationHandler,
    MessageHandler, ContextTypes, filters,
)
from telegram.request import HTTPXRequest

# ==================== CẤU HÌNH ====================
BOT_TOKEN = "8691281927:AAGgAFTEAIHq-CLLtF5_ziKIdsmYCp8R4dU"
ADMIN_IDS = [6471940209]

SHORTENER_API_URL = "https://link4m.co/api-shorten/v2"
SHORTENER_API_KEY = "6a66d2f0849d7b73b377f764"

CHANNEL_URL = "https://t.me/tuongtacmxh36_bot"
GROUP_URL = ""

DEPOSIT_MOMO = "0900000000 - NGUYEN VAN A"
DEPOSIT_BANK = "MB Bank - 0123456789 - NGUYEN VAN A"

CONTACT_INFO = (
    "👨‍💻 Admin: @your_admin_username\n"
    "📢 Kênh: https://t.me/tuongtacmxh36_bot\n"
    "🕐 Hỗ trợ: 8h - 22h hằng ngày"
)

SERVICES = [
    {"id": "fb_like",   "cat": "buff", "name": "👍 Like Facebook",  "cost": 500,  "desc": "100 like / đơn"},
    {"id": "fb_follow", "cat": "buff", "name": "➕ Follow Facebook","cost": 800,  "desc": "100 follow / đơn"},
    {"id": "tt_view",   "cat": "buff", "name": "👁 View TikTok",     "cost": 300,  "desc": "1000 view / đơn"},
    {"id": "yt_sub",    "cat": "buff", "name": "🔔 Sub YouTube",     "cost": 1500, "desc": "50 sub / đơn"},
    {"id": "lq_quan",   "cat": "game", "name": "💎 Quân huy LQ",     "cost": 1000, "desc": "100 quân huy"},
    {"id": "lq_acc",    "cat": "game", "name": "🎮 Acc Liên Quân",   "cost": 2000, "desc": "acc trắng thông tin"},
    {"id": "sv_other",  "cat": "other","name": "🛠 Dịch vụ khác",    "cost": 500,  "desc": "báo admin yêu cầu riêng"},
]
CAT_TITLE = {"buff": "📊 BUFF MXH", "game": "🎮 LIÊN QUÂN", "other": "🛒 DỊCH VỤ"}

DB_PATH = "earnbot.db"

DEFAULT_SETTINGS = {
    "points_per_view": "500",
    "vnd_per_point": "1",
    "deposit_vnd_per_point": "1",
    "min_withdraw": "10000",
    "referral_bonus": "200",
    "earn_cooldown": "30",
    "token_ttl": "1800",
    "daily_bonus": "100",
    "getkey_daily_limit": "5",
}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
log = logging.getLogger("earnbot")
BOT_USERNAME = None

BTN_GETKEY = "🔑 Kiếm Điểm"
BTN_BUFF = "📊 Buff MXH"
BTN_STATUS = "📦 Status"
BTN_SERVICE = "🛒 Dịch Vụ"
BTN_GAME = "🎮 Liên Quân"
BTN_DEPOSIT = "💳 Nạp Tiền"
BTN_REF = "🔗 Giới Thiệu"
BTN_CONTACT = "📞 Liên Hệ"
BTN_CHAT = "💬 Chat Admin"
BTN_BALANCE = "💰 Số Dư"
BTN_WITHDRAW = "💸 Rút Tiền"
BTN_TOP = "🏆 Bảng Xếp Hạng"
BTN_HELP = "ℹ️ Trợ Giúp"

MAIN_KB = ReplyKeyboardMarkup(
    [
        [BTN_GETKEY],
        [BTN_BUFF, BTN_STATUS],
        [BTN_SERVICE, BTN_GAME],
        [BTN_DEPOSIT, BTN_REF],
        [BTN_CONTACT, BTN_CHAT],
        [BTN_BALANCE, BTN_WITHDRAW],
        [BTN_TOP, BTN_HELP],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

LINE = "━━━━━━━━━━━━━━━"

W_AMOUNT, W_METHOD, W_DETAIL = range(3)
CHAT_MSG = 10
DEP_METHOD, DEP_AMOUNT, DEP_NOTE = 20, 21, 22


async def db_init():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY, username TEXT,
                balance INTEGER DEFAULT 0, total_earned INTEGER DEFAULT 0,
                referrals INTEGER DEFAULT 0, referred_by INTEGER,
                last_earn INTEGER DEFAULT 0, last_daily TEXT,
                banned INTEGER DEFAULT 0, joined_at TEXT
            );
            CREATE TABLE IF NOT EXISTS tokens(
                token TEXT PRIMARY KEY, user_id INTEGER, created_at INTEGER,
                used INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS withdrawals(
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                points INTEGER, vnd INTEGER, method TEXT, detail TEXT,
                status TEXT DEFAULT 'pending', created_at TEXT, processed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS deposits(
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                vnd INTEGER, points INTEGER, method TEXT, note TEXT,
                status TEXT DEFAULT 'pending', created_at TEXT, processed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS orders(
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                service TEXT, cost INTEGER, target TEXT,
                status TEXT DEFAULT 'pending', created_at TEXT, processed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
            """
        )
        for stmt in ("ALTER TABLE users ADD COLUMN last_daily TEXT",):
            try:
                await db.execute(stmt)
            except Exception:
                pass
        
        for k, v in DEFAULT_SETTINGS.items():
            await db.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, v)
            )
        await db.commit()


async def get_setting(key: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = await cur.fetchone()
        return int(row[0]) if row else int(DEFAULT_SETTINGS.get(key, 0))


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        return await cur.fetchone()


async def ensure_user(user_id: int, username: str, referred_by: int | None = None):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
        if await cur.fetchone():
            await db.execute("UPDATE users SET username=? WHERE user_id=?",
                             (username, user_id))
            await db.commit()
            return False
        await db.execute(
            "INSERT INTO users(user_id,username,referred_by,joined_at) VALUES(?,?,?,?)",
            (user_id, username, referred_by, datetime.now(timezone.utc).isoformat()))
        await db.commit()
        return True


async def add_balance(user_id: int, points: int, count_earned: bool = True):
    async with aiosqlite.connect(DB_PATH) as db:
        if count_earned:
            await db.execute(
                "UPDATE users SET balance=balance+?, total_earned=total_earned+? "
                "WHERE user_id=?", (points, points, user_id))
        else:
            await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?",
                             (points, user_id))
        await db.commit()


async def shorten_url(long_url: str) -> str | None:
    params = {"api": SHORTENER_API_KEY, "url": long_url}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(SHORTENER_API_URL, params=params)
            r.raise_for_status()
            return parse_short_response(r)
    except Exception as e:
        log.error("Shorten error: %s", e)
        return None


def parse_short_response(resp: httpx.Response) -> str | None:
    text = resp.text.strip()
    try:
        data = resp.json()
        for key in ("shortenedUrl", "short", "shorturl", "url", "result"):
            if data.get(key):
                return data[key]
    except Exception:
        pass
    
    if text.startswith("http"):
        return text
    return None


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    
    if args and not args[0].isdigit():
        token_val = args[0].strip()
        now = int(time.time())
        ttl = await get_setting("token_ttl")
        ppv = await get_setting("points_per_view")
        
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            row = await (await db.execute(
                "SELECT * FROM tokens WHERE token=? AND user_id=?", 
                (token_val, user.id)
            )).fetchone()
            
            if not row:
                await update.message.reply_text("❌ Mã phiên làm việc không hợp lệ.", reply_markup=MAIN_KB)
                return
            if row["used"]:
                await update.message.reply_text("❌ Link này đã được sử dụng để nhận thưởng rồi.", reply_markup=MAIN_KB)
                return
            if now - row["created_at"] > ttl:
                await update.message.reply_text("⌛ Phiên vượt link đã quá hạn (quá 30 phút). Vui lòng lấy link mới.", reply_markup=MAIN_KB)
                return
                
            await db.execute("UPDATE tokens SET used=1 WHERE token=?", (token_val,))
            await db.commit()
            
        await add_balance(user.id, ppv, count_earned=True)
        updated_user = await get_user(user.id)
        
        success_msg = (
            f"🎉 <b>VƯỢT LINK THÀNH CÔNG!</b>\n"
            f"{LINE}\n"
            f"➕ Nhận được: <b>+{ppv} điểm</b>\n"
            f"💰 Số dư hiện tại: <b>{updated_user['balance']:,} điểm</b>"
        )
        await update.message.reply_text(success_msg, parse_mode=ParseMode.HTML, reply_markup=MAIN_KB)
        return

    referred_by = None
    if args and args[0].isdigit() and int(args[0]) != user.id:
        referred_by = int(args[0])
        
    await ensure_user(user.id, user.username or user.first_name, referred_by)
    row2 = await get_user(user.id)
    bal = row2["balance"] if row2 else 0
    header = f"🚀 <b>BOT VƯỢT LINK KIẾM TIỀN</b>"
    if CHANNEL_URL:
        header += f" | {CHANNEL_URL}"
    text = (
        f"{header}\n\n"
        f"👋 Xin chào, <b>{user.first_name}</b>!\n"
        f"💎 Điểm của bạn: <b>{bal:,} điểm</b>\n\n"
        "📋 <b>MENU CHÍNH:</b>\n"
        "Bấm <b>🔑 Kiếm Điểm</b> để bắt đầu vượt link nhận thưởng ngay 👇")
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=MAIN_KB)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ppv = await get_setting("points_per_view")
    vpp = await get_setting("vnd_per_point")
    mw = await get_setting("min_withdraw")
    text = (
        f"ℹ️ <b>HƯỚNG DẪN</b>\n{LINE}\n"
        f"🔗 Vượt Link — mỗi link: <b>{ppv} điểm</b>\n"
        f"💱 Quy đổi: <b>1 điểm = {vpp} VND</b>\n"
        f"💸 Rút tối thiểu: <b>{mw:,} điểm</b>\n{LINE}\n"
        "<b>Cách kiếm điểm:</b>\n"
        "① Bấm 🔑 Kiếm Điểm để lấy link vượt quảng cáo.\n"
        "② Vượt link thành công, bot sẽ **tự động cộng điểm** ngay khi bạn quay lại Telegram!")
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=MAIN_KB)


async def cmd_getkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    row = await get_user(user.id)
    if not row:
        await ensure_user(user.id, user.username or user.first_name)
        row = await get_user(user.id)
    if row["banned"]:
        await update.message.reply_text("🚫 Tài khoản của bạn đã bị khóa.")
        return
    cooldown = await get_setting("earn_cooldown")
    now = int(time.time())
    if now - row["last_earn"] < cooldown:
        wait = cooldown - (now - row["last_earn"])
        await update.message.reply_text(f"⏳ Chờ <b>{wait}s</b> nữa rồi lấy link mới nhé.",
                                        parse_mode=ParseMode.HTML)
        return
    
    token = secrets.token_urlsafe(16)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO tokens(token, user_id, created_at, used) VALUES(?, ?, ?, 0)",
            (token, user.id, now))
        await db.execute("UPDATE users SET last_earn=? WHERE user_id=?", (now, user.id))
        await db.commit()
    
    redirect_url = f"https://t.me/{BOT_USERNAME}?start={token}"
    short = await shorten_url(redirect_url)
    if not short:
        await update.message.reply_text("⚠️ Tạo link thất bại, thử lại sau ít phút.")
        return
        
    ppv = await get_setting("points_per_view")
    
    msg_text = (
        f"🔑 <b>KIẾM ĐIỂM TỰ ĐỘNG</b>\n{LINE}\n"
        f"💎 Phần thưởng: <b>+{ppv} điểm</b>\n"
        "⏱ Hạn sử dụng: <b>30 phút</b>\n\n"
        "👉 Bấm nút bên dưới để vượt link, sau khi hoàn tất bot sẽ **tự động cộng điểm** cho bạn!"
    )
    
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 VƯỢT LINK NHẬN ĐIỂM", url=short)]])
    await update.message.reply_text(msg_text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_add_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "⚙️ <b>Cú pháp cộng điểm:</b>\n"
            "<code>/cong [user_id] [số_điểm]</code>\n"
            "Ví dụ: <code>/cong 123456789 5000</code>",
            parse_mode=ParseMode.HTML
        )
        return

    target_id_str, points_str = args[0], args[1]
    if not target_id_str.isdigit() or not points_str.lstrip("-").isdigit():
        await update.message.reply_text("❌ User ID hoặc số điểm không hợp lệ (phải là số).")
        return

    target_id = int(target_id_str)
    points = int(points_str)

    target_user = await get_user(target_id)
    if not target_user:
        await update.message.reply_text(f"❌ Không tìm thấy user ID `{target_id}` trong cơ sở dữ liệu.")
        return

    await add_balance(target_id, points, count_earned=(points > 0))
    updated_user = await get_user(target_id)

    await update.message.reply_text(
        f"✅ <b>CỘNG ĐIỂM THÀNH CÔNG!</b>\n"
        f"{LINE}\n"
        f"👤 User ID: <code>{target_id}</code>\n"
        f"➕ Đã cộng/trừ: <b>{points:,} điểm</b>\n"
        f"💰 Số dư mới: <b>{updated_user['balance']:,} điểm</b>",
        parse_mode=ParseMode.HTML
    )

    try:
        await context.bot.send_message(
            target_id,
            f"🎁 Bạn vừa được Admin cộng <b>{points:,} điểm</b> vào tài khoản!\n"
            f"💰 Số dư hiện tại: <b>{updated_user['balance']:,} điểm</b>",
            parse_mode=ParseMode.HTML
        )
    except Exception:
        pass


async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    row = await get_user(update.effective_user.id)
    if not row:
        await update.message.reply_text("Bấm /start trước nhé.")
        return
    vpp = await get_setting("vnd_per_point")
    await update.message.reply_text(
        f"💼 <b>VÍ CỦA BẠN</b>\n{LINE}\n"
        f"💰 Số dư: <b>{row['balance']:,} điểm</b>\n"
        f"💵 Quy đổi: <b>~{row['balance']*vpp:,} VND</b>\n"
        f"📈 Tổng đã kiếm: {row['total_earned']:,} điểm",
        parse_mode=ParseMode.HTML, reply_markup=MAIN_KB)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    st = {"pending": "⏳ Chờ", "approved": "✅ Duyệt", "rejected": "❌ Từ chối", "done": "✅ Xong"}
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        wds = await (await db.execute("SELECT * FROM withdrawals WHERE user_id=? ORDER BY id DESC LIMIT 5", (uid,))).fetchall()
        deps = await (await db.execute("SELECT * FROM deposits WHERE user_id=? ORDER BY id DESC LIMIT 5", (uid,))).fetchall()
        ords = await (await db.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 5", (uid,))).fetchall()
    lines = [f"📊 <b>TRẠNG THÁI ĐƠN</b>", LINE]
    lines.append("💳 <b>Nạp tiền:</b>")
    lines += [f"  #{d['id']} · {d['vnd']:,}₫ · {st.get(d['status'])}" for d in deps] or ["  —"]
    lines.append("💸 <b>Rút tiền:</b>")
    lines += [f"  #{w['id']} · {w['points']:,}đ · {st.get(w['status'])}" for w in wds] or ["  —"]
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=MAIN_KB)


async def cmd_ref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    row = await get_user(uid)
    rb = await get_setting("referral_bonus")
    link = f"https://t.me/{BOT_USERNAME}?start={uid}"
    await update.message.reply_text(
        f"👥 <b>MỜI BẠN — NHẬN ĐIỂM</b>\n{LINE}\n"
        f"🎁 Mỗi người mời được: <b>+{rb} điểm</b>\n"
        f"🏅 Đã mời: <b>{row['referrals'] if row else 0} người</b>\n\n"
        f"🔗 Link của bạn:\n<code>{link}</code>",
        parse_mode=ParseMode.HTML, reply_markup=MAIN_KB)


async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute("SELECT username,total_earned FROM users ORDER BY total_earned DESC LIMIT 10")).fetchall()
    if not rows:
        await update.message.reply_text("Chưa có ai trên BXH.", reply_markup=MAIN_KB)
        return
    medals = ["🥇", "🥈", "🥉"] + [f"{i}\u20e3" for i in range(4, 10)] + ["🔟"]
    lines = [f"🏆 <b>TOP 10 KIẾM NHIỀU NHẤT</b>", LINE]
    for i, r in enumerate(rows):
        lines.append(f"{medals[i]} {r['username'] or 'user'} — <b>{r['total_earned']:,}</b> điểm")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=MAIN_KB)


async def cmd_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📞 <b>LIÊN HỆ</b>\n{LINE}\n{CONTACT_INFO}", parse_mode=ParseMode.HTML, reply_markup=MAIN_KB)


async def show_category(update: Update, cat: str):
    items = [s for s in SERVICES if s["cat"] == cat]
    rows, lines = [], [f"<b>{CAT_TITLE.get(cat, 'DỊCH VỤ')}</b>", LINE]
    for s in items:
        lines.append(f"{s['name']} — <b>{s['cost']:,} điểm</b>\n   <i>{s['desc']}</i>")
        rows.append([InlineKeyboardButton(f"Đặt: {s['name']} ({s['cost']:,}đ)", callback_data=f"svc_{s['id']}")])
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(rows))


async def cmd_buff(update, context): await show_category(update, "buff")
async def cmd_game(update, context): await show_category(update, "game")
async def cmd_services(update, context): await show_category(update, "other")


async def cb_service_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    sid = q.data[len("svc_"):]
    svc = next((s for s in SERVICES if s["id"] == sid), None)
    if not svc:
        await q.answer("Dịch vụ không tồn tại.", show_alert=True)
        return
    user = q.from_user
    row = await get_user(user.id)
    if not row or row["balance"] < svc["cost"]:
        await q.answer(f"Không đủ điểm. Cần {svc['cost']:,} điểm.", show_alert=True)
        return
    await q.answer()
    await add_balance(user.id, -svc["cost"], count_earned=False)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("INSERT INTO orders(user_id,service,cost,created_at) VALUES(?,?,?,?)",
                               (user.id, svc["name"], svc["cost"], datetime.now(timezone.utc).isoformat()))
        await db.commit()
        oid = cur.lastrowid
    await q.edit_message_text(f"✅ Đã đặt <b>{svc['name']}</b> (#{oid})", parse_mode=ParseMode.HTML)


async def dep_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rate = await get_setting("deposit_vnd_per_point")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Momo", callback_data="dm_momo")],
        [InlineKeyboardButton("🏦 Ngân hàng", callback_data="dm_bank")],
    ])
    await update.message.reply_text(f"💳 <b>NẠP TIỀN</b>\n{LINE}\nTỷ giá: <b>{rate:,} VND = 1 điểm</b>", parse_mode=ParseMode.HTML, reply_markup=kb)
    return DEP_METHOD


async def dep_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    method = "Momo" if q.data == "dm_momo" else "Ngân hàng"
    context.user_data["dep_method"] = method
    info = DEPOSIT_MOMO if method == "Momo" else DEPOSIT_BANK
    await q.edit_message_text(f"💳 <b>Nạp qua {method}</b>\n{LINE}\nCK tới:\n<code>{info}</code>\n\nNhập số tiền VND:", parse_mode=ParseMode.HTML)
    return DEP_AMOUNT


async def dep_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(".", "").replace(",", "")
    if not text.isdigit():
        await update.message.reply_text("Nhập số tiền hợp lệ.")
        return DEP_AMOUNT
    context.user_data["dep_vnd"] = int(text)
    await update.message.reply_text("Nhập mã giao dịch / nội dung:")
    return DEP_NOTE


async def dep_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    proof = update.message.text.strip()
    vnd = context.user_data["dep_vnd"]
    method = context.user_data["dep_method"]
    rate = await get_setting("deposit_vnd_per_point")
    points = vnd // rate
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO deposits(user_id,vnd,points,method,note,created_at) VALUES(?,?,?,?,?,?)",
                         (user.id, vnd, points, method, proof, datetime.now(timezone.utc).isoformat()))
        await db.commit()
    await update.message.reply_text("✅ Đã gửi yêu cầu nạp tiền, chờ admin duyệt.", reply_markup=MAIN_KB)
    context.user_data.clear()
    return ConversationHandler.END


async def chat_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💬 Nhập nội dung tin nhắn gửi admin:")
    return CHAT_MSG


async def chat_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message.text.strip()
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, f"💬 Tin từ {user.first_name} (`{user.id}`):\n{msg}", parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass
    await update.message.reply_text("✅ Đã gửi tới admin.", reply_markup=MAIN_KB)
    return ConversationHandler.END


async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    row = await get_user(update.effective_user.id)
    mw = await get_setting("min_withdraw")
    if not row or row["balance"] < mw:
        await update.message.reply_text(f"💸 Chưa đủ điểm rút (tối thiểu {mw:,} điểm).", reply_markup=MAIN_KB)
        return ConversationHandler.END
    await update.message.reply_text(f"💸 Nhập số điểm muốn rút (tối thiểu {mw:,}):")
    return W_AMOUNT


async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("Nhập số hợp lệ.")
        return W_AMOUNT
    mw = await get_setting("min_withdraw")
    amount = int(text)
    if amount < mw:
        await update.message.reply_text(f"Số tiền rút tối thiểu là {mw:,} điểm.")
        return W_AMOUNT
    context.user_data["w_amount"] = amount
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Momo", callback_data="wm_momo")],
        [InlineKeyboardButton("🏦 Ngân hàng", callback_data="wm_bank")],
    ])
    await update.message.reply_text("Chọn phương thức nhận tiền 👇", reply_markup=kb)
    return W_METHOD


async def withdraw_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["w_method"] = "Momo" if q.data == "wm_momo" else "Ngân hàng"
    await q.edit_message_text("Nhập thông tin tài khoản nhận tiền:")
    return W_DETAIL


async def withdraw_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    detail = update.message.text.strip()
    amount = context.user_data["w_amount"]
    method = context.user_data["w_method"]
    vpp = await get_setting("vnd_per_point")
    vnd = amount * vpp
    await add_balance(user.id, -amount, count_earned=False)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO withdrawals(user_id,points,vnd,method,detail,created_at) VALUES(?,?,?,?,?,?)",
                         (user.id, amount, vnd, method, detail, datetime.now(timezone.utc).isoformat()))
        await db.commit()
    await update.message.reply_text("✅ Đã tạo lệnh rút tiền, chờ duyệt.", reply_markup=MAIN_KB)
    context.user_data.clear()
    return ConversationHandler.END


async def conv_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Đã hủy.", reply_markup=MAIN_KB)
    return ConversationHandler.END


async def post_init(app: Application):
    global BOT_USERNAME
    me = await app.bot.get_me()
    BOT_USERNAME = me.username
    await db_init()
    log.info("Bot @%s sẵn sàng.", BOT_USERNAME)


def btn(label: str):
    return filters.Regex(rf"^{re.escape(label)}$")


def main():
    global BOT_USERNAME
    # Khởi tạo Application kèm HTTPXRequest tường minh để tránh lỗi khởi tạo request trong container
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(HTTPXRequest(connect_timeout=30, read_timeout=30))
        .post_init(post_init)
        .build()
    )

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("withdraw", withdraw_start), MessageHandler(btn(BTN_WITHDRAW), withdraw_start)],
        states={W_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount)],
                W_METHOD: [CallbackQueryHandler(withdraw_method, pattern=r"^wm_")],
                W_DETAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_detail)]},
        fallbacks=[CommandHandler("cancel", conv_cancel)]))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("deposit", dep_start), MessageHandler(btn(BTN_DEPOSIT), dep_start)],
        states={DEP_METHOD: [CallbackQueryHandler(dep_method, pattern=r"^dm_")],
                DEP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, dep_amount)],
                DEP_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, dep_note)]},
        fallbacks=[CommandHandler("cancel", conv_cancel)]))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("chat", chat_start), MessageHandler(btn(BTN_CHAT), chat_start)],
        states={CHAT_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, chat_send)]},
        fallbacks=[CommandHandler("cancel", conv_cancel)]))

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("getkey", cmd_getkey))
    app.add_handler(CommandHandler("balance", cmd_balance))
    app.add_handler(CommandHandler("ref", cmd_ref))
    app.add_handler(CommandHandler("top", cmd_top))
    app.add_handler(CommandHandler("services", cmd_services))
    app.add_handler(CommandHandler("dichvukhac", cmd_services))
    app.add_handler(CommandHandler("buffmxh", cmd_buff))
    app.add_handler(CommandHandler("lienquan", cmd_game))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("contact", cmd_contact))
    
    app.add_handler(CommandHandler("cong", cmd_add_points))

    app.add_handler(MessageHandler(btn(BTN_GETKEY), cmd_getkey))
    app.add_handler(MessageHandler(btn(BTN_BUFF), cmd_buff))
    app.add_handler(MessageHandler(btn(BTN_STATUS), cmd_status))
    app.add_handler(MessageHandler(btn(BTN_SERVICE), cmd_services))
    app.add_handler(MessageHandler(btn(BTN_GAME), cmd_game))
    app.add_handler(MessageHandler(btn(BTN_REF), cmd_ref))
    app.add_handler(MessageHandler(btn(BTN_CONTACT), cmd_contact))
    app.add_handler(MessageHandler(btn(BTN_BALANCE), cmd_balance))
    app.add_handler(MessageHandler(btn(BTN_TOP), cmd_top))
    app.add_handler(MessageHandler(btn(BTN_HELP), cmd_help))

    app.add_handler(CallbackQueryHandler(cb_service_order, pattern=r"^svc_"))

    log.info("Đang chạy polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
