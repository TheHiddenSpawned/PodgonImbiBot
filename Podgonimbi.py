import os
import asyncio
import asyncpg
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaDocument,
    InputMediaAudio
)
from aiogram.enums import ContentType
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram import F
from aiogram.exceptions import TelegramBadRequest
from threading import Thread
from http.server import SimpleHTTPRequestHandler, HTTPServer
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
DATABASE_URL = os.getenv("DATABASE_URL")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID not set")

CHANNEL_ID = int(CHANNEL_ID)

bot = Bot(TOKEN)
dp = Dispatcher()


class Form(StatesGroup):
    choosing_type = State()
    waiting_text = State()
    text_menu = State()        
    waiting_media = State()
    media_menu = State()       
    nickname = State()
    custom_nickname = State()
    delete_media = State()
    preview = State()
    edit_menu = State()
    admin_edit_text = State()
    admin_edit_nickname = State()
    admin_delete_media = State()


# ---------- INLINE КЛАВИАТУРЫ ----------

def start_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Прислать текст", callback_data="send_text")],
        [InlineKeyboardButton(text="📎 Прислать медиа", callback_data="send_media")]
    ])


def after_text_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 Добавить медиа", callback_data="add_media")],
        [InlineKeyboardButton(text="🚀 Опубликовать", callback_data="to_nick")],
        [
            InlineKeyboardButton(text="🔄 Назад", callback_data="back"),
            InlineKeyboardButton(text="🏠 В начало", callback_data="home")
        ]
    ])


def after_media_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Добавить текст", callback_data="add_text")],
        [InlineKeyboardButton(text="🗑 Удалить медиа", callback_data="delete_media")],
        [InlineKeyboardButton(text="🚀 Опубликовать", callback_data="to_nick")],
        [
            InlineKeyboardButton(text="🔄 Назад", callback_data="back"),
            InlineKeyboardButton(text="🏠 В начало", callback_data="home")
        ]
    ])


def nick_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ник из телеграмма", callback_data="my_nick")],
        [InlineKeyboardButton(text="Анонимно", callback_data="anon")],
         [InlineKeyboardButton(text="✏️ Ввести свой ник", callback_data="custom_nick")],
        [
            InlineKeyboardButton(text="🔄 Назад", callback_data="back"),
            InlineKeyboardButton(text="🏠 В начало", callback_data="home")
        ]
    ])

def preview_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Опубликовать", callback_data="confirm_publish")],
        [InlineKeyboardButton(text="✏️ Изменить", callback_data="edit_menu")],
        [
            InlineKeyboardButton(text="🔄 Назад", callback_data="back"),
            InlineKeyboardButton(text="🏠 В начало", callback_data="home")
        ]
    ])

def moderation_kb(submission_id, has_text: bool, has_media: bool):
    buttons = []

    if has_text:
        buttons.append(
            [InlineKeyboardButton(
                text="✏ Изменить текст",
                callback_data=f"edit_text_{submission_id}"
            )]
        )

    if has_media:
        buttons.append(
            [InlineKeyboardButton(
                text="🗑 Удалить медиа",
                callback_data=f"edit_media_{submission_id}"
            )]
        )

    buttons.append(
        [InlineKeyboardButton(
            text="👤 Изменить ник",
            callback_data=f"edit_nick_{submission_id}"
        )]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                text="✅ Опубликовать",
                callback_data=f"approve_{submission_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"reject_{submission_id}"
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def after_submit_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Прислать ещё подгон", callback_data="home")],
    ])

def edit_kb(has_text: bool, has_media: bool):
    buttons = []

    # Текст
    if has_text:
        buttons.append(
            [InlineKeyboardButton(text="✍️ Изменить текст", callback_data="edit_text")]
        )
    else:
        buttons.append(
            [InlineKeyboardButton(text="➕ Добавить текст", callback_data="add_text")]
        )

    # Медиа
    if has_media:
        buttons.append(
            [InlineKeyboardButton(text="🗑 Удалить медиа", callback_data="delete_media")]
        )

    buttons.append(
        [InlineKeyboardButton(text="📎 Добавить медиа", callback_data="add_media")]
    )

    # Ник
    buttons.append(
        [InlineKeyboardButton(text="👤 Изменить ник", callback_data="edit_nick_user")]
    )

    # Навигация
    buttons.append(
        [
            InlineKeyboardButton(text="🔄 Назад", callback_data="back"),
            InlineKeyboardButton(text="🏠 В начало", callback_data="home")
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)    

# ---------- СТАРТ ----------

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Кидай имбу 🔥\n\n"
        "Можно отправить:\n\n"
        "✍️ Текст — описание фишки, мысль, новость, в общем всё, что считаешь имбой\n\n"
        "📎 Медиа — скрин, видео, файл, голосовое, музыку и т.д.\n\n"
        "Можно отправить и текст, и медиа или что-то одно.",
        reply_markup=start_kb()
    )
    await state.set_state(Form.choosing_type)


