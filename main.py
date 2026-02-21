import telebot
from telebot import types
import sqlite3
from datetime import datetime

# ===== ТОКЕН (ВСТАВЬ СВОЙ) =====
BOT_TOKEN = "8572115748:AAEwfw09KZVIhVgRvh3FzbqR-OAq7I4MejA"
ADMIN_ID = 1142854194  # Вставь свой ID

bot = telebot.TeleBot(BOT_TOKEN)


# ===== ПРОСТАЯ БАЗА ДАННЫХ =====
def init_db():
    conn = sqlite3.connect('oge.db')
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            date TEXT
        )
    ''')

    # Таблица результатов - ПРОСТАЯ
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            topic TEXT,
            correct INTEGER,
            total INTEGER
        )
    ''')

    conn.commit()
    conn.close()


# ===== СОХРАНЕНИЕ ПОЛЬЗОВАТЕЛЯ =====
def save_user(message):
    user = message.from_user
    conn = sqlite3.connect('oge.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user.id,))
    if not cursor.fetchone():
        date = datetime.now().strftime("%d.%m.%Y")
        cursor.execute(
            "INSERT INTO users (user_id, name, date) VALUES (?, ?, ?)",
            (user.id, user.first_name, date)
        )
        conn.commit()
    conn.close()


# ===== ГЛАВНОЕ МЕНЮ =====
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("📚 Справочник")
    btn2 = types.KeyboardButton("📝 Задачи")
    btn3 = types.KeyboardButton("📊 Результаты")
    btn4 = types.KeyboardButton("ℹ️ О боте")
    btn5 = types.KeyboardButton("❓ Помощь")
    markup.add(btn1, btn2, btn3, btn4, btn5)
    return markup


# ===== МЕНЮ ТЕМ =====
def topics_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("🔹 Информатика")
    btn2 = types.KeyboardButton("🔹 Логика")
    btn3 = types.KeyboardButton("🔹 Алгоритмы")
    btn4 = types.KeyboardButton("🔹 Файлы")
    btn5 = types.KeyboardButton("◀️ Назад в меню")
    markup.add(btn1, btn2, btn3, btn4, btn5)
    return markup


# ===== ЗАДАЧИ (ПРОСТОЙ СЛОВАРЬ) =====
tasks = {
    "Информатика": {
        "question": "Сколько бит в одном байте?",
        "answer": "8",
        "explain": "1 байт = 8 бит"
    },
    "Логика": {
        "question": "Чему равно 1 AND 0?",
        "answer": "0",
        "explain": "Конъюнкция (И) - 1 только если оба операнда равны 1"
    },
    "Алгоритмы": {
        "question": "Что такое алгоритм?",
        "answer": "последовательность действий",
        "explain": "Алгоритм - это точная последовательность действий для достижения цели"
    },
    "Файлы": {
        "question": "Сколько байт в 1 Кбайте?",
        "answer": "1024",
        "explain": "1 Кбайт = 1024 байта"
    }
}


# ===== СОХРАНЕНИЕ РЕЗУЛЬТАТА =====
def save_result(user_id, topic, is_correct):
    conn = sqlite3.connect('oge.db')
    cursor = conn.cursor()

    # Проверяем, есть ли уже записи по этой теме
    cursor.execute(
        "SELECT correct, total FROM results WHERE user_id=? AND topic=?",
        (user_id, topic)
    )
    result = cursor.fetchone()

    if result:
        # Обновляем существующую запись
        new_correct = result[0] + (1 if is_correct else 0)
        new_total = result[1] + 1
        cursor.execute(
            "UPDATE results SET correct=?, total=? WHERE user_id=? AND topic=?",
            (new_correct, new_total, user_id, topic)
        )
    else:
        # Создаем новую запись
        cursor.execute(
            "INSERT INTO results (user_id, topic, correct, total) VALUES (?, ?, ?, ?)",
            (user_id, topic, 1 if is_correct else 0, 1)
        )

    conn.commit()
    conn.close()


# ===== ПОКАЗ РЕЗУЛЬТАТОВ =====
def show_results(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('oge.db')
    cursor = conn.cursor()

    cursor.execute("SELECT topic, correct, total FROM results WHERE user_id=?", (user_id,))
    results = cursor.fetchall()
    conn.close()

    if not results:
        text = "📊 У тебя пока нет решенных задач!"
    else:
        text = "📊 Твои результаты:\n\n"
        total_correct = 0
        total_all = 0
        for topic, correct, total in results:
            percent = (correct / total * 100) if total > 0 else 0
            text += f"• {topic}: {correct}/{total} ({percent:.0f}%)\n"
            total_correct += correct
            total_all += total

        total_percent = (total_correct / total_all * 100) if total_all > 0 else 0
        text += f"\n✅ Всего: {total_correct}/{total_all} ({total_percent:.0f}%)"

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_menu()
    )


# ===== ХРАНЕНИЕ СОСТОЯНИЙ =====
user_waiting = {}  # {user_id: topic}


# ===== КОМАНДА START =====
@bot.message_handler(commands=['start'])
def start(message):
    save_user(message)
    bot.send_message(
        message.chat.id,
        f"👋 Привет, {message.from_user.first_name}!\n\nЯ помогу тебе подготовиться к ОГЭ по информатике. Выбери действие:",
        reply_markup=main_menu()
    )


# ===== КОМАНДА HELP =====
@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.send_message(
        message.chat.id,
        "❓ Команды:\n/start - начать\n/help - помощь\n/stop - выход\n/tasks - задачи\n/results - результаты",
        reply_markup=main_menu()
    )


# ===== КОМАНДА STOP =====
@bot.message_handler(commands=['stop'])
def stop(message):
    bot.send_message(
        message.chat.id,
        f"👋 Пока, {message.from_user.first_name}! Чтобы начать заново, нажми /start"
    )


# ===== КОМАНДА TASKS =====
@bot.message_handler(commands=['tasks'])
def tasks_cmd(message):
    bot.send_message(
        message.chat.id,
        "📝 Выбери тему:",
        reply_markup=topics_menu()
    )


# ===== КОМАНДА RESULTS =====
@bot.message_handler(commands=['results'])
def results_cmd(message):
    show_results(message)


# ===== ОБРАБОТКА ВСЕХ СООБЩЕНИЙ =====
@bot.message_handler(func=lambda m: True)
def handle_all(message):
    user_id = message.from_user.id
    text = message.text

    # ГЛАВНОЕ МЕНЮ
    if text == "📚 Справочник":
        bot.send_message(
            user_id,
            "📚 *Основные темы ОГЭ:*\n\n"
            "• Информация и ее кодирование\n"
            "• Логические операции\n"
            "• Алгоритмы и исполнители\n"
            "• Файловая система\n"
            "• Информационные модели\n\n"
            "Подробнее можно изучить в разделе 'Задачи'!",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )

    elif text == "📝 Задачи":
        bot.send_message(
            user_id,
            "📝 Выбери тему:",
            reply_markup=topics_menu()
        )

    elif text == "📊 Результаты":
        show_results(message)

    elif text == "ℹ️ О боте":
        bot.send_message(
            user_id,
            "ℹ️ *Бот для подготовки к ОГЭ по информатике*\n\nВерсия: 1.0\nРазработчик: @username\n\nУдачи в подготовке! 🍀",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )

    elif text == "❓ Помощь":
        bot.send_message(
            user_id,
            "❓ *Как пользоваться:*\n\n"
            "1. Нажми '📝 Задачи'\n"
            "2. Выбери тему\n"
            "3. Ответь на вопрос\n"
            "4. Смотри результаты в '📊 Результаты'\n\n"
            "Если есть вопросы, пиши @username",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )

    elif text == "◀️ Назад в меню":
        bot.send_message(
            user_id,
            "Главное меню:",
            reply_markup=main_menu()
        )

    # ВЫБОР ТЕМЫ ДЛЯ ЗАДАЧ
    elif text in ["🔹 Информатика", "🔹 Логика", "🔹 Алгоритмы", "🔹 Файлы"]:
        topic = text.replace("🔹 ", "")
        task = tasks[topic]

        # Запоминаем, что пользователь ждет ответа
        user_waiting[user_id] = topic

        # Клавиатура с кнопкой назад
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("◀️ Назад в меню"))

        bot.send_message(
            user_id,
            f"❓ *Вопрос по теме {topic}:*\n\n{task['question']}\n\n(Напиши ответ):",
            parse_mode="Markdown",
            reply_markup=markup
        )

    # ПРОВЕРКА ОТВЕТА
    elif user_id in user_waiting:
        topic = user_waiting[user_id]
        task = tasks[topic]

        user_answer = text.strip().lower()
        correct_answer = task['answer'].lower()

        if user_answer == correct_answer:
            result_text = f"✅ *Правильно!*\n\n{task['explain']}"
            is_correct = True
        else:
            result_text = f"❌ *Неправильно!*\n\nПравильный ответ: *{task['answer']}*\n\n{task['explain']}"
            is_correct = False

        # Сохраняем результат
        save_result(user_id, topic, is_correct)

        # Удаляем из ожидания
        del user_waiting[user_id]

        # Показываем результат и предлагаем выбрать тему
        bot.send_message(
            user_id,
            result_text,
            parse_mode="Markdown"
        )

        bot.send_message(
            user_id,
            "📝 Выбери следующую тему:",
            reply_markup=topics_menu()
        )

    # ЕСЛИ НИЧЕГО НЕ ПОДОШЛО
    else:
        bot.send_message(
            user_id,
            "Я не понимаю эту команду. Используй кнопки меню!",
            reply_markup=main_menu()
        )


# ===== ЗАПУСК =====
if __name__ == "__main__":
    init_db()
    print("✅ Бот запущен!")
    print("👤 Проверь бота в Telegram")
    bot.infinity_polling()