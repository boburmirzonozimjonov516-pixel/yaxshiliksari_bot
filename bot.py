import os
import json
import logging
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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8922158442:AAHXph_Zs2_3PxgKIP5N9PLhg1y_981ojOs")
ADMIN_IDS_FILE = "admin_ids.json"
MATERIALS_FILE = "materials.json"

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

def is_admin(user_id: int) -> bool:
    return user_id in get_admins()

# ===================== FOYDALANUVCHI KOMANDALAR =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    admins = get_admins()
    materials = get_materials()
    
    text = (
        f"👋 Salom, {user.first_name}!\n\n"
        "📚 *YaxshiliksarI Bot*ga xush kelibsiz!\n\n"
        "Bu botda kitoblar, slaydlar va konspektlar mavjud.\n\n"
        "📥 Material olish uchun uning *raqamini* yuboring.\n"
        f"📦 Jami materiallar soni: *{len(materials)}* ta\n\n"
        "📋 Barcha materiallar ro'yxati uchun /list buyrug'ini yuboring."
    )
    
    if not admins:
        text += "\n\n⚙️ /addme — Admin bo'lish (birinchi foydalanuvchi)"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def list_materials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    materials = get_materials()
    
    if not materials:
        await update.message.reply_text("📭 Hozircha materiallar yo'q.\nAdmin tez orada yuklaydi!")
        return
    
    text = "📚 *Mavjud materiallar:*\n\n"
    for num, mat in sorted(materials.items(), key=lambda x: int(x[0])):
        icon = "📄" if mat.get("type") == "document" else "🖼"
        text += f"{icon} *{num}* — {mat.get('title', 'Nomsiz')}\n"
    
    text += "\n💡 Raqamini yozing va material yuklab beriladi!"
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    materials = get_materials()
    
    # Raqam yuborilganmi?
    if text.isdigit():
        mat = materials.get(text)
        if mat:
            await update.message.reply_text(f"⏳ *{mat.get('title')}* yuklanmoqda...", parse_mode="Markdown")
            try:
                file_id = mat.get("file_id")
                file_type = mat.get("type", "document")
                caption = f"📚 *{mat.get('title')}*\n\n{mat.get('description', '')}"
                
                if file_type == "photo":
                    await update.message.reply_photo(photo=file_id, caption=caption, parse_mode="Markdown")
                elif file_type == "video":
                    await update.message.reply_video(video=file_id, caption=caption, parse_mode="Markdown")
                else:
                    await update.message.reply_document(document=file_id, caption=caption, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Fayl yuborishda xato: {e}")
                await update.message.reply_text("❌ Faylni yuborishda xato. Admin bilan bog'laning.")
        else:
            await update.message.reply_text(
                f"❓ *{text}* raqamli material topilmadi.\n\n"
                "📋 /list — barcha materiallarni ko'rish",
                parse_mode="Markdown"
            )
    else:
        await update.message.reply_text(
            "💡 Material olish uchun faqat *raqam* yuboring.\n"
            "Masalan: `1` yoki `15`\n\n"
            "📋 /list — barcha materiallar ro'yxati",
            parse_mode="Markdown"
        )


# ===================== ADMIN KOMANDALAR =====================

async def add_me_as_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Birinchi admin qo'shilish"""
    admins = get_admins()
    user_id = update.effective_user.id
    
    if admins and not is_admin(user_id):
        await update.message.reply_text("❌ Siz admin emassiz.")
        return
    
    if user_id not in admins:
        admins.append(user_id)
        save_json(ADMIN_IDS_FILE, admins)
        await update.message.reply_text(
            f"✅ Admin bo'ldingiz!\nSizning ID: `{user_id}`\n\n"
            "🔧 Admin buyruqlari:\n"
            "/upload — Material yuklash\n"
            "/delete [raqam] — Material o'chirish\n"
            "/stats — Statistika",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(f"✅ Siz allaqachon adminsiz. ID: `{user_id}`", parse_mode="Markdown")


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Ruxsat yo'q.")
        return
    
    materials = get_materials()
    admins = get_admins()
    
    text = (
        "🔧 *Admin Panel*\n\n"
        f"👥 Adminlar soni: {len(admins)}\n"
        f"📦 Materiallar soni: {len(materials)}\n\n"
        "📤 *Material yuklash:*\n"
        "Faylni bot ga yuboring + caption (sarlavha):\n"
        "`/upload [raqam] | [sarlavha] | [tavsif]`\n\n"
        "Avval faylni yuboring, keyin:\n"
        "`/save [raqam] | [sarlavha]`\n\n"
        "🗑 *O'chirish:*\n"
        "`/delete [raqam]`\n\n"
        "📋 *Ro'yxat:* /list\n"
        "📊 *Statistika:* /stats"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_admin_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin fayl yuborganda saqlash"""
    if not is_admin(update.effective_user.id):
        return
    
    message = update.message
    caption = message.caption or ""
    
    # Caption formatini tekshirish: /save raqam | sarlavha | tavsif
    if not caption.startswith("/save"):
        await message.reply_text(
            "📌 Faylni saqlash uchun caption qo'shing:\n"
            "`/save [raqam] | [sarlavha] | [tavsif]`\n\n"
            "Misol: `/save 1 | Python kitob | Boshlang'ich Python darsligi`",
            parse_mode="Markdown"
        )
        return
    
    await save_file_from_message(message, caption)


async def save_file_from_message(message, caption):
    parts = caption.replace("/save", "").strip().split("|")
    if len(parts) < 2:
        await message.reply_text(
            "❌ Format xato!\n"
            "`/save [raqam] | [sarlavha] | [tavsif (ixtiyoriy)]`",
            parse_mode="Markdown"
        )
        return
    
    num = parts[0].strip()
    title = parts[1].strip()
    description = parts[2].strip() if len(parts) > 2 else ""
    
    if not num.isdigit():
        await message.reply_text("❌ Raqam to'g'ri emas!")
        return
    
    # Fayl turini aniqlash
    if message.document:
        file_id = message.document.file_id
        file_type = "document"
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
    elif message.video:
        file_id = message.video.file_id
        file_type = "video"
    else:
        await message.reply_text("❌ Fayl turi qo'llab-quvvatlanmaydi!")
        return
    
    materials = get_materials()
    materials[num] = {
        "title": title,
        "description": description,
        "file_id": file_id,
        "type": file_type
    }
    save_json(MATERIALS_FILE, materials)
    
    await message.reply_text(
        f"✅ Material saqlandi!\n\n"
        f"🔢 Raqam: *{num}*\n"
        f"📌 Sarlavha: *{title}*\n"
        f"📁 Turi: {file_type}",
        parse_mode="Markdown"
    )


async def delete_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Ruxsat yo'q.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Raqam kiriting: `/delete 5`", parse_mode="Markdown")
        return
    
    num = context.args[0]
    materials = get_materials()
    
    if num in materials:
        title = materials[num].get("title", "Nomsiz")
        del materials[num]
        save_json(MATERIALS_FILE, materials)
        await update.message.reply_text(f"🗑 *{num}* — {title} o'chirildi.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ {num} raqamli material topilmadi.")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Ruxsat yo'q.")
        return
    
    materials = get_materials()
    admins = get_admins()
    
    doc_count = sum(1 for m in materials.values() if m.get("type") == "document")
    photo_count = sum(1 for m in materials.values() if m.get("type") == "photo")
    video_count = sum(1 for m in materials.values() if m.get("type") == "video")
    
    text = (
        "📊 *Statistika*\n\n"
        f"📦 Jami materiallar: *{len(materials)}*\n"
        f"  📄 Hujjatlar: {doc_count}\n"
        f"  🖼 Rasmlar: {photo_count}\n"
        f"  🎥 Videolar: {video_count}\n\n"
        f"👥 Adminlar: {len(admins)}\n"
        f"🆔 Admin IDlar: {', '.join(str(a) for a in admins)}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ===================== MAIN =====================

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Foydalanuvchi komandalar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_materials))
    
    # Admin komandalar
    app.add_handler(CommandHandler("addme", add_me_as_admin))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("delete", delete_material))
    app.add_handler(CommandHandler("stats", stats))
    
    # Fayl yuklash (admin)
    app.add_handler(MessageHandler(
        filters.Document.ALL | filters.PHOTO | filters.VIDEO,
        handle_admin_file
    ))
    
    # Matn xabarlari (raqam)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("✅ Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