# ---------- Одобрить ----------

@dp.callback_query(F.data.startswith("approve_"))
async def approve_handler(callback: CallbackQuery):

    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Не твоя кнопка 😎", show_alert=True)
        return

    submission_id = int(callback.data.split("_")[1])

    conn = await dp["db"].acquire()
    submission = await conn.fetchrow(
        "SELECT * FROM submissions WHERE id = $1",
        submission_id
    )

    if not submission:
        await dp["db"].release(conn)
        return

    caption = f"🔥 Новый подгон\n\n👤 {submission['nickname']}"

    if submission["text"]:
        caption += f"\n\n📝 {submission['text']}"

    media_list = json.loads(submission["media"]) if submission["media"] else []

    if media_list:
        first = True
        for media_type, file_id in media_list:
            if first:
                if media_type == "photo":
                    await bot.send_photo(CHANNEL_ID, file_id, caption=caption)
                elif media_type == "video":
                    await bot.send_video(CHANNEL_ID, file_id, caption=caption)
                elif media_type == "document":
                    await bot.send_document(CHANNEL_ID, file_id, caption=caption)
                elif media_type == "audio":
                    await bot.send_audio(CHANNEL_ID, file_id, caption=caption)
                elif media_type == "voice":
                    await bot.send_voice(CHANNEL_ID, file_id, caption=caption)
                first = False
            else:
                if media_type == "photo":
                    await bot.send_photo(CHANNEL_ID, file_id)
                elif media_type == "video":
                    await bot.send_video(CHANNEL_ID, file_id)
                elif media_type == "document":
                    await bot.send_document(CHANNEL_ID, file_id)
                elif media_type == "audio":
                    await bot.send_audio(CHANNEL_ID, file_id)
                elif media_type == "voice":
                    await bot.send_voice(CHANNEL_ID, file_id)
    else:
        await bot.send_message(CHANNEL_ID, caption)

    await conn.execute(
        "UPDATE submissions SET status = 'approved' WHERE id = $1",
        submission_id
    )

    await dp["db"].release(conn)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("Опубликовано ✅")

# ---------- Отклоить ----------

@dp.callback_query(F.data.startswith("reject_"))
async def reject_handler(callback: CallbackQuery):

    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Не твоя кнопка 😎", show_alert=True)
        return

    submission_id = int(callback.data.split("_")[1])

    conn = await dp["db"].acquire()

    await conn.execute(
        "UPDATE submissions SET status = 'rejected' WHERE id = $1",
        submission_id
    )

    await dp["db"].release(conn)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("Отклонено ❌")

# ---------- Редактировать текст ----------

@dp.callback_query(F.data.startswith("edit_text_"))
async def admin_edit_text_start(callback: CallbackQuery, state: FSMContext):

    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Не твоя кнопка 😎", show_alert=True)
        return

    submission_id = int(callback.data.split("_")[2])

    msg = await callback.message.answer(
        "✏ Введи новый текст для этого подгона:"
    )

    await state.update_data(
        admin_submission_id=submission_id,
        admin_prompt_message_id=msg.message_id,
        admin_panel_message_id=callback.message.message_id
    )

    await state.set_state(Form.admin_edit_text)

# ---------- Редактировать ник ----------

@dp.callback_query(F.data.startswith("edit_nick_"))
async def admin_edit_nickname_start(callback: CallbackQuery, state: FSMContext):

    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Не твоя кнопка 😎", show_alert=True)
        return

    submission_id = int(callback.data.split("_")[2])

    msg = await callback.message.answer(
        "✏️ Введи новый ник для этого подгона:"
    )

    await state.update_data(
        submission_id=submission_id,
        prompt_message_id=msg.message_id,
        panel_message_id=callback.message.message_id
    )

    await state.set_state(Form.admin_edit_nickname)

    await callback.answer()

# ---------- Редактировать медиа ----------

@dp.callback_query(F.data.startswith("edit_media_"))
async def admin_delete_media_start(callback: CallbackQuery, state: FSMContext):

    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Не твоя кнопка 😎", show_alert=True)
        return

    submission_id = int(callback.data.split("_")[2])

    conn = await dp["db"].acquire()
    submission = await conn.fetchrow(
        "SELECT * FROM submissions WHERE id = $1",
        submission_id
    )
    await dp["db"].release(conn)

    media_raw = submission["media"]

    if isinstance(media_raw, str):
        media_list = json.loads(media_raw)
    else:
        media_list = media_raw or []

    if not media_list:
        await callback.answer("Медиа нет ❌", show_alert=True)
        return

    msg = await callback.message.answer(
        f"🗑 Введи номер медиа для удаления (1–{len(media_list)}):"
    )

    await state.update_data(
        admin_submission_id=submission_id,
        admin_panel_message_id=callback.message.message_id,
        admin_prompt_message_id=msg.message_id
    )

    await state.set_state(Form.admin_delete_media)
    await callback.answer()

