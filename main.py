import telebot
from telebot import types
import sqlite3
from datetime import datetime
import os
from dotenv import load_dotenv
import logging
import time

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Загружаем переменные окружения из .env файла
load_dotenv()

# ===== ПОЛУЧАЕМ ТОКЕН ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ =====
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))

if not BOT_TOKEN:
    raise Exception("❌ Токен не найден! Создайте файл .env с BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)


# ===== ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ =====
def init_db():
    """Создание всех необходимых таблиц в базе данных"""
    conn = sqlite3.connect('oge_bot.db')
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            joined_date TEXT,
            last_activity TEXT,
            is_admin INTEGER DEFAULT 0,
            total_tasks_completed INTEGER DEFAULT 0,
            correct_answers INTEGER DEFAULT 0
        )
    ''')

    # Таблица результатов задач
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            topic TEXT,
            question TEXT,
            user_answer TEXT,
            correct_answer TEXT,
            is_correct INTEGER,
            timestamp TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    # Таблица для логирования действий
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            timestamp TEXT
        )
    ''')

    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")


# ===== ФУНКЦИИ ДЛЯ ЗАПИСИ ДАННЫХ В БД =====
def save_user_to_db(user):
    """Запись/обновление информации о пользователе"""
    conn = sqlite3.connect('oge_bot.db')
    cursor = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    is_admin = 1 if user.id == ADMIN_ID else 0
    try:
        cursor.execute("""
            INSERT INTO users 
            (user_id, username, first_name, last_name, joined_date, last_activity, is_admin) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                last_activity = excluded.last_activity
        """, (user.id, user.username, user.first_name, user.last_name, now, now, is_admin))

        conn.commit()
        logger.info(f"✅ Пользователь {user.first_name} (ID: {user.id}) сохранен в БД")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения пользователя: {e}")
    finally:
        conn.close()

    log_user_action(user.id, "user_saved", f"Пользователь {user.first_name} сохранен в БД")


def save_user_result(user_id, topic, question, user_answer, correct_answer, is_correct):
    """Запись результата выполнения задания"""
    conn = sqlite3.connect('oge_bot.db')
    cursor = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO results 
        (user_id, topic, question, user_answer, correct_answer, is_correct, timestamp) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, topic, question, user_answer, correct_answer, 1 if is_correct else 0, now))

    # Обновляем статистику пользователя
    cursor.execute("""
        UPDATE users 
        SET total_tasks_completed = total_tasks_completed + 1,
            correct_answers = correct_answers + ?
        WHERE user_id = ?
    """, (1 if is_correct else 0, user_id))

    conn.commit()
    conn.close()

    result_text = "правильно" if is_correct else "неправильно"
    log_user_action(user_id, "task_completed", f"Задача по теме {topic}: {result_text}")


def log_user_action(user_id, action, details=""):
    """Логирование действий пользователя"""
    conn = sqlite3.connect('oge_bot.db')
    cursor = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO user_actions (user_id, action, details, timestamp) 
        VALUES (?, ?, ?, ?)
    """, (user_id, action, details, now))

    conn.commit()
    conn.close()


def get_user_stats(user_id):
    """Получение статистики пользователя из БД"""
    conn = sqlite3.connect('oge_bot.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT total_tasks_completed, correct_answers, joined_date, last_activity 
        FROM users WHERE user_id = ?
    """, (user_id,))
    user_data = cursor.fetchone()

    cursor.execute("""
        SELECT topic, COUNT(*) as total, SUM(is_correct) as correct 
        FROM results WHERE user_id = ? GROUP BY topic
    """, (user_id,))
    topic_results = cursor.fetchall()

    conn.close()
    return user_data, topic_results


# ===== БАЗА ЗАДАЧ =====
tasks_db = {
    "Информатика": [
        {
            "question": "Сколько бит в одном байте?",
            "answer": "8",
            "explain": "1 байт = 8 бит"
        },
        {
            "question": "Сколько байт в 1 Кбайте?",
            "answer": "1024",
            "explain": "1 Кбайт = 1024 байта"
        }
    ],
    "Логика": [
        {
            "question": "Чему равно 1 AND 0?",
            "answer": "0",
            "explain": "Конъюнкция (И) - 1 только если оба операнда равны 1"
        },
        {
            "question": "Чему равно 1 OR 0?",
            "answer": "1",
            "explain": "Дизъюнкция (ИЛИ) - 1 если хотя бы один операнд равен 1"
        }
    ],
    "Алгоритмы": [
        {
            "question": "Что такое алгоритм?",
            "answer": "последовательность действий",
            "explain": "Алгоритм - это точная последовательность действий для достижения цели"
        }
    ],
    "Файлы": [
        {
            "question": "Какое расширение у текстовых файлов?",
            "answer": "txt",
            "explain": ".txt - текстовые файлы"
        }
    ]
}


