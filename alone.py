import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.markdown import html_decoration as hd # Xavfsiz formatlash uchun

# Token va Admin ID
TOKEN = "8692469958:AAH75IR4Wvo1fF4zxD1eH5P013KF72Y0cLY"
ADMIN_ID = 6650430442
ADMIN_USERNAME = "yaxzw"

# Majburiy obuna kanallari ro'yxati
REQUIRED_CHANNELS = [
    {
        "id": -1003468210313, 
        "url": "https://t.me/+T8AbrhJjGrthNDVi", 
        "name": {"uz": "1-Kanalga obuna bo'lish", "ru": "Подписаться на 1-й канал", "en": "Subscribe to Channel 1"}
    },
    {
        "id": -1004390081241, 
        "url": "https://t.me/alonebotnews", 
        "name": {"uz": "2-Kanalga obuna bo'lish (@alonebotnews)", "ru": "Подписаться на 2-й канал (@alonebotnews)", "en": "Subscribe to Channel 2 (@alonebotnews)"}
    }
]

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# --- BAZA BILAN ISHLASH (SQLite) ---
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            referred_by INTEGER,
            referrals INTEGER DEFAULT 0,
            received INTEGER DEFAULT 0,
            language TEXT DEFAULT 'ru'
        )
    """)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'ru'")
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    conn.close()

init_db()

def get_user(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, referred_by, referrals, received, language FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def add_user(user_id, username, referred_by=None):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, referred_by) VALUES (?, ?, ?)", (user_id, username, referred_by))
    conn.commit()
    conn.close()

def update_user_lang(user_id, lang):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()
    conn.close()

def update_referral(inviter_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (inviter_id,))
    conn.commit()
    conn.close()

def get_top_users():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, referrals FROM users ORDER BY referrals DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()
    return rows

def add_received_acc(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET received = received + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# Admin uchun FSM holatlari
class AdminStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_acc_info = State()

# Matnlar lug'ati (Tarjimalar)
translations = {
    'uz': {
        'sub_required': "❌ **DIQQAT! Kirish cheklangan!** 🔒\n\nBotdan foydalanish uchun quyidagi barcha rasmiy kanallarimizga obuna bo'lishingiz kerak. 👇\n\n✨ *Obuna bo'lgach «Obunani tekshirish» tugmasini bosing* 👇",
        'check_sub_btn': "🔄 Obunani tekshirish",
        'not_subscribed': "❌ Siz barcha kanalga obuna bo'lmadingiz! Davom etish uchun barchasiga obuna bo'ling.",
        'welcome': "👋 **Salom! FREE ACC BOT ga xush kelibsiz** 🚀\n\n🎁 *Bu yerda siz referallar evaziga bepul va zo'r akkauntlar olishingiz mumkin.* 💎\n\n👥 **Do'stlaringizni taklif qiling va shartlarni bajaring!** 🔥",
        'profile_btn': "👤 Mening profilim",
        'info_btn': "ℹ️ Batafsil ma'lumot",
        'rating_btn': "🏆 Haftalik reyting",
        'support_btn': "💬 Qo'llab-quvvatlash",
        'lang_btn': "🌐 Til / Language",
        'admin_btn': "⚙️ Admin panel",
        'info_text': "ℹ️ **BATAFSIL MA'LUMOT** ⚡️\n\n👥 *O'z referal havolangiz orqali foydalanuvchilarni taklif qiling va top akkauntlarni oling!* 🚀\n\n🎁 **Referallar uchun mukofotlar:** 🌟\n\n👤 **10 ta referal** → 🎮 *35+ LVL random akkaunt*\n👤 **20 ta referal** → 🎮 *50+ LVL random akkaunt*\n👤 **30 ta referal** → ❄️ *«Lednik» random akkaunt*\n👤 **40 ta referal** → 🔥 *OLD random akkaunt*",
        'profile_text': "👤 **MENING PROFILIM** 💎\n\n🆔 **ID:** `{}`\n👥 **Referallar:** `{}` ⚡️\n🎁 **Olingan akkauntlar:** `{}` 🏆\n\n🔗 **Sizning referal havolangiz:**\n`{}`",
        'empty_rating': "🏆 **HAFTALIK REYTING** ⚡️\n\n*Hozircha bo'sh. Birinchi bo'ling!* 🚀",
        'rating_title': "🏆 **TOP-10 HAFTALIK REFERALLAR** 🔥\n\n",
        'support_text': "💬 **QO'LLAB-QUVVATLASH** 🛠\n\n*Agar savollaringiz yoki muammolaringiz bo'lsa, administratorimizga murojaat qiling.* 📞\n\n👤 **Administrator:** @{} ⚡️\n\n📩 *Unga yozib, muammoingizni to'liq tushuntiring.*",
        'support_btn_link': "✍️ Administratorga yozish",
        'admin_stats': "📊 Statistikadagi top",
        'admin_give': "🎁 Akkaunt berish",
        'admin_panel_title': "⚙️ **Boshqaruv paneli** 🛠\n\n👥 **Bazadagi jami foydalanuvchilar:** `{}` ⚡️",
        'ask_user_id': "✍️ **Foydalanuvchining ID raqamini yuboring:** 🎯",
        'err_digit': "❌ **ID faqat raqamlardan iborat bo'lishi kerak. Qaytadan kiriting:**",
        'err_not_found': "❌ **Bunday foydalanuvchi bazada topilmadi. Qaytadan ID kiriting:**",
        'ask_acc_info': "🎁 **Endi foydalanuvchiga yuboriladigan akkaunt ma'lumotlarini (login/parol) yuboring:** 🚀",
        'acc_sent_success': "✅ **Akkaunt muvaffaqiyatli yuborildi va bazada qayd etildi!** 🎉",
        'acc_sent_err': "❌ **Xatolik: Ehtimol foydalanuvchi botni bloklagan.**",
        'choose_lang': "🌐 **Iltimos, tilni tanlang / Пожалуйста, выберите язык / Please select a language:**",
        'lang_changed': "✅ **Til muvaffaqiyatli o'zgartirildi!**"
    },
    'ru': {
        'sub_required': "❌ **ВНИМАНИЕ! Доступ ограничен!** 🔒\n\nЧтобы пользоваться ботом и получать бесплатные аккаунты, вы должны подписаться на все наши официальные каналы. 👇\n\n✨ *После подписки нажмите кнопку «Проверить подписку»* 👇",
        'check_sub_btn': "🔄 Проверить подписку",
        'not_subscribed': "❌ Вы подписались не на все каналы! Подпишитесь на все для продолжения.",
        'welcome': "👋 **Привет! Добро пожаловать в FREE ACC BOT** 🚀\n\n🎁 *Здесь ты можешь получить крутой аккаунт совершенно бесплатно за рефералов.* 💎\n\n👥 **Приглашай друзей по своей уникальной ссылке и выполняй простые условия!** 🔥",
        'profile_btn': "👤 Мой профиль",
        'info_btn': "ℹ️ Подробная информация",
        'rating_btn': "🏆 Недельный рейтинг",
        'support_btn': "💬 Поддержка",
        'lang_btn': "🌐 Язык / Language",
        'admin_btn': "⚙️ Админ панель",
        'info_text': "ℹ️ **ПОДРОБНАЯ ИНФОРМАЦИЯ** ⚡️\n\n👥 *Приглашай пользователей по своей реферальной ссылке и забирай топовые аккаунты!* 🚀\n\n🎁 **Награды за рефералов:** 🌟\n\n👤 **10 рефералов** → 🎮 *Рандом аккаунт 35+ LVL*\n👤 **20 рефералов** → 🎮 *Рандом аккаунт 50+ LVL*\n👤 **30 рефералов** → ❄️ *Рандом аккаунт «Ледник»*\n👤 **40 рефералов** → 🔥 *Рандом OLD аккаунт*",
        'profile_text': "👤 **МОЙ ПРОФИЛЬ** 💎\n\n🆔 **ID:** `{}`\n👥 **Рефералов:** `{}` ⚡️\n🎁 **Получено аккаунтов:** `{}` 🏆\n\n🔗 **Ваша реферальная ссылка:**\n`{}`",
        'empty_rating': "🏆 **НЕДЕЛЬНЫЙ РЕЙТИНГ** ⚡️\n\n*Пока пуст. Будьте первыми!* 🚀",
        'rating_title': "🏆 **ТОП-10 РЕФЕРАЛОВ НЕДЕЛИ** 🔥\n\n",
        'support_text': "💬 **ПОДДЕРЖКА** 🛠\n\n*Если у вас возникли вопросы или проблемы, обратитесь к нашему администратору.* 📞\n\n👤 **Администратор:** @{} ⚡️\n\n📩 *Напишите ему напрямую и подробно опишите свою проблему.*",
        'support_btn_link': "✍️ Написать администратору",
        'admin_stats': "📊 Топ пользователей",
        'admin_give': "🎁 Выдать аккаунт",
        'admin_panel_title': "⚙️ **Панель администратора** 🛠\n\n👥 **Всего пользователей в базе:** `{}` ⚡️",
        'ask_user_id': "✍️ **Отправьте ID пользователя:** 🎯",
        'err_digit': "❌ **ID должен состоять только из цифр. Введите заново:**",
        'err_not_found': "❌ **Такой пользователь не найден в базе. Введите ID заново:**",
        'ask_acc_info': "🎁 **Теперь отправьте данные аккаунта (логин/пароль) для отправки пользователю:** 🚀",
        'acc_sent_success': "✅ **Аккаунт успешно отправлен пользователю и зафиксирован в базе!** 🎉",
        'acc_sent_err': "❌ **Ошибка: Возможно, пользователь заблокировал бота.**",
        'choose_lang': "🌐 **Пожалуйста, выберите язык / Iltimos, tilni tanlang / Please select a language:**",
        'lang_changed': "✅ **Язык успешно изменен!**"
    },
    'en': {
        'sub_required': "❌ **ATTENTION! Access restricted!** 🔒\n\nYou must subscribe to all our official channels to use the bot. 👇\n\n✨ *After subscribing, click «Check subscription»* 👇",
        'check_sub_btn': "🔄 Check subscription",
        'not_subscribed': "❌ You are not subscribed to all channels yet! Please subscribe to all to continue.",
        'welcome': "👋 **Hello! Welcome to FREE ACC BOT** 🚀\n\n🎁 *Here you can get awesome accounts for free by inviting referrals.* 💎\n\n👥 **Invite friends using your unique link and complete simple conditions!** 🔥",
        'profile_btn': "👤 My Profile",
        'info_btn': "ℹ️ Detailed Info",
        'rating_btn': "🏆 Weekly Rating",
        'support_btn': "💬 Support",
        'lang_btn': "🌐 Language / Til",
        'admin_btn': "⚙️ Admin Panel",
        'info_text': "ℹ️ **DETAILED INFORMATION** ⚡️\n\n👥 *Invite users via your referral link and grab top accounts!* 🚀\n\n🎁 **Referral Rewards:** 🌟\n\n👤 **10 referrals** → 🎮 *Random account 35+ LVL*\n👤 **20 referrals** → 🎮 *Random account 50+ LVL*\n👤 **30 referrals** → ❄️ *Random account «Glacier»*\n👤 **40 referrals** → 🔥 *Random OLD account*",
        'profile_text': "👤 **MY PROFILE** 💎\n\n🆔 **ID:** `{}`\n👥 **Referrals:** `{}` ⚡️\n🎁 **Received accounts:** `{}` 🏆\n\n🔗 **Your referral link:**\n`{}`",
        'empty_rating': "🏆 **WEEKLY RATING** ⚡️\n\n*Empty for now. Be the first!* 🚀",
        'rating_title': "🏆 **TOP-10 WEEKLY REFERRALS** 🔥\n\n",
        'support_text': "💬 **SUPPORT** 🛠\n\n*If you have questions or problems, contact our administrator.* 📞\n\n👤 **Administrator:** @{} ⚡️\n\n📩 *Write to him directly and describe your problem.*",
        'support_btn_link': "✍️ Contact Administrator",
        'admin_stats': "📊 Top Users",
        'admin_give': "🎁 Give Account",
        'admin_panel_title': "⚙️ **Admin Panel** 🛠\n\n👥 **Total users in database:** `{}` ⚡️",
        'ask_user_id': "✍️ **Send user ID:** 🎯",
        'err_digit': "❌ **ID must contain only digits. Enter again:**",
        'err_not_found': "❌ **User not found in database. Enter ID again:**",
        'ask_acc_info': "🎁 **Now send account details (login/password) to send to the user:** 🚀",
        'acc_sent_success': "✅ **Account successfully sent to user and logged in database!** 🎉",
        'acc_sent_err': "❌ **Error: The user may have blocked the bot.**",
        'choose_lang': "🌐 **Please select a language / Iltimos, tilni tanlang:**",
        'lang_changed': "✅ **Language successfully changed!**"
    }
}

# Hamma kanallarga obunani tekshirish funksiyasi
async def check_subscription(user_id: int) -> bool:
    for channel in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel["id"], user_id=user_id)
            if member.status not in ["creator", "administrator", "member"]:
                return False
        except Exception:
            return False
    return True

# Asosiy menyu
def get_main_menu(user_id: int, lang='ru'):
    t = translations.get(lang, translations['ru'])
    builder = ReplyKeyboardBuilder()
    builder.row(
        types.KeyboardButton(text=t['profile_btn']),
        types.KeyboardButton(text=t['info_btn'])
    )
    builder.row(
        types.KeyboardButton(text=t['rating_btn']),
        types.KeyboardButton(text=t['support_btn'])
    )
    builder.row(
        types.KeyboardButton(text=t['lang_btn'])
    )
    if user_id == ADMIN_ID:
        builder.row(types.KeyboardButton(text=t['admin_btn']))
    return builder.as_markup(resize_keyboard=True)

# Barcha kanallar uchun obuna tugmalari
def get_sub_keyboard(lang='ru'):
    builder = InlineKeyboardBuilder()
    for channel in REQUIRED_CHANNELS:
        btn_text = channel["name"].get(lang, channel["name"]["ru"])
        builder.row(types.InlineKeyboardButton(text=btn_text, url=channel["url"]))
    
    t = translations.get(lang, translations['ru'])
    builder.row(types.InlineKeyboardButton(text=t['check_sub_btn'], callback_data="check_sub"))
    return builder.as_markup()

# Til tanlash tugmalari (Inline)
def get_lang_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
        types.InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
        types.InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")
    )
    return builder.as_markup()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or f"id{user_id}"
    args = message.text.split()
    
    user = get_user(user_id)
    if not user:
        inviter_id = None
        if len(args) > 1 and args[1].isdigit():
            potential_inviter = int(args[1])
            if potential_inviter != user_id and get_user(potential_inviter):
                if await check_subscription(user_id):
                    inviter_id = potential_inviter
                    update_referral(inviter_id)
                    try:
                        inviter_data = get_user(inviter_id)
                        inv_lang = inviter_data[5] if inviter_data else 'ru'
                        msg_text = "🎉 **Ура!** Новый реферал засчитан! ⚡️" if inv_lang=='ru' else ("🎉 **Ura!** Yangi referal qo'shildi! ⚡️" if inv_lang=='uz' else "🎉 **Hooray!** New referral counted! ⚡️")
                        await bot.send_message(inviter_id, msg_text, parse_mode="Markdown")
                    except Exception:
                        pass
        add_user(user_id, username, inviter_id)
        await message.answer(
            "🌐 **Iltimos, tilni tanlang / Пожалуйста, выберите язык / Please select a language:**",
            reply_markup=get_lang_keyboard(),
            parse_mode="Markdown"
        )
        return

    lang = user[5] if user[5] in translations else 'ru'
    t = translations[lang]

    if not await check_subscription(user_id):
        await message.answer(t['sub_required'], reply_markup=get_sub_keyboard(lang), parse_mode="Markdown")
        return

    await message.answer(t['welcome'], reply_markup=get_main_menu(user_id, lang), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("lang_"))
async def process_language_selection(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = callback.data.split("_")[1]
    
    if not get_user(user_id):
        add_user(user_id, callback.from_user.username or f"id{user_id}")
    update_user_lang(user_id, lang)
    
    t = translations[lang]
    await callback.message.delete()
    
    if not await check_subscription(user_id):
        await callback.message.answer(t['sub_required'], reply_markup=get_sub_keyboard(lang), parse_mode="Markdown")
        return

    await callback.message.answer(
        f"{t['lang_changed']}\n\n{t['welcome']}",
        reply_markup=get_main_menu(user_id, lang),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "check_sub")
async def process_check_sub(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    lang = user[5] if user and user[5] in translations else 'ru'
    t = translations[lang]

    if await check_subscription(user_id):
        await callback.message.delete()
        await callback.message.answer(t['welcome'], reply_markup=get_main_menu(user_id, lang), parse_mode="Markdown")
    else:
        await callback.answer(t['not_subscribed'], show_alert=True)

@dp.message(F.text.in_(["🌐 Язык / Language", "🌐 Til / Language", "🌐 Language / Til"]))
async def change_lang_handler(message: types.Message):
    await message.answer(
        "🌐 **Iltimos, tilni tanlang / Пожалуйста, выберите язык / Please select a language:**",
        reply_markup=get_lang_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(F.text.in_([translations['uz']['info_btn'], translations['ru']['info_btn'], translations['en']['info_btn']]))
async def info_handler(message: types.Message):
    user = get_user(message.from_user.id)
    lang = user[5] if user else 'ru'
    t = translations[lang]

    if not await check_subscription(message.from_user.id):
        await message.answer(t['sub_required'], reply_markup=get_sub_keyboard(lang), parse_mode="Markdown")
        return

    await message.answer(t['info_text'], parse_mode="Markdown")

@dp.message(F.text.in_([translations['uz']['profile_btn'], translations['ru']['profile_btn'], translations['en']['profile_btn']]))
async def profile_handler(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    lang = user[5] if user else 'ru'
    t = translations[lang]

    if not await check_subscription(user_id):
        await message.answer(t['sub_required'], reply_markup=get_sub_keyboard(lang), parse_mode="Markdown")
        return

    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    
    profile_text = t['profile_text'].format(user_id, user[3], user[4], ref_link)
    await message.answer(profile_text, parse_mode="Markdown")

@dp.message(F.text.in_([translations['uz']['rating_btn'], translations['ru']['rating_btn'], translations['en']['rating_btn']]))
async def weekly_rating(message: types.Message):
    user = get_user(message.from_user.id)
    lang = user[5] if user else 'ru'
    t = translations[lang]

    if not await check_subscription(message.from_user.id):
        await message.answer(t['sub_required'], reply_markup=get_sub_keyboard(lang), parse_mode="Markdown")
        return

    top_users = get_top_users()
    if not top_users:
        await message.answer(t['empty_rating'], parse_mode="Markdown")
        return

    rating_text = t['rating_title']
    for index, (uid, uname, refs) in enumerate(top_users, start=1):
        medal = "🥇" if index == 1 else "🥈" if index == 2 else "🥉" if index == 3 else f"🔹 {index}."
        
        # MUAMMONI HAL QILISH: Username ichidagi maxsus belgilarni (Markdown ni buzmasligi uchun) tozalaymiz
        safe_uname = uname.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
        
        rating_text += f"{medal} **@{safe_uname}** — 👥 `{refs}`\n"

    await message.answer(rating_text, parse_mode="Markdown")

@dp.message(F.text.in_([translations['uz']['support_btn'], translations['ru']['support_btn'], translations['en']['support_btn']]))
async def support_handler(message: types.Message):
    user = get_user(message.from_user.id)
    lang = user[5] if user else 'ru'
    t = translations[lang]

    if not await check_subscription(message.from_user.id):
        await message.answer(t['sub_required'], reply_markup=get_sub_keyboard(lang), parse_mode="Markdown")
        return

    support_text = t['support_text'].format(ADMIN_USERNAME)
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text=t['support_btn_link'], url=f"https://t.me/{ADMIN_USERNAME}"))
    await message.answer(support_text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.message(F.text.in_([translations['uz']['admin_btn'], translations['ru']['admin_btn'], translations['en']['admin_btn']]))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    user = get_user(message.from_user.id)
    lang = user[5] if user else 'ru'
    t = translations[lang]

    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    conn.close()

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text=t['admin_stats'], callback_data="admin_stats"))
    builder.row(types.InlineKeyboardButton(text=t['admin_give'], callback_data="admin_give_acc"))
    
    await message.answer(
        t['admin_panel_title'].format(total_users),
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    top_users = get_top_users()
    text = "📊 **Top users in database:** 💎\n\n"
    for uid, uname, refs in top_users[:10]:
        safe_uname = uname.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
        text += f"🆔 `{uid}` | **@{safe_uname}** | 👥 `{refs}`\n"
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_give_acc")
async def admin_give_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    await callback.message.answer("✍️ **Foydalanuvchining ID raqamini yuboring / Отправьте ID пользователя:** 🎯", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_user_id)
    await callback.answer()

@dp.message(AdminStates.waiting_for_user_id)
async def process_admin_user_id(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    if not message.text.isdigit():
        await message.answer("❌ **ID faqat raqamlardan iborat bo'lishi kerak / ID должен состоять только из цифр:**", parse_mode="Markdown")
        return
    
    target_id = int(message.text)
    if not get_user(target_id):
        await message.answer("❌ **Bunday foydalanuvchi topilmadi / Пользователь не найден:**", parse_mode="Markdown")
        return

    await state.update_data(target_id=target_id)
    await message.answer("🎁 **Akkaunt ma'lumotlarini (login/parol) yuboring / Отправьте данные аккаунта:** 🚀", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_acc_info)

@dp.message(AdminStates.waiting_for_acc_info)
async def process_admin_acc_info(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    data = await state.get_data()
    target_id = data.get("target_id")
    acc_info = message.text

    add_received_acc(target_id)
    target_user = get_user(target_id)
    t_lang = target_user[5] if target_user and target_user[5] in translations else 'ru'

    congrats_text = {
        'uz': f"🎁 **Tabriklaymiz! Admin sizga akkaunt taqdim etdi:** 💎\n\n{acc_info}",
        'ru': f"🎁 **Поздравляем! Администратор выдал вам аккаунт:** 💎\n\n{acc_info}",
        'en': f"🎁 **Congratulations! Administrator gave you an account:** 💎\n\n{acc_info}"
    }

    try:
        await bot.send_message(target_id, congrats_text[t_lang], parse_mode="Markdown")
        await message.answer("✅ **Muvaffaqiyatli yuborildi!** 🎉", parse_mode="Markdown")
    except Exception:
        await message.answer("❌ **Xatolik: Foydalanuvchi bloklagan bo'lishi mumkin.**", parse_mode="Markdown")
    
    await state.clear()

async def main():
    print("Bot xatolik tuzatilgan holda ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())