@dp.message(Form.admin_edit_text)
async def admin_edit_text_save(message: Message, state: FSMContext):

    if message.from_user.id != ADMIN_ID:
        return

    data = await state.get_data()
    submission_id = data.get("admin_submission_id")
    prompt_message_id = data.get("admin_prompt_message_id")
    panel_message_id = data.get("admin_panel_message_id")

    if not submission_id:
        await state.clear()
        return

    new_text = message.text

    conn = await dp["db"].acquire()

    # 🔹 Обновляем текст
    await conn.execute(
        "UPDATE submissions SET text = $1 WHERE id = $2",
        new_text,
        submission_id
    )

    # 🔹 Получаем обновлённую запись
    submission = await conn.fetchrow(
        "SELECT * FROM submissions WHERE id = $1",
        submission_id
    )

    await dp["db"].release(conn)

    # 🔹 Собираем новый caption
    caption = f"🔥 Новый подгон\n\n👤 {submission['nickname']}"

    if submission["text"]:
        caption += f"\n\n📝 {submission['text']}"

    media_raw = submission["media"]

    if isinstance(media_raw, str):
        media_list = json.loads(media_raw)
    else:
        media_list = media_raw or []

    # 🔹 Перерисовываем карточку
    try:
        if len(media_list) > 0:
            await bot.edit_message_caption(
                caption=caption,
                chat_id=message.chat.id,
                message_id=panel_message_id,
                reply_markup=moderation_kb(
                    submission_id,
                    has_text=bool(submission["text"]),
                    has_media=True
                )
            )
        else:
            await bot.edit_message_text(
                caption,
                chat_id=message.chat.id,
                message_id=panel_message_id,
                reply_markup=moderation_kb(
                    submission_id,
                    has_text=bool(submission["text"]),
                    has_media=False
                )
            )
    except Exception as e:
        print("EDIT ERROR:", e)

    # 🔹 Удаляем сообщение админа
    await message.delete()

    # 🔹 Удаляем "Введите новый текст..."
    if prompt_message_id:
        try:
            await bot.delete_message(message.chat.id, prompt_message_id)
        except:
            pass

    # 🔹 Подтверждение
    confirm_msg = await message.answer("✅ Текст обновлён")
    await asyncio.sleep(2.5)

    try:
        await confirm_msg.delete()
    except:
        pass

    await state.clear()

@dp.message(Form.admin_delete_media)
async def admin_delete_media_process(message: Message, state: FSMContext):

    if message.from_user.id != ADMIN_ID:
        return

    if not message.text.isdigit():
        await message.answer("Нужно ввести цифру 👀")
        return

    index = int(message.text) - 1

    data = await state.get_data()
    submission_id = data.get("admin_submission_id")
    panel_message_id = data.get("admin_panel_message_id")
    prompt_message_id = data.get("admin_prompt_message_id")

    conn = await dp["db"].acquire()
    submission = await conn.fetchrow(
        "SELECT * FROM submissions WHERE id = $1",
        submission_id
    )

    media_raw = submission["media"]

    if isinstance(media_raw, str):
        media_list = json.loads(media_raw)
    else:
        media_list = media_raw or []

    if index < 0 or index >= len(media_list):
        await message.answer("Такого номера нет 😕")
        await dp["db"].release(conn)
        return

    media_list.pop(index)

    await conn.execute(
        "UPDATE submissions SET media = $1 WHERE id = $2",
        json.dumps(media_list),
        submission_id
    )

    submission = await conn.fetchrow(
        "SELECT * FROM submissions WHERE id = $1",
        submission_id
    )

    await dp["db"].release(conn)

    # --- новый caption ---
    caption = f"🔥 Новый подгон\n\n👤 {submission['nickname']}"

    if submission["text"]:
        caption += f"\n\n📝 {submission['text']}"

    try:
        if media_list:
            await bot.edit_message_caption(
                chat_id=message.chat.id,
                message_id=panel_message_id,
                caption=caption,
                reply_markup=moderation_kb(
                    submission_id,
                    has_text=bool(submission["text"]),
                    has_media=True
                )
            )
        else:
            await bot.edit_message_text(
                caption,
                chat_id=message.chat.id,
                message_id=panel_message_id,
                reply_markup=moderation_kb(
                    submission_id,
                    has_text=bool(submission["text"]),
                    has_media=False
                )
            )
    except Exception as e:
        print("ADMIN DELETE MEDIA ERROR:", e)

    # --- чистка ---
    await message.delete()

    if prompt_message_id:
        try:
            await bot.delete_message(message.chat.id, prompt_message_id)
        except:
            pass

    confirm_msg = await message.answer("✅ Медиа удалено!")
    await asyncio.sleep(2.5)

    try:
        await confirm_msg.delete()
    except:
        pass

    await state.clear()

# ---------- CALLBACK ОБРАБОТЧИК ----------

@dp.callback_query(F.data)
async def callbacks(callback: CallbackQuery, state: FSMContext):
    data = callback.data
    await callback.answer()

    async def safe_edit(text, markup):
        try:
            await callback.message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise

    async def go(new_state):
        current = await state.get_state()
        user_data = await state.get_data()
        history = user_data.get("history", [])

        if current:
            history.append(current)

        await state.update_data(history=history)
        await state.set_state(new_state)

    # ---------------- HOME ----------------
    if data == "home":
        await state.clear()
        await safe_edit(
            "Кидай имбу 🔥\n\n"
            "Можно отправить:\n\n"
            "✍️ Текст — описание фишки, мысль, новость, в общем всё, что считаешь имбой\n\n"
            "📎 Медиа — скрин, видео, файл и т.д.\n\n"
            "Можно отправить и текст, и медиа или что-то одно.",
            start_kb()
        )
        await state.set_state(Form.choosing_type)
        return

    # ---------------- BACK ----------------
    elif data == "back":

        user_data = await state.get_data()
        history = user_data.get("history", [])

        if not history:
            return

        prev_state = history.pop()
        await state.update_data(history=history)
        await state.set_state(prev_state)

        if prev_state == Form.choosing_type:
            await safe_edit(
                "Кидай имбу 🔥\n\n"
                "Можно отправить:\n\n"
                "✍️ Текст — описание фишки, мысль, новость, в общем всё, что считаешь имбой\n\n"
                "📎 Медиа — скрин, видео и т.д.\n\n"
                "Можно отправить и текст, и медиа или что-то одно.",
                start_kb()
            )

        elif prev_state == Form.waiting_text:
            await safe_edit(
                "Отправь текст ✍️",
                InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Назад", callback_data="back")],
                    [InlineKeyboardButton(text="🏠 В начало", callback_data="home")]
                ])
            )

        elif prev_state == Form.text_menu:
            await safe_edit(
                "Текст сохранён ✅\nХочешь добавить медиа или перейти дальше?",
                after_text_kb()
            )

        elif prev_state == Form.waiting_media:
            await safe_edit(
                "Отправь медиа 📎 (можно несколько подряд)",
                InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Назад", callback_data="back")],
                [InlineKeyboardButton(text="🏠 В начало", callback_data="home")]
                ])
            )

        elif prev_state == Form.media_menu:
            user_data = await state.get_data()
            media = user_data.get("media", [])

            await safe_edit(
                f"Медиа добавлено ({len(media)}/10) ✅\n"
                "Можешь отправить ещё или перейти дальше.",
                after_media_kb()
        )

        elif prev_state == Form.nickname:
            await safe_edit(
                "Как подписать подгон?",
                nick_kb()
            )

        elif prev_state == Form.custom_nickname:
            await safe_edit(
                "Введи ник или подпись 👇",
                InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Назад", callback_data="back")],
                    [InlineKeyboardButton(text="🏠 В начало", callback_data="home")]
                ])
            )

        elif prev_state == Form.preview:
            await safe_edit(
                "Публикуем?",
                preview_kb()
            )
        elif prev_state == Form.edit_menu:
            user_data = await state.get_data()
            has_text = bool(user_data.get("text"))
            has_media = bool(user_data.get("media"))

            await safe_edit(
                "Что хочешь изменить?",
                edit_kb(has_text, has_media)
            )

    elif data == "edit_menu":
        user_data = await state.get_data()

        has_text = bool(user_data.get("text"))
        has_media = bool(user_data.get("media"))

        await go(Form.edit_menu)

        await safe_edit(
            "Что хочешь изменить?",
            edit_kb(has_text, has_media)
        )
        return

    # ---------------- TEXT ----------------
    if data in ["send_text", "add_text"]:
        await go(Form.waiting_text)

        await safe_edit(
            "Отправь текст ✍️",
            InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Назад", callback_data="back")],
                [InlineKeyboardButton(text="🏠 В начало", callback_data="home")]
            ])
        )
        return

    # ---------------- NEW TEXT ----------------
    if data == "edit_text":
        await go(Form.waiting_text)

        await safe_edit(
            "Отправь новый текст ✍️",
            InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Назад", callback_data="back")],
                [InlineKeyboardButton(text="🏠 В начало", callback_data="home")]
            ])
        )
        return

    # ---------------- MEDIA ----------------
    if data == "send_media":
        await state.update_data(media=[])
        await go(Form.waiting_media)

        await safe_edit(
            "Отправь медиа 📎 (можно несколько подряд)",
            InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Назад", callback_data="back")],
            [InlineKeyboardButton(text="🏠 В начало", callback_data="home")]
            ])
        )
        return


    if data == "add_media":
        await go(Form.waiting_media)

        await safe_edit(
            "Отправь медиа 📎 (можно несколько подряд)",
            InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Назад", callback_data="back")],
                [InlineKeyboardButton(text="🏠 В начало", callback_data="home")]
            ])
        )
        return

    # ---------------- EDIT NICK USER ----------------

    elif data == "edit_nick_user":

        # сбрасываем старый ник
        await state.update_data(final_nick=None)

        await go(Form.nickname)

        await safe_edit(
            "Как подписать подгон?",
            nick_kb()
        )
        return
    
    # ---------------- TO NICK ----------------
    elif data == "to_nick":
        user_data = await state.get_data()

        # если ник уже выбран — сразу превью
        if user_data.get("final_nick"):
            await go(Form.preview)

            nickname = user_data.get("final_nick")
            caption = f"🔥 Вот как будет выглядеть пост:\n\n👤 {nickname}"

            if user_data.get("text"):
                caption += f"\n\n📝 {user_data['text']}"

            media_list = user_data.get("media", [])

            try:
                await callback.message.delete()
            except:
                pass

            if media_list:
                first = True
                for media_type, file_id in media_list:
                    if first:
                        if media_type == "photo":
                            await bot.send_photo(callback.from_user.id, file_id, caption=caption)
                        elif media_type == "video":
                            await bot.send_video(callback.from_user.id, file_id, caption=caption)
                        elif media_type == "document":
                            await bot.send_document(callback.from_user.id, file_id, caption=caption)
                        elif media_type == "audio":
                            await bot.send_audio(callback.from_user.id, file_id, caption=caption)
                        elif media_type == "voice":
                            await bot.send_voice(callback.from_user.id, file_id, caption=caption)
                        first = False
                    else:
                        if media_type == "photo":
                            await bot.send_photo(callback.from_user.id, file_id)
                        elif media_type == "video":
                            await bot.send_video(callback.from_user.id, file_id)
                        elif media_type == "document":
                            await bot.send_document(callback.from_user.id, file_id)
                        elif media_type == "audio":
                            await bot.send_audio(callback.from_user.id, file_id)
                        elif media_type == "voice":
                            await bot.send_voice(callback.from_user.id, file_id)
            else:
                await bot.send_message(callback.from_user.id, caption)

            await bot.send_message(
                callback.from_user.id,
                "Публикуем?",
                reply_markup=preview_kb()
            )

            return

        # 🔥 ВОТ ЭТО ТЫ УДАЛИЛ — И НАДО ВЕРНУТЬ
        await go(Form.nickname)

        await safe_edit(
            "Как подписать подгон?",
            nick_kb()
        )
        return
        
        # ---------- DELETE MEDIA ----------
    if data == "delete_media":

        user_data = await state.get_data()
        media_list = user_data.get("media", [])

        if not media_list:
            await callback.message.answer("❌ Медиа пока нет.")
            return

        await state.set_state(Form.delete_media)

        await callback.message.answer(
            f"🗑 Какое по счёту медиа удалить? (1–{len(media_list)})\n"
            "Просто напиши цифру."
        )
        return

    # ---------------- CUSTOM NICK ----------------
    if data == "custom_nick":
        await go(Form.custom_nickname)

        await safe_edit(
            "Введи ник или подпись 👇",
            InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Назад", callback_data="back")],
                [InlineKeyboardButton(text="🏠 В начало", callback_data="home")]
            ])
        )
        return

    # Ник
    if data in ["my_nick", "anon"] or data == "publish_custom":

        user_data = await state.get_data()

        # определяем ник
        if data == "my_nick":
            nickname = (
                f"@{callback.from_user.username}"
                if callback.from_user.username
                else callback.from_user.full_name
            )
        else:
            nickname = "Аноним"

        if user_data.get("custom_nick"):
            nickname = user_data.get("custom_nick")
        await state.update_data(final_nick=nickname)

        caption = f"🔥 Вот как будет выглядеть пост:\n\n👤 {nickname}"


        if user_data.get("text"):
            caption += f"\n\n📝 {user_data['text']}"

        media_list = user_data.get("media", [])

        if media_list:
            first = True
            for media_type, file_id in media_list:
                if first:
                    if media_type == "photo":
                        await bot.send_photo(callback.from_user.id, file_id, caption=caption)
                    elif media_type == "video":
                        await bot.send_video(callback.from_user.id, file_id, caption=caption)
                    elif media_type == "document":
                        await bot.send_document(callback.from_user.id, file_id, caption=caption)
                    elif media_type == "audio":
                        await bot.send_audio(callback.from_user.id, file_id, caption=caption)
                    elif media_type == "voice":
                        await bot.send_voice(callback.from_user.id, file_id, caption=caption)
                    first = False
                else:
                    if media_type == "photo":
                                await bot.send_photo(callback.from_user.id, file_id)
                    elif media_type == "video":
                        await bot.send_video(callback.from_user.id, file_id)
                    elif media_type == "document":
                        await bot.send_document(callback.from_user.id, file_id)
                    elif media_type == "audio":
                        await bot.send_audio(callback.from_user.id, file_id)
                    elif media_type == "voice":
                        await bot.send_voice(callback.from_user.id, file_id)
        else:
            await callback.message.answer(caption)

        await callback.message.answer(
            "Публикуем?",
            reply_markup=preview_kb()
        )

        await go(Form.preview)
        return
    
    # ---------- ПОДТВЕРЖДЕНИЕ ПУБЛИКАЦИИ ----------

    if data == "confirm_publish":

        user_data = await state.get_data()

        nickname = user_data.get("final_nick")

        caption = f"🔥 Новый подгон\n\n👤 {nickname}"

        if user_data.get("text"):
            caption += f"\n\n📝 {user_data['text']}"

        media_list = user_data.get("media", [])

        conn = await dp["db"].acquire()

        submission_id = await conn.fetchval("""
            INSERT INTO submissions (telegram_id, username, nickname, text, media)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """,
            callback.from_user.id,
            callback.from_user.username,
            nickname,
            user_data.get("text"),
            json.dumps(media_list)
        )

        await dp["db"].release(conn)

        if media_list:

            from aiogram.types import InputMediaPhoto, InputMediaVideo

            photos_videos = []
            others = []

            for media_type, file_id in media_list:
                if media_type in ["photo", "video"]:
                    photos_videos.append((media_type, file_id))
                else:
                    others.append((media_type, file_id))

            # 1️⃣ Отправляем альбом фото/видео
            if photos_videos:
                media_group = []

                for i, (media_type, file_id) in enumerate(photos_videos):
                    if media_type == "photo":
                        media_group.append(
                            InputMediaPhoto(
                                media=file_id,
                                caption=caption if i == 0 else None
                            )
                        )
                    else:
                        media_group.append(
                            InputMediaVideo(
                                media=file_id,
                                caption=caption if i == 0 else None
                            )
                        )

                await bot.send_media_group(
                    chat_id=ADMIN_ID,
                    media=media_group
                )

            else:
                # если нет фото/видео — отправляем текст отдельно
                await bot.send_message(
                    ADMIN_ID,
                    caption
                )

            # 2️⃣ Отправляем остальные файлы
            for media_type, file_id in others:

                send_func = {
                    "document": bot.send_document,
                    "audio": bot.send_audio,
                    "voice": bot.send_voice,
                }.get(media_type)

                if send_func:
                    await send_func(ADMIN_ID, file_id)

            # 3️⃣ Отдельное сообщение с кнопками модерации
            await bot.send_message(
                ADMIN_ID,
                "⬇️ Модерация",
                reply_markup=moderation_kb(
                    submission_id,
                    has_text=bool(user_data.get("text")),
                    has_media=True
                )
            )

        else:
            await bot.send_message(
                ADMIN_ID,
                caption,
                reply_markup=moderation_kb(
                    submission_id,
                    has_text=bool(user_data.get("text")),
                    has_media=False
                )
            )
        # --- ЧИСТИМ ПОЛЬЗОВАТЕЛЬСКИЙ СРАЧ ---

        try:
            # удаляем сообщение с кнопкой "Публикуем?"
            await callback.message.delete()
        except:
            pass

        # удаляем 10 последних сообщений бота (которые могли быть предпросмотром)
        for i in range(1, 15):
            try:
                await bot.delete_message(callback.from_user.id, callback.message.message_id - i)
            except:
                pass
        await state.clear()

        await callback.message.answer(
            "🔥 Подгон отправлен на модерацию!\n\n"
            "Хочешь прислать ещё один?",
            reply_markup=after_submit_kb()
        )
        return

# ---------- ТЕКСТ ----------

@dp.message(Form.waiting_text)
async def get_text(message: Message, state: FSMContext):

    if message.content_type != ContentType.TEXT:
        await message.answer("Сейчас нужен текст ✍️")
        return   

    await state.update_data(text=message.text)

    user_data = await state.get_data()

    # если уже есть ник — значит это редактирование перед публикацией
    if user_data.get("final_nick"):

        nickname = user_data.get("final_nick")
        caption = f"🔥 Вот как будет выглядеть пост:\n\n👤 {nickname}"

        if user_data.get("text"):
            caption += f"\n\n📝 {user_data['text']}"

        media_list = user_data.get("media", [])

        if media_list:
            first = True
            for media_type, file_id in media_list:
                if first:
                    if media_type == "photo":
                        await bot.send_photo(message.from_user.id, file_id, caption=caption)
                    elif media_type == "video":
                        await bot.send_video(message.from_user.id, file_id, caption=caption)
                    elif media_type == "document":
                        await bot.send_document(message.from_user.id, file_id, caption=caption)
                    elif media_type == "audio":
                        await bot.send_audio(message.from_user.id, file_id, caption=caption)
                    elif media_type == "voice":
                        await bot.send_voice(message.from_user.id, file_id, caption=caption)
                    first = False
                else:
                    if media_type == "photo":
                        await bot.send_photo(message.from_user.id, file_id)
                    elif media_type == "video":
                        await bot.send_video(message.from_user.id, file_id)
                    elif media_type == "document":
                        await bot.send_document(message.from_user.id, file_id)
                    elif media_type == "audio":
                        await bot.send_audio(message.from_user.id, file_id)
                    elif media_type == "voice":
                        await bot.send_voice(message.from_user.id, file_id)
        else:
            await message.answer(caption)

        await message.answer(
            "Публикуем?",
            reply_markup=preview_kb()
        )

        await go(Form.preview)
        return

    # если это первый ввод текста
    await state.set_state(Form.text_menu)

    await message.answer(
        "Текст сохранён ✅\nХочешь добавить медиа или перейти дальше?",
        reply_markup=after_text_kb()
    )