# ===== КЛАВИАТУРЫ =====
def main_menu(user_id=None):
    """Главное меню с 5+ кнопками"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    # 5 основных кнопок для всех пользователей
    btn1 = types.KeyboardButton("📚 Справочник")
    btn2 = types.KeyboardButton("📝 Задачи")
    btn3 = types.KeyboardButton("📊 Результаты")
    btn4 = types.KeyboardButton("ℹ️ О боте")
    btn5 = types.KeyboardButton("❓ Помощь")
    markup.add(btn1, btn2, btn3, btn4, btn5)

    # Дополнительные кнопки для администратора
    if user_id and user_id == ADMIN_ID:
        admin_btn1 = types.KeyboardButton("📈 Статистика бота")
        admin_btn2 = types.KeyboardButton("👥 Пользователи")
        admin_btn3 = types.KeyboardButton("📋 Логи действий")
        markup.add(admin_btn1, admin_btn2, admin_btn3)

    return markup


def topics_menu():
    """Меню выбора темы"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = []
    for topic in tasks_db.keys():
        buttons.append(types.KeyboardButton(f"🔹 {topic}"))
    buttons.append(types.KeyboardButton("◀️ Назад в меню"))
    markup.add(*buttons)
    return markup


# ===== ХРАНЕНИЕ СОСТОЯНИЙ ПОЛЬЗОВАТЕЛЕЙ =====
user_sessions = {}


# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С ЗАДАЧАМИ =====
def send_task(chat_id, user_id):
    """Отправка текущей задачи пользователю"""
    if user_id not in user_sessions:
        return

    session = user_sessions[user_id]
    topic = session['topic']
    task_index = session['task_index']

    task = tasks_db[topic][task_index]
    total_tasks = len(tasks_db[topic])

    text = f"📝 *Тема: {topic}*\n"
    text += f"*Вопрос {task_index + 1} из {total_tasks}:*\n\n"
    text += f"❓ {task['question']}"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("◀️ Завершить"))

    bot.send_message(
        chat_id,
        text,
        parse_mode="Markdown",
        reply_markup=markup
    )


def show_detailed_results(message):
    """Показ детальной статистики пользователя"""
    user_id = message.from_user.id
    user_data, topic_results = get_user_stats(user_id)

    if not user_data or user_data[0] == 0:
        text = "📊 У тебя пока нет решенных задач!"
    else:
        total_tasks, correct, joined, last_active = user_data

        text = f"📊 *Твоя подробная статистика*\n\n"
        text += f"👤 *Пользователь:* {message.from_user.first_name}\n"
        text += f"📅 *Зарегистрирован:* {joined}\n"
        text += f"⏰ *Последняя активность:* {last_active}\n\n"

        if total_tasks > 0:
            percent = (correct / total_tasks * 100) if total_tasks > 0 else 0
            text += f"📈 *Общий прогресс:*\n"
            text += f"   ✅ Правильно: {correct}\n"
            text += f"   ❌ Неправильно: {total_tasks - correct}\n"
            text += f"   📊 Процент: {percent:.1f}%\n\n"

        if topic_results:
            text += f"📚 *По темам:*\n"
            for topic, total, cor in topic_results:
                cor = cor or 0
                topic_percent = (cor / total * 100) if total > 0 else 0
                text += f"   • {topic}: {cor}/{total} ({topic_percent:.1f}%)\n"

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown",
        reply_markup=main_menu(user_id)
    )


# ===== АДМИН-ФУНКЦИИ =====
def show_admin_stats(message):
    """Показ общей статистики бота (только для админа)"""
    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect('oge_bot.db')
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM results")
    total_results = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM user_actions")
    total_actions = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM results")
    active_users = cursor.fetchone()[0]

    cursor.execute("""
        SELECT user_id, first_name, total_tasks_completed, correct_answers 
        FROM users ORDER BY total_tasks_completed DESC LIMIT 5
    """)
    top_users = cursor.fetchall()

    conn.close()

    text = f"""
📊 *СТАТИСТИКА БОТА (Админ-панель)*

👥 *Всего пользователей:* {total_users}
🎯 *Активных пользователей:* {active_users}
📝 *Всего выполненных заданий:* {total_results}
📋 *Всего действий:* {total_actions}

🏆 *Топ-5 пользователей:*\n"""

    for i, (uid, name, total, correct) in enumerate(top_users, 1):
        percent = (correct / total * 100) if total > 0 else 0
        text += f"{i}. {name}: {correct}/{total} ({percent:.1f}%)\n"

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown",
        reply_markup=main_menu(message.from_user.id)
    )


