import os
import json
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===================== SOZLAMALAR =====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Tokenni environment variable orqali bering!
ADMIN_IDS_FILE = "admin_ids.json"
MATERIALS_FILE = "materials.json"
USERS_FILE = "users.json"

NARX = 10000
KARTA = "KARTA_RAQAMINI_BU_YERGA_YOZING"  # O'z karta raqamingizni yozing
ADMIN_USERNAME = "@nozimjonov20"
BEPUL_RAQAM = "1"  # Bu raqamdagi material bepul

# ===================== MA'LUMOT YUKLASH =====================
def load_json(filename, default):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_admins():
    return load_json(ADMIN_IDS_FILE, [])

def get_materials():
    return load_json(MATERIALS_FILE, {})

def get_users():
    return load_json(USERS_FILE, {})

def is_admin(user_id: int) -> bool:
    return user_id in get_admins()

def is_paid(user_id: int) -> bool:
    users = get_users()
    return users.get(str(user_id), {}).get("paid", False)

def set_paid(user_id: int, name: str):
    users = get_users()
    if str(user_id) not in users:
        users[str(user_id)] = {"name": name, "username": "", "qoshilgan": ""}
    users[str(user_id)]["paid"] = True
    users[str(user_id)]["tolagan_vaqt"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_json(USERS_FILE, users)

def register_user(user_id: int, name: str, username: str = ""):
    users = get_users()
    if str(user_id) not in users:
        users[str(user_id)] = {
            "name": name,
            "username": username,
            "paid": False,
            "qoshilgan": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        save_json(USERS_FILE, users)

# ===================== FOYDALANUVCHI KOMANDALAR =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    materials = get_materials()
    register_user(user.id, user.full_name, user.username or "")

    if is_admin(user.id):
        await update.message.reply_text(
            f"👋 Salom, {user.first_name}!\n\n"
            "🔧 Siz admin sifatida kirgansiz.\n"
            "/admin — Admin panel"
        )
        return

    paid = is_paid(user.id)

    if paid:
        text = (
            f"👋 Salom, {user.first_name}!\n\n"
            "📖 *Dinshunoslik fani materiallari botiga xush kelibsiz!*\n\n"
            "✅ Sizning obunangiz faol.\n\n"
            f"📦 Jami materiallar: *{len(materials)}* ta\n\n"
            "📋 /list — Materiallar ro'yxati\n"
            "💡 Material raqamini yuboring va yuklab oling!"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
    else:
        keyboard = [
            [InlineKeyboardButton("🎁 Bepul namuna ko'rish", callback_data="bepul_namuna")],
            [InlineKeyboardButton("💳 Payme orqali to'lash", callback_data="tolov_payme")],
            [InlineKeyboardButton("💳 Click orqali to'lash", callback_data="tolov_click")],
            [InlineKeyboardButton("📞 Admin bilan bog'lanish", url="https://t.me/nozimjonov20")],
        ]
        text = (
            f"👋 Salom, {user.first_name}!\n\n"
            "📖 *Dinshunoslik fani materiallari botiga xush kelibsiz!*\n\n"
            "Bu botda:\n"
            "📑 Slaydlar\n"
            "📚 Konspektlar\n"
            "📝 Testlar va qo'shimcha materiallar\n\n"
            "🎁 *1-material bepul!* Sinab ko'ring.\n\n"
            f"💰 To'liq obuna narxi: *{NARX:,} so'm*\n\n"
            "⬇️ Quyidagi tugmani bosing:"
        )
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    materials = get_materials()

    if query.data == "bepul_namuna":
        mat = materials.get(BEPUL_RAQAM)
        if mat:
            await query.message.reply_text(f"⏳ *{mat.get('title')}* yuklanmoqda...", parse_mode="Markdown")
            try:
                file_id = mat.get("file_id")
                file_type = mat.get("type", "document")
                caption = (
                    f"🎁 *BEPUL NAMUNA*\n\n"
                    f"📚 *{mat.get('title')}*\n\n"
                    f"{mat.get('description', '')}\n\n"
                    f"✅ To'liq obuna uchun: /start"
                )
                if file_type == "photo":
                    await query.message.reply_photo(photo=file_id, caption=caption, parse_mode="Markdown")
                elif file_type == "video":
                    await query.message.reply_video(video=file_id, caption=caption, parse_mode="Markdown")
                else:
                    await query.message.reply_document(document=file_id, caption=caption, parse_mode="Markdown")
            except Exception as e:
                logger.error(e)
                await query.message.reply_text("❌ Hozircha bepul material yuklanmagan. Tez orada qo'shiladi!")
        else:
            await query.message.reply_text("📭 Hozircha bepul material yuklanmagan. Tez orada qo'shiladi!")

    elif query.data == "tolov_payme":
        text = (
            "💳 *Payme orqali to'lash:*\n\n"
            f"💰 Summa: *{NARX:,} so'm*\n\n"
            "📱 Quyidagi karta raqamiga o'tkazma qiling:\n"
            f"`{KARTA}`\n\n"
            f"✅ To'lovdan so'ng chekni adminga yuboring:\n"
            f"👤 {ADMIN_USERNAME}\n\n"
            "⏳ Admin tasdiqlashidan so'ng obunangiz faollashadi."
        )
        keyboard = [
            [InlineKeyboardButton("✅ Chekni adminga yuborish", url="https://t.me/nozimjonov20")],
            [InlineKeyboardButton("◀️ Orqaga", callback_data="orqaga")],
        ]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "tolov_click":
        text = (
            "💳 *Click orqali to'lash:*\n\n"
            f"💰 Summa: *{NARX:,} so'm*\n\n"
            "📱 Quyidagi karta raqamiga o'tkazma qiling:\n"
            f"`{KARTA}`\n\n"
            f"✅ To'lovdan so'ng chekni adminga yuboring:\n"
            f"👤 {ADMIN_USERNAME}\n\n"
            "⏳ Admin tasdiqlashidan so'ng obunangiz faollashadi."
        )
        keyboard = [
            [InlineKeyboardButton("✅ Chekni adminga yuborish", url="https://t.me/nozimjonov20")],
            [InlineKeyboardButton("◀️ Orqaga", callback_data="orqaga")],
        ]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "orqaga":
        keyboard = [
            [InlineKeyboardButton("🎁 Bepul namuna ko'rish", callback_data="bepul_namuna")],
            [InlineKeyboardButton("💳 Payme orqali to'lash", callback_data="tolov_payme")],
            [InlineKeyboardButton("💳 Click orqali to'lash", callback_data="tolov_click")],
            [InlineKeyboardButton("📞 Admin bilan bog'lanish", url="https://t.me/nozimjonov20")],
        ]
        text = (
            "📖 *Dinshunoslik fani materiallari botiga xush kelibsiz!*\n\n"
            "🎁 *1-material bepul!* Sinab ko'ring.\n\n"
            f"💰 To'liq obuna narxi: *{NARX:,} so'm*\n\n"
            "⬇️ Quyidagi tugmani bosing:"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def list_materials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id) and not is_paid(user.id):
        await update.message.reply_text(
            "❌ Bu bo'lim faqat obuna bo'lganlar uchun.\n\n"
            "/start — To'lov qilish"
        )
        return

    materials = get_materials()
    if not materials:
        await update.message.reply_text("📭 Hozircha materiallar yo'q.")
        return

    text = "📚 *Mavjud materiallar:*\n\n"
    for num, mat in sorted(materials.items(), key=lambda x: int(x[0])):
        icon = "📄" if mat.get("type") == "document" else "🖼"
        tag = "🎁 " if num == BEPUL_RAQAM else ""
        text += f"{tag}{icon} *{num}* — {mat.get('title', 'Nomsiz')}\n"

    text += "\n💡 Raqamini yozing va material yuklab beriladi!"
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    materials = get_materials()
    register_user(user.id, user.full_name, user.username or "")

    if text.isdigit():
        # Bepul material — hamma yuklay oladi
        if text == BEPUL_RAQAM:
            mat = materials.get(text)
            if mat:
                await send_material(update.message, mat, bepul=True)
            else:
                await update.message.reply_text("📭 Bepul material hali yuklanmagan.")
            return

        # Pullik materiallar
        if not is_admin(user.id) and not is_paid(user.id):
            keyboard = [
                [InlineKeyboardButton("💳 Obuna bo'lish", callback_data="orqaga")]
            ]
            await update.message.reply_text(
                "🔒 Bu material faqat obuna bo'lganlar uchun.\n\n"
                "🎁 *1-material bepul* — sinab ko'ring!\n\n"
                "/start — Obuna bo'lish",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        mat = materials.get(text)
        if mat:
            await send_material(update.message, mat)
        else:
            await update.message.reply_text(
                f"❓ *{text}* raqamli material topilmadi.\n\n"
                "📋 /list — barcha materiallarni ko'rish",
                parse_mode="Markdown"
            )
    else:
        await update.message.reply_text(
            "💡 Material olish uchun faqat *raqam* yuboring.\n"
            "Masalan: `1` yoki `5`\n\n"
            "📋 /list — materiallar ro'yxati",
            parse_mode="Markdown"
        )


async def send_material(message, mat, bepul=False):
    title = mat.get('title')
    await message.reply_text(f"⏳ *{title}* yuklanmoqda...", parse_mode="Markdown")
    try:
        file_id = mat.get("file_id")
        file_type = mat.get("type", "document")
        if bepul:
            caption = f"🎁 *BEPUL NAMUNA*\n📚 *{title}*\n\n{mat.get('description', '')}\n\n✅ To'liq obuna: /start"
        else:
            caption = f"📚 *{title}*\n\n{mat.get('description', '')}"

        if file_type == "photo":
            await message.reply_photo(photo=file_id, caption=caption, parse_mode="Markdown")
        elif file_type == "video":
            await message.reply_video(video=file_id, caption=caption, parse_mode="Markdown")
        else:
            await message.reply_document(document=file_id, caption=caption, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Fayl yuborishda xato: {e}")
        await message.reply_text("❌ Faylni yuborishda xato. Admin bilan bog'laning.")


# ===================== ADMIN KOMANDALAR =====================

async def add_me_as_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admins = get_admins()
    user_id = update.effective_user.id

    if user_id in admins:
        await update.message.reply_text(f"✅ Siz allaqachon adminsiz. ID: `{user_id}`", parse_mode="Markdown")
        return

    if len(admins) >= 5:
        await update.message.reply_text("❌ Adminlar soni to'ldi (max 5 ta).")
        return

    admins.append(user_id)
    save_json(ADMIN_IDS_FILE, admins)
    await update.message.reply_text(
        f"✅ Admin bo'ldingiz!\nID: `{user_id}`\n\n"
        "/admin — Admin panel",
        parse_mode="Markdown"
    )


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Ruxsat yo'q.")
        return

    materials = get_materials()
    users = get_users()
    paid_count = sum(1 for u in users.values() if u.get("paid"))

    text = (
        "🔧 *Admin Panel*\n\n"
        f"📦 Materiallar: {len(materials)}\n"
        f"👥 Jami foydalanuvchilar: {len(users)}\n"
        f"✅ To'lagan: {paid_count}\n"
        f"💰 Narx: {NARX:,} so'm\n\n"
        "📤 *Fayl yuklash:*\n"
        "Faylni yuboring va izohga (caption) yozing:\n"
        "`1/Mavzu nomi`\n\n"
        "Misol: `1/Islom dini tarixi`\n\n"
        "✅ *Obuna faollashtirish:*\n"
        "`/faollashtir [user_id]`\n\n"
        "💰 *Narx o'zgartirish:*\n"
        "`/narx [summa]`\n\n"
        "🗑 `/delete [raqam]`\n"
        "📊 /stats — Statistika\n"
        "👥 /foydalanuvchilar — Ro'yxat"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def faollashtir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Ruxsat yo'q.")
        return

    if not context.args:
        await update.message.reply_text("❌ User ID kiriting: `/faollashtir 123456789`", parse_mode="Markdown")
        return

    user_id = context.args[0]
    set_paid(int(user_id), "Admin tomonidan")
    await update.message.reply_text(f"✅ {user_id} obunasi faollashtirildi!")

    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text="🎉 *Tabriklaymiz!*\n\nObunangiz faollashtirildi!\n\n"
                 "📚 Barcha materiallarga kirish imkoningiz bor.\n"
                 "/list — Materiallar ro'yxati",
            parse_mode="Markdown"
        )
    except Exception:
        pass


async def narx_ozgartir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Ruxsat yo'q.")
        return

    if not context.args:
        await update.message.reply_text("❌ Narx kiriting: `/narx 15000`", parse_mode="Markdown")
        return

    global NARX
    try:
        NARX = int(context.args[0])
        await update.message.reply_text(f"✅ Narx: *{NARX:,} so'm*", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ To'g'ri son kiriting!")


async def foydalanuvchilar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Ruxsat yo'q.")
        return

    users = get_users()
    if not users:
        await update.message.reply_text("📭 Hali foydalanuvchilar yo'q.")
        return

    paid_users = {k: v for k, v in users.items() if v.get("paid")}
    free_users = {k: v for k, v in users.items() if not v.get("paid")}

    text = "✅ *SOTIB OLGANLAR:*\n\n"
    if paid_users:
        for uid, info in paid_users.items():
            uname = f"@{info['username']}" if info.get("username") else "username yo'q"
            vaqt = info.get("tolagan_vaqt", "")
            text += f"💰 {info.get('name', 'Nomsiz')} ({uname})\n"
            text += f"   🆔 `{uid}`\n"
            if vaqt:
                text += f"   📅 {vaqt}\n"
            text += "\n"
    else:
        text += "Hali hech kim sotib olmagan.\n\n"

    text += f"\n❌ *SOTIB OLMAGANLAR:* {len(free_users)} ta\n\n"
    for uid, info in list(free_users.items())[:30]:
        uname = f"@{info['username']}" if info.get("username") else "username yo'q"
        text += f"• {info.get('name', 'Nomsiz')} ({uname}) — `{uid}`\n"

    if len(free_users) > 30:
        text += f"\n... va yana {len(free_users) - 30} ta"

    if len(text) > 4000:
        text = text[:4000] + "\n\n... (ro'yxat juda uzun)"

    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_admin_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    message = update.message
    caption = (message.caption or "").strip()

    if not caption:
        await message.reply_text(
            "📌 Faylni yuborayotganda izohga (caption) shunday yozing:\n\n"
            "`1/Mavzu nomi`\n\n"
            "Misol:\n"
            "`1/Islom dini tarixi`\n"
            "`5/Test savollari`",
            parse_mode="Markdown"
        )
        return

    if "/" in caption:
        parts = caption.split("/", 1)
    else:
        parts = caption.split(" ", 1)

    num = parts[0].strip()

    if not num.isdigit():
        await message.reply_text(
            "❌ Birinchi qism *raqam* bo'lishi kerak!\n\n"
            "Misol: `1/Mavzu nomi`",
            parse_mode="Markdown"
        )
        return

    title = parts[1].strip() if len(parts) > 1 else f"Material {num}"
    description = ""

    if message.document:
        file_id, file_type = message.document.file_id, "document"
    elif message.photo:
        file_id, file_type = message.photo[-1].file_id, "photo"
    elif message.video:
        file_id, file_type = message.video.file_id, "video"
    else:
        await message.reply_text("❌ Fayl turi qo'llab-quvvatlanmaydi!")
        return

    materials = get_materials()
    materials[num] = {"title": title, "description": description, "file_id": file_id, "type": file_type}
    save_json(MATERIALS_FILE, materials)

    tag = " 🎁 (BEPUL)" if num == BEPUL_RAQAM else ""
    await message.reply_text(
        f"✅ Saqlandi!\n📚 *{num}* — {title}{tag}",
        parse_mode="Markdown"
    )


async def delete_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Ruxsat yo'q.")
        return

    if not context.args:
        await update.message.reply_text("❌ `/delete 5`", parse_mode="Markdown")
        return

    num = context.args[0]
    materials = get_materials()

    if num in materials:
        title = materials[num].get("title", "Nomsiz")
        del materials[num]
        save_json(MATERIALS_FILE, materials)
        await update.message.reply_text(f"🗑 *{num}* — {title} o'chirildi.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ {num} topilmadi.")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Ruxsat yo'q.")
        return

    materials = get_materials()
    users = get_users()
    paid_count = sum(1 for u in