# ---------- ПОКАЗ ПРЕВЬЮ ---------

@dp.callback_query(F.data == "back_to_preview")
async def back_to_preview(callback: CallbackQuery, state: FSMContext):

    user_data = await state.get_data()

    nickname = user_data.get("final_nick")
    caption = f"🔥 Вот как будет выглядеть пост:\n\n👤 {nickname}"

    if user_data.get("text"):
        caption += f"\n\n📝 {user_data['text']}"

    media_list = user_data.get("media", [])

    if media_list:
        first = True
        for media_type, file_id in media_list:
            if first:
                if media_type == "photo":
                    await bot.send_photo(callback.from_user.id, file_id, caption=caption)
                elif media_type == "video":
                    await bot.send_video(callback.from_user.id, file_id, caption=caption)
                elif media_type == "document":
                    await bot.send_document(callback.from_user.id, file_id, caption=caption)
                elif media_type == "audio":
                    await bot.send_audio(callback.from_user.id, file_id, caption=caption)
                elif media_type == "voice":
                    await bot.send_voice(callback.from_user.id, file_id, caption=caption)
                first = False
            else:
                if media_type == "photo":
                    await bot.send_photo(callback.from_user.id, file_id)
                elif media_type == "video":
                    await bot.send_video(callback.from_user.id, file_id)
                elif media_type == "document":
                    await bot.send_document(callback.from_user.id, file_id)
                elif media_type == "audio":
                    await bot.send_audio(callback.from_user.id, file_id)
                elif media_type == "voice":
                    await bot.send_voice(callback.from_user.id, file_id)
    else:
        await callback.message.answer(caption)

    await callback.message.answer(
        "Публикуем?",
        reply_markup=preview_kb()
    )

    await go(Form.preview)
    await callback.answer()