def show_all_users(message):
    """Показ списка всех пользователей (только для админа)"""
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ У вас нет прав администратора!")
        return

    conn = sqlite3.connect('oge_bot.db')
    cursor = conn.cursor()

    # Проверяем, есть ли вообще пользователи
    cursor.execute("SELECT COUNT(*) FROM users")
    total_count = cursor.fetchone()[0]

    if total_count == 0:
        bot.send_message(
            message.chat.id,
            "❌ В базе данных пока нет пользователей!\n\n"
            "Возможные причины:\n"
            "• Никто не запускал бота\n"
            "• Функция save_user_to_db() не работает\n"
            "• Ошибка в структуре БД",
            reply_markup=main_menu(message.from_user.id)
        )
        conn.close()
        return

    # Получаем всех пользователей
    cursor.execute("""
        SELECT 
            user_id, 
            first_name, 
            username, 
            joined_date, 
            last_activity,
            total_tasks_completed,
            correct_answers
        FROM users 
        ORDER BY joined_date DESC
    """)
    users = cursor.fetchall()

    # Получаем статистику активности
    cursor.execute("""
        SELECT user_id, COUNT(*) as actions 
        FROM user_actions 
        GROUP BY user_id
    """)
    actions_count = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()

    # Отправляем пользователей по частям, без Markdown
    text = f"👥 ВСЕ ПОЛЬЗОВАТЕЛИ БОТА\n"
    text += f"Всего: {total_count}\n"
    text += "=" * 30 + "\n\n"

    for i, (uid, name, username, joined, last_active, tasks, correct) in enumerate(users, 1):
        if tasks > 0:
            percent = (correct / tasks * 100)
            progress = f"{correct}/{tasks} ({percent:.1f}%)"
        else:
            progress = "нет задач"

        username_str = f"@{username}" if username else "нет username"
        actions = actions_count.get(uid, 0)

        text += f"{i}. {name}\n"
        text += f"   📝 {username_str}\n"
        text += f"   🆔 {uid}\n"
        text += f"   📅 Присоединился: {joined}\n"
        text += f"   ⏰ Последний раз: {last_active}\n"
        text += f"   📊 Прогресс: {progress}\n"
        text += f"   🔄 Действий: {actions}\n\n"

        # Разбиваем на части
        if len(text) > 3500:
            bot.send_message(
                message.chat.id,
                text
            )
            text = ""

    if text:
        bot.send_message(
            message.chat.id,
            text,
            reply_markup=main_menu(message.from_user.id)
        )


def show_action_logs(message):
    """Показ последних действий пользователей (только для админа)"""
    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect('oge_bot.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ua.user_id, u.first_name, ua.action, ua.details, ua.timestamp 
        FROM user_actions ua
        LEFT JOIN users u ON ua.user_id = u.user_id
        ORDER BY ua.timestamp DESC LIMIT 30
    """)
    logs = cursor.fetchall()
    conn.close()

    if not logs:
        text = "📋 Логов пока нет"
    else:
        text = f"📋 ПОСЛЕДНИЕ ДЕЙСТВИЯ\n\n"
        for uid, name, action, details, ts in logs:
            name = name or "Неизвестный"
            text += f"• [{ts}] {name} (ID:{uid})\n"
            text += f"  Действие: {action}\n"
            if details:
                text += f"  Детали: {details}\n"
            text += "\n"

    # Отправляем без Markdown
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            part = text[i:i + 4000]
            bot.send_message(
                message.chat.id,
                part,
                reply_markup=main_menu(message.from_user.id) if i + 4000 >= len(text) else None
            )
    else:
        bot.send_message(
            message.chat.id,
            text,
            reply_markup=main_menu(message.from_user.id)
        )


# ===== ОТЛАДОЧНЫЕ ФУНКЦИИ ДЛЯ АДМИНА =====
@bot.message_handler(commands=['debug_users'])
def debug_users(message):
    """Отладка - проверить, есть ли пользователи в БД"""
    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect('oge_bot.db')
    cursor = conn.cursor()

    # Проверяем структуру таблицы
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()

    # Считаем количество пользователей
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]

    # Получаем всех пользователей
    cursor.execute("SELECT user_id, first_name, username, joined_date FROM users")
    users = cursor.fetchall()

    conn.close()

    # Формируем текст БЕЗ Markdown
    debug_text = "🔍 ОТЛАДКА БАЗЫ ДАННЫХ\n\n"
    debug_text += "Структура таблицы users:\n"
    for col in columns:
        debug_text += f"  • {col[1]} ({col[2]})\n"

    debug_text += f"\n📊 Всего записей: {count}\n\n"

    if users:
        debug_text += "👥 Пользователи в БД:\n"
        for uid, name, username, joined in users:
            username = username if username else "нет username"
            debug_text += f"  • {name} (@{username}) ID:{uid} - {joined}\n"
    else:
        debug_text += "❌ В БД НЕТ пользователей!"

    # Отправляем без parse_mode (обычный текст)
    bot.send_message(
        message.chat.id,
        debug_text
    )


@bot.message_handler(commands=['test_users'])
def test_users(message):
    """Тестовая команда для проверки работы с БД"""
    if message.from_user.id != ADMIN_ID:
        return

    # Пробуем сохранить текущего пользователя принудительно
    save_user_to_db(message.from_user)

    # Проверяем, сохранился ли
    conn = sqlite3.connect('oge_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (message.from_user.id,))
    user_data = cursor.fetchone()
    conn.close()

    if user_data:
        bot.send_message(
            message.chat.id,
            f"✅ Тест пройден! Ваши данные в БД:\n\n"
            f"ID: {user_data[0]}\n"
            f"Username: {user_data[1]}\n"
            f"Имя: {user_data[2]}\n"
            f"Дата регистрации: {user_data[4]}",
            reply_markup=main_menu(message.from_user.id)
        )
    else:
        bot.send_message(
            message.chat.id,
            "❌ Ошибка: ваши данные НЕ сохранились в БД!",
            reply_markup=main_menu(message.from_user.id)
        )


@bot.message_handler(commands=['admin'])
def admin_panel(message):
    """Админ-панель"""
    if message.from_user.id != ADMIN_ID:
        return

    text = """
🔐 *АДМИН-ПАНЕЛЬ*

📋 *Основные команды:*
/users - список пользователей
/stats - статистика бота
/logs - последние действия

🔧 *Отладочные команды:*
/debug_users - структура БД
/test_users - тест сохранения

🔄 *Кнопки в меню:*
• 👥 Пользователи - список
• 📈 Статистика бота - общая статистика
• 📋 Логи действий - последние действия
    """

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown"
    )


@bot.message_handler(commands=['users'])
def cmd_users(message):
    """Команда для быстрого вызова списка пользователей"""
    if message.from_user.id == ADMIN_ID:
        show_all_users(message)


@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    """Команда для быстрого вызова статистики"""
    if message.from_user.id == ADMIN_ID:
        show_admin_stats(message)


@bot.message_handler(commands=['logs'])
def cmd_logs(message):
    """Команда для быстрого вызова логов"""
    if message.from_user.id == ADMIN_ID:
        show_action_logs(message)


# ===== ОБРАБОТЧИКИ КОМАНД =====
@bot.message_handler(commands=['start'])
def start_command(message):
    """Обработка команды /start с приветствием по имени"""
    user = message.from_user

    # Запись данных пользователя в БД
    save_user_to_db(user)
    log_user_action(user.id, "start", "Пользователь запустил бота")

    welcome_text = f"""
👋 *Привет, {user.first_name}!*

Добро пожаловать в бота для подготовки к ОГЭ по информатике! 🎓

Я помогу тебе:
• 📚 Изучать теорию по темам
• 📝 Решать задачи с проверкой
• 📊 Отслеживать свой прогресс

*Доступные команды:*
/help - подробная справка
/stop - остановить бота

Выбери действие в меню ниже 👇
    """

    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode="Markdown",
        reply_markup=main_menu(user.id)
    )


@bot.message_handler(commands=['help'])
def help_command(message):
    """Обработка команды /help"""
    user = message.from_user
    log_user_action(user.id, "help", "Пользователь запросил помощь")

    help_text = """
❓ *Справка по использованию бота*

*Основные команды:*
/start - перезапустить бота
/help - показать эту справку
/stop - завершить работу

*Как пользоваться:*
1️⃣ Нажми "📚 Справочник" - теория по темам
2️⃣ Нажми "📝 Задачи" - выбор темы и решение
3️⃣ Нажми "📊 Результаты" - твоя статистика
4️⃣ Нажми "ℹ️ О боте" - информация о боте

*Советы:*
• Отвечай на вопросы развернуто
• Результаты сохраняются в БД
• Следи за своим прогрессом

Удачи в подготовке! 🍀
    """

    bot.send_message(
        message.chat.id,
        help_text,
        parse_mode="Markdown",
        reply_markup=main_menu(user.id)
    )


@bot.message_handler(commands=['stop'])
def stop_command(message):
    """Обработка команды /stop"""
    user = message.from_user
    log_user_action(user.id, "stop", "Пользователь остановил бота")

    stop_text = f"""
👋 *До свидания, {user.first_name}!*

Бот остановлен. Чтобы начать заново, нажми /start

*Статистика сессии сохранена в БД* 📊
    """

    bot.send_message(
        message.chat.id,
        stop_text,
        parse_mode="Markdown"
    )


@bot.message_handler(commands=['tasks'])
def tasks_command(message):
    """Быстрый переход к задачам"""
    user = message.from_user
    log_user_action(user.id, "tasks", "Переход к задачам через команду")

    bot.send_message(
        message.chat.id,
        "📝 Выбери тему для решения задач:",
        reply_markup=topics_menu()
    )


@bot.message_handler(commands=['results'])
def results_command(message):
    """Быстрый просмотр результатов"""
    show_detailed_results(message)


# ===== ОСНОВНОЙ ОБРАБОТЧИК СООБЩЕНИЙ =====
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Обработка всех текстовых сообщений"""
    user_id = message.from_user.id
    text = message.text

    # Логируем действие
    log_user_action(user_id, "message", f"Отправил: {text[:50]}...")

    # === ГЛАВНОЕ МЕНЮ ===
    if text == "📚 Справочник":
        handbook_text = """
📚 *Краткий справочник по темам ОГЭ:*

🔹 *Информатика*
• Единицы измерения информации (бит, байт, Кбайт)
• Кодирование данных

🔹 *Логика*
• Логические операции (И, ИЛИ, НЕ)
• Таблицы истинности

🔹 *Алгоритмы*
• Свойства алгоритмов
• Способы записи

🔹 *Файлы*
• Файловая система
• Расширения файлов

Для закрепления переходи в раздел "📝 Задачи"!
        """
        bot.send_message(
            user_id,
            handbook_text,
            parse_mode="Markdown",
            reply_markup=main_menu(user_id)
        )

    elif text == "📝 Задачи":
        bot.send_message(
            user_id,
            "📝 Выбери тему:",
            reply_markup=topics_menu()
        )

    elif text == "📊 Результаты":
        show_detailed_results(message)

    elif text == "ℹ️ О боте":
        about_text = """
ℹ️ *О боте подготовки к ОГЭ*

*Версия:* 2.0
*Разработчик:* @username

*Функции:*
✅ Приветствие по имени
✅ 5+ кнопок в меню
✅ Запись данных в БД
✅ Разграничение прав (админ/пользователь)
✅ Команды /start, /help, /stop

*Технологии:*
• Python + TeleBot
• SQLite для хранения данных
• Логирование действий

Успехов в подготовке! 🍀
        """
        bot.send_message(
            user_id,
            about_text,
            parse_mode="Markdown",
            reply_markup=main_menu(user_id)
        )

    elif text == "❓ Помощь":
        help_command(message)

    # === АДМИН-МЕНЮ ===
    elif text == "📈 Статистика бота" and user_id == ADMIN_ID:
        show_admin_stats(message)

    elif text == "👥 Пользователи" and user_id == ADMIN_ID:
        show_all_users(message)

    elif text == "📋 Логи действий" and user_id == ADMIN_ID:
        show_action_logs(message)

    # === ВЫБОР ТЕМЫ ===
    elif text.startswith("🔹 ") and text.replace("🔹 ", "") in tasks_db:
        topic = text.replace("🔹 ", "")

        user_sessions[user_id] = {
            'topic': topic,
            'task_index': 0,
            'correct': 0,
            'total': 0
        }

        log_user_action(user_id, "topic_selected", f"Выбрана тема: {topic}")
        send_task(message.chat.id, user_id)

    # === ЗАВЕРШЕНИЕ ===
    elif text == "◀️ Завершить" or text == "◀️ Назад в меню":
        if user_id in user_sessions:
            session = user_sessions[user_id]

            if session['total'] > 0:
                percent = (session['correct'] / session['total'] * 100) if session['total'] > 0 else 0
                result_text = f"""
📊 *Результаты по теме {session['topic']}:*

✅ Правильно: {session['correct']}
❌ Неправильно: {session['total'] - session['correct']}
📈 Процент: {percent:.1f}%

Результаты сохранены в БД!
                """
                bot.send_message(
                    user_id,
                    result_text,
                    parse_mode="Markdown"
                )

            del user_sessions[user_id]

        bot.send_message(
            user_id,
            "Главное меню:",
            reply_markup=main_menu(user_id)
        )

    # === ОТВЕТ НА ЗАДАЧУ ===
    elif user_id in user_sessions:
        session = user_sessions[user_id]
        topic = session['topic']
        task_index = session['task_index']

        current_task = tasks_db[topic][task_index]
        correct_answer = current_task['answer'].lower().strip()
        user_answer = text.lower().strip()

        is_correct = user_answer == correct_answer

        if is_correct:
            session['correct'] += 1
            response = f"✅ *Правильно!*\n\n{current_task['explain']}"
        else:
            response = f"❌ *Неправильно!*\n\nПравильный ответ: *{current_task['answer']}*\n\n{current_task['explain']}"

        session['total'] += 1

        # ЗАПИСЬ ДАННЫХ В БД
        save_user_result(
            user_id,
            topic,
            current_task['question'],
            user_answer,
            correct_answer,
            is_correct
        )

        bot.send_message(
            user_id,
            response,
            parse_mode="Markdown"
        )

        # Переход к следующему вопросу
        if task_index + 1 < len(tasks_db[topic]):
            session['task_index'] += 1
            send_task(message.chat.id, user_id)
        else:
            percent = (session['correct'] / session['total'] * 100) if session['total'] > 0 else 0
            final_text = f"""
🎉 *Тема '{topic}' полностью пройдена!*

✅ Правильных ответов: {session['correct']}
📈 Процент выполнения: {percent:.1f}%

Все результаты сохранены в базу данных!
            """

            bot.send_message(
                user_id,
                final_text,
                parse_mode="Markdown"
            )

            del user_sessions[user_id]

            bot.send_message(
                user_id,
                "📝 Выбери следующую тему:",
                reply_markup=topics_menu()
            )

    else:
        bot.send_message(
            user_id,
            "Я не понимаю эту команду. Используй кнопки меню!",
            reply_markup=main_menu(user_id)
        )


# ===== ЗАПУСК БОТА С ЗАЩИТОЙ ОТ ПАДЕНИЙ =====
if __name__ == "__main__":
    # Инициализация БД
    init_db()

    print("=" * 50)
    print("✅ БОТ ДЛЯ ПОДГОТОВКИ К ОГЭ ЗАПУЩЕН!")
    print("=" * 50)
    print(f"👤 Администратор ID: {ADMIN_ID}")

    # Проверка токена
    if not BOT_TOKEN:
        print("❌ ОШИБКА: Токен не найден в .env файле!")
        print("📝 Создайте файл .env с содержимым:")
        print('BOT_TOKEN=ваш_токен_здесь')
        print('ADMIN_ID=ваш_id_здесь')
        exit(1)

    print(f"🔑 Токен: {BOT_TOKEN[:10]}... (первые 10 символов)")
    print("📝 Доступные команды:")
    print("   /start - приветствие")
    print("   /help - справка")
    print("   /stop - выход")
    print("   /tasks - задачи")
    print("   /results - результаты")
    print("   /admin - админ-панель")
    print("=" * 50)
    print("🎯 Все функции активны:")
    print("   ✅ Приветствие по имени")
    print("   ✅ 5+ кнопок в меню")
    print("   ✅ Разграничение админ/пользователь")
    print("   ✅ Запись данных в БД")
    print("   ✅ Просмотр пользователей")
    print("=" * 50)

    # Запуск с защитой
    while True:
        try:
            print("🟢 Бот запускается...")
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"🔴 Бот упал с ошибкой: {e}")
            print("🟡 Перезапуск через 5 секунд...")
            time.sleep(5)
            continue
        break