# ---------- МЕДИА ----------

@dp.message(Form.waiting_media)
async def get_media(message: Message, state: FSMContext):

    if message.content_type not in [
        ContentType.PHOTO,
        ContentType.VIDEO,
        ContentType.DOCUMENT,
        ContentType.AUDIO,
        ContentType.VOICE
    ]:
        await message.answer("Сейчас нужно медиа 📎")
        return

    data = await state.get_data()
    media_list = data.get("media", [])

    # 🚫 ЛИМИТ 10
    if len(media_list) >= 10:
        await message.answer(
            "😒 Эй, хватит!\n\n"
            "Можно отправить максимум 10 файлов.\n"
            "Так что либо публикуй, либо удаляй один из файлов.",
            reply_markup=after_media_kb()
        )
        return

    if message.photo:
        media_list.append(("photo", message.photo[-1].file_id))

    elif message.video:
        media_list.append(("video", message.video.file_id))

    elif message.document:
        media_list.append(("document", message.document.file_id))

    elif message.audio:
        media_list.append(("audio", message.audio.file_id))

    elif message.voice:
        media_list.append(("voice", message.voice.file_id))

    await state.update_data(media=media_list)
    current = await state.get_state()
    user_data = await state.get_data()
    history = user_data.get("history", [])

    if current:
        history.append(current)

    await state.update_data(history=history)

    current_count = len(media_list)

    if current_count < 10:
        await message.answer(
            f"Медиа добавлено ({current_count}/10) ✅\n"
            "Можешь отправить ещё или перейти дальше.",
            reply_markup=after_media_kb()
        )
    else:
        await message.answer(
            "✅ Добавлено 10/10 медиа.\n\n"
            "Лимит достигнут. Теперь можешь перейти дальше.",
            reply_markup=after_media_kb()
        )
    
@dp.message(Form.delete_media)
async def process_delete_media(message: Message, state: FSMContext):

    if not message.text.isdigit():
        await message.answer("Нужно отправить цифру 👀")
        return

    index = int(message.text) - 1

    data = await state.get_data()
    media_list = data.get("media", [])

    if index < 0 or index >= len(media_list):
        await message.answer("Такого номера нет 😕")
        return

    media_list.pop(index)

    await state.update_data(media=media_list)

    current = await state.get_state()
    user_data = await state.get_data()
    history = user_data.get("history", [])

    if current:
        history.append(current)

    await state.update_data(history=history)
    await state.set_state(Form.media_menu)

    await message.answer(
        f"✅ Удалено медиа №{index + 1}\n"
        f"Осталось файлов: {len(media_list)}/10",
        reply_markup=after_media_kb()
    )    

@dp.message(Form.admin_edit_nickname)
async def admin_edit_nickname_save(message: Message, state: FSMContext):

    if message.from_user.id != ADMIN_ID:
        return

    data = await state.get_data()

    submission_id = data.get("submission_id")
    panel_message_id = data.get("panel_message_id")
    prompt_message_id = data.get("prompt_message_id")

    if not submission_id:
        await state.clear()
        return

    new_nickname = message.text.strip()

    conn = await dp["db"].acquire()

    # 🔹 Обновляем ник
    await conn.execute(
        "UPDATE submissions SET nickname = $1 WHERE id = $2",
        new_nickname,
        submission_id
    )

    # 🔹 Получаем обновлённую запись
    submission = await conn.fetchrow(
        "SELECT * FROM submissions WHERE id = $1",
        submission_id
    )

    await dp["db"].release(conn)

    # 🔹 Формируем caption
    caption = f"🔥 Новый подгон\n\n👤 {submission['nickname']}"

    if submission["text"]:
        caption += f"\n\n📝 {submission['text']}"

    media_raw = submission["media"]

    if isinstance(media_raw, str):
        media_list = json.loads(media_raw)
    else:
        media_list = media_raw or []

    # 🔹 Обновляем админскую карточку
    try:
        if len(media_list) > 0:
            await bot.edit_message_caption(
                chat_id=message.chat.id,
                message_id=panel_message_id,
                caption=caption,
                reply_markup=moderation_kb(
                    submission_id,
                    has_text=bool(submission["text"]),
                    has_media=True
                )
            )
        else:
            await bot.edit_message_text(
                caption,
                chat_id=message.chat.id,
                message_id=panel_message_id,
                reply_markup=moderation_kb(
                    submission_id,
                    has_text=bool(submission["text"]),
                    has_media=False
                )
            )
    except Exception as e:
        print("NICK EDIT ERROR:", e)

    # 🔹 Удаляем сообщение админа
    await message.delete()

    # 🔹 Удаляем "Введите новый ник"
    if prompt_message_id:
        try:
            await bot.delete_message(message.chat.id, prompt_message_id)
        except:
            pass

    # 🔹 Показываем уведомление
    confirm_msg = await message.answer("✅ Ник изменён!")
    await asyncio.sleep(2.5)

    try:
        await confirm_msg.delete()
    except:
        pass

    await state.clear()
    
# ---------- Ник ----------
@dp.message(Form.custom_nickname)
async def get_custom_nick(message: Message, state: FSMContext):

    if message.content_type != ContentType.TEXT:
        await message.answer("Нужен текстовый ник ✍️")
        return

    await state.update_data(custom_nick=message.text)
    user_data = await state.get_data()

    nickname = message.text
    await state.update_data(final_nick=nickname)

    caption = f"🔥 Вот как будет выглядеть пост:\n\n👤 {nickname}"

    if user_data.get("text"):
        caption += f"\n\n📝 {user_data['text']}"

    media_list = user_data.get("media", [])

    if media_list:
        first = True
        for media_type, file_id in media_list:
            if first:
                if media_type == "photo":
                    await bot.send_photo(message.from_user.id, file_id, caption=caption)
                elif media_type == "video":
                    await bot.send_video(message.from_user.id, file_id, caption=caption)
                elif media_type == "document":
                    await bot.send_document(message.from_user.id, file_id, caption=caption)
                elif media_type == "audio":
                    await bot.send_audio(message.from_user.id, file_id, caption=caption)
                elif media_type == "voice":
                    await bot.send_voice(message.from_user.id, file_id, caption=caption)
                first = False
            else:
                if media_type == "photo":
                    await bot.send_photo(message.from_user.id, file_id)
                elif media_type == "video":
                    await bot.send_video(message.from_user.id, file_id)
                elif media_type == "document":
                    await bot.send_document(message.from_user.id, file_id)
                elif media_type == "audio":
                    await bot.send_audio(message.from_user.id, file_id)
                elif media_type == "voice":
                    await bot.send_voice(message.from_user.id, file_id)
    else:
        await message.answer(caption)

    await message.answer(
        "Публикуем?",
        reply_markup=preview_kb()
    )

    await go(Form.preview)
    
async def create_pool():
    return await asyncpg.create_pool(DATABASE_URL)


# ---------- ЗАПУСК ----------

async def main():
    await bot.delete_webhook(drop_pending_updates=True)

    # 🔹 Сначала создаём пул
    dp["db"] = await create_pool()

    # 🔹 Создаём таблицы
    async with dp["db"].acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE,
                username TEXT
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT,
                username TEXT,
                nickname TEXT,
                text TEXT,
                media JSONB,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

    # 🔹 И ТОЛЬКО ПОТОМ запускаем polling
    await dp.start_polling(bot)

def run_http():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    server.serve_forever()


if __name__ == "__main__":
    Thread(target=run_http, daemon=True).start()
    asyncio.run(main())
