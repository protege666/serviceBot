from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import dotenv
import os
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import sqlite3
from io import BytesIO
from PIL import Image
from aiogram import types
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher import FSMContext
import re
import requests

storage = MemoryStorage()

dotenv = dotenv.load_dotenv("config/.env")

class Tokens():
    bot_token = os.environ['TOKEN']
    admin_id = os.environ['ADMIN_ID']
    group_id = os.environ['GROUP_ID']

bot = Bot(Tokens.bot_token)
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

class OrderForm(StatesGroup):
    name = State()
    phone = State()
    vin_check = State()
    vin_code = State()
    parts_list = State()
    car_make = State()
  
class SecondForm(StatesGroup):
    name = State()
    phone = State()
    view = State()
    model = State()
    order = State()

class AddForm(StatesGroup):
    add = State()

class AdminForm(StatesGroup):
    photo = State()
    desc = State()
    shdesc = State()

def validate_russian_phone_number(phone_number):
    # Паттерн для российских номеров телефона
    # Российские номера могут начинаться с +7, 8, или без кода страны
    pattern = re.compile(r'^(\+7|8|7)?(\d{10})$')

    # Проверка соответствия паттерну
    match = pattern.match(phone_number)
    
    return bool(match)

def validate_russian_name(name):
    pattern = re.compile(r'^[А-Яа-яЁё\s]+$')

    # Проверка соответствия паттерну
    match = pattern.match(name)

    return bool(match)

def get_telegram_user(user_id, bot_token):
    url = f'https://api.telegram.org/bot{bot_token}/getChat'
    data = {'chat_id': user_id}
    response = requests.post(url, data=data)
    return response.json()

def menu_button():
    menu_btn = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
    menu_btn.add(KeyboardButton("Заказ автозапчастей"), KeyboardButton("Заказ запчастей мото, вело, инструменты"))
    menu_btn.add(KeyboardButton("Контакты"), KeyboardButton("Акции"))
    return menu_btn

def get_base_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(KeyboardButton('Назад'))
    return keyboard

def btn_from_vin():
    keybtn = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keybtn.add(KeyboardButton('Да'))
    keybtn.add(KeyboardButton('Нет'))
    keybtn.add(KeyboardButton('Назад'))
    return keybtn

def adminBtn():
    admin_button = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    admin_button.add(KeyboardButton('Добавить'))
    admin_button.add(KeyboardButton('Удалить'))
    admin_button.add(KeyboardButton('Удалить все акции и скидки'))
    return admin_button

def adminBtn_plus():
    admin_button = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    admin_button.add(KeyboardButton('Добавить'))
    admin_button.add(KeyboardButton('Добавить админа'))
    admin_button.add(KeyboardButton('Удалить'))
    admin_button.add(KeyboardButton('Удалить все акции и скидки'))
    return admin_button


@dp.message_handler(lambda message: message.text == 'Добавить админа', state="*")
async def add_id_handler(message: types.Message):
    # Запрос пользователя на ввод Telegram ID
    await message.answer("Введите Telegram ID:")
    await AddForm.add.set()

@dp.message_handler(state=AddForm.add)
async def add_admins(message: types.Message, state: FSMContext):
    if message.text == "/start":
        await state.finish()
        return await start_message(message)
    elif message.text == "/menu":
        await state.finish()
        return await menu(message)
    telegram_id = message.text
    user = get_telegram_user(telegram_id, Tokens.bot_token)
    if 'result' in user:
        print(f'User with ID {telegram_id} exists.')
        conn = sqlite3.connect('mag.db')
        cursor = conn.cursor()

        # Добавление Telegram ID в базу данных
        cursor.execute('INSERT INTO admins (telegram_id) VALUES (?)', (telegram_id,))

        # Сохранение изменений и закрытие соединения
        conn.commit()
        conn.close()

        # Отправка сообщения об успешном добавлении
        await message.answer(f"Telegram ID {telegram_id} успешно добавлен в базу данных!")
        await state.finish()
    else:
        await message.answer(f"Telegram ID {telegram_id} не существует! Попробуйте еще раз!")
        await AddForm.add.set()
    
    
    
@dp.message_handler(lambda message: message.text == 'Удалить все акции и скидки', state="*")
async def cmd_delete_all_promotions(message: types.Message):
    # Выполняем SQL-запрос для удаления всех записей из таблицы sales
    conn = sqlite3.connect('mag.db', check_same_thread=False)
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM sales")
        conn.commit()
        await message.answer("Все акции и скидки успешно удалены.")
    except Exception as e:
        print(f"Error deleting all promotions: {e}")
        await message.answer("Произошла ошибка при удалении всех акций и скидок.")
    finally:
        conn.close()


@dp.message_handler(lambda message: message.text == 'Добавить', state="*")
async def cmd_add_promotion(message: types.Message, state: FSMContext):
    await message.answer("Отправьте фотографию акции:")
    await AdminForm.photo.set()


@dp.message_handler(state=AdminForm.photo, content_types=types.ContentType.PHOTO)
async def process_image(message: types.Message, state: FSMContext):
    # Сохраняем фотографию в базу данных
    photo_file_id = message.photo[-1].file_id
    file_info = await bot.get_file(photo_file_id)
    file = await bot.download_file(file_info.file_path)
    image_blob = file.read()

    # Сохраняем фотографию в базу данных
    conn = sqlite3.connect('mag.db', check_same_thread=False)
    cursor = conn.cursor()

    try:
        # Вставляем запись в базу данных только с изображением
        cursor.execute("INSERT INTO sales (imj, \"desc\", shdesc) VALUES (?, 'Default value', 'Default value')", (image_blob,))
        conn.commit()

        # Получаем идентификатор только что вставленной записи
        cursor.execute("SELECT last_insert_rowid()")
        promo_id = cursor.fetchone()[0]

        # Сохраняем идентификатор в состояние
        async with state.proxy() as data:
            data['promo_id'] = promo_id

        await message.answer("Фотография успешно добавлена. Теперь отправьте описание акции:")
        await AdminForm.desc.set()
    except Exception as e:
        print(f"Error adding image to database: {e}")
        await message.answer("Произошла ошибка при добавлении фотографии в базу данных.")
    finally:
        conn.close()



@dp.message_handler(state=AdminForm.desc)
async def process_description(message: types.Message, state: FSMContext):
    # Сохраняем описание в базу данных
    description = message.text

    # Получаем идентификатор записи, которую нужно обновить
    async with state.proxy() as data:
        promo_id = data.get('promo_id')

    if not promo_id:
        await message.answer("Ошибка: Не удалось определить идентификатор записи.")
        return

    # Обновляем запись в базе данных
    conn = sqlite3.connect('mag.db')
    cursor = conn.cursor()

    try:
        cursor.execute("UPDATE sales SET \"desc\" = ? WHERE id = ?", (description, promo_id))
        conn.commit()
        await message.answer("Описание успешно добавлено. Теперь отправьте короткое описание акции:")
        await AdminForm.shdesc.set()
    except Exception as e:
        print(f"Error adding description to database: {e}")
        await message.answer("Произошла ошибка при добавлении описания в базу данных.")


@dp.message_handler(state=AdminForm.shdesc)
async def process_short_description(message: types.Message, state: FSMContext):
    # Сохраняем короткое описание в базу данных
    short_description = message.text

    # Получаем идентификатор записи, которую нужно обновить
    async with state.proxy() as data:
        promo_id = data.get('promo_id')

    if not promo_id:
        await message.answer("Ошибка: Не удалось определить идентификатор записи.")
        return

    # Обновляем запись в базе данных
    conn = sqlite3.connect('mag.db')
    cursor = conn.cursor()

    try:
        cursor.execute("UPDATE sales SET shdesc = ? WHERE id = ?", (short_description, promo_id))
        conn.commit()
        await message.answer("Короткое описание успешно добавлено.")
    except Exception as e:
        print(f"Error adding short description to database: {e}")
        await message.answer("Произошла ошибка при добавлении короткого описания в базу данных.")

    await state.finish()

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ...

@dp.message_handler(lambda message: message.text.lower() == 'удалить', state="*")
async def cmd_delete_promotion(message: types.Message, state: FSMContext):
    try:
        conn = sqlite3.connect('mag.db', check_same_thread=False)
        cursor = conn.cursor()

        # Получаем данные из базы данных
        cursor.execute("SELECT id, \"desc\", shdesc FROM sales")
        rows = cursor.fetchall()

        # Создаем inline-кнопки для каждой записи
        buttons = []
        for row in rows:
            promo_id, promo_desc, shdesc = row
            button_text = f"Удалить {shdesc}"
            button = InlineKeyboardButton(button_text, callback_data=f"delete_promo:{promo_id}")
            buttons.append(button)

        # Создаем обновленную inline-клавиатуру с возможностью многострочных кнопок
        keyboard = InlineKeyboardMarkup(resize_keyboard=True).add(*buttons)

        await message.answer("Выберите запись для удаления:", reply_markup=keyboard)
    except Exception as e:
        print(f"Error fetching records for deletion: {e}")
        await message.answer("Произошла ошибка при получении записей для удаления.")
    finally:
        conn.close()

    await state.finish()

# ...

@dp.callback_query_handler(lambda c: c.data.startswith('delete_promo:'))
async def process_delete_callback(callback_query: types.CallbackQuery):
    try:
        promo_id = int(callback_query.data.split(':')[1])

        conn = sqlite3.connect('mag.db', check_same_thread=False)
        cursor = conn.cursor()

        # Получаем информацию о записи
        cursor.execute("SELECT id, \"desc\" FROM sales WHERE id = ?", (promo_id,))
        row = cursor.fetchone()
        if row:
            promo_id, promo_desc = row
            message_text = f"Вы уверены, что хотите удалить запись?\n\n{promo_desc}"
        else:
            message_text = "Запись не найдена."

        # Отправляем сообщение с подробной информацией и inline-клавиатурой для подтверждения удаления
        await bot.send_message(callback_query.from_user.id, message_text, reply_markup=confirm_keyboard(promo_id))
    except ValueError:
        await bot.send_message(callback_query.from_user.id, "Ошибка: Некорректный идентификатор.")
    except Exception as e:
        print(f"Error processing delete callback: {e}")
        await bot.send_message(callback_query.from_user.id, "Произошла ошибка при обработке команды удаления.")
    finally:
        conn.close()

# ...

def confirm_keyboard(promo_id):
    return InlineKeyboardMarkup().add(
        InlineKeyboardButton("Да, удалить", callback_data=f"confirm_delete:{promo_id}"),
        InlineKeyboardButton("Отмена", callback_data="cancel_delete")
    )
@dp.callback_query_handler(lambda c: c.data == 'cancel_delete')
async def process_cancel_delete_callback(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id, "Удаление отменено.")
    admin_keyboard = adminBtn()
    await bot.send_message(callback_query.from_user.id, "Возвращаемся к начальной клавиатуре.", reply_markup=admin_keyboard)

    # Завершаем обработку коллбэка
    await bot.answer_callback_query(callback_query.id)


@dp.callback_query_handler(lambda c: c.data.startswith('confirm_delete:'))
async def process_confirm_delete_callback(callback_query: types.CallbackQuery):
    try:
        promo_id = int(callback_query.data.split(':')[1])

        if callback_query.data == 'cancel_delete':
            await bot.send_message(callback_query.from_user.id, "Удаление отменено.")
        else:
            conn = sqlite3.connect('mag.db', check_same_thread=False)
            cursor = conn.cursor()

            # Удаляем запись из базы данных
            cursor.execute("DELETE FROM sales WHERE id = ?", (promo_id,))
            conn.commit()

            await bot.send_message(callback_query.from_user.id, f"Запись успешно удалена.")
    except ValueError:
        await bot.send_message(callback_query.from_user.id, "Ошибка: Некорректный идентификатор.")
    except Exception as e:
        print(f"Error deleting record from database: {e}")
        await bot.send_message(callback_query.from_user.id, "Произошла ошибка при удалении записи из базы данных.")
    finally:
        conn.close()

    # Завершаем обработку коллбэка
    await bot.answer_callback_query(callback_query.id)

@dp.message_handler(commands=['menu'])
async def menu(message: types.Message):
    await message.answer("Выберите опцию:", reply_markup=menu_button())

@dp.message_handler(commands=['start'])
async def start_message(message: types.Message):
    user_id = message.from_user.id

    # Добавляем идентификатор пользователя в таблицу
    conn = sqlite3.connect('mag.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()
    await bot.send_message(message.chat.id, "*Наш БОТ, может вам предложить:*\n\
Подбор запчастей не выходя из дома, на многие виды техники и инструмента.\n\
Оригинальные и бюджетные аналоги.\n\
Доступные цены и гарантия качества.\n\
Удобный способ оплаты.\n\
*А так же при заказе запчастей через БОТ, бесплатная доставка в пределах города Волхов!!!*\n\
1. Для подбора запчастей выберите соответствующий раздел\n\
2. Заполните форму заявки\n\
3. Ожидайте, наши менеджеры с Вами свяжутся", parse_mode="markdown")
    await menu(message)

@dp.message_handler(commands=['my_id'])
async def my_id_command(message: types.Message):
    # Отправка ID чата
    await message.reply(f"ID этой группы: {message.chat.id}")
@dp.message_handler(commands=['admin'])
async def admin_menu(message: types.Message):
    # Подключение к базе данных
    conn = sqlite3.connect('mag.db')
    cursor = conn.cursor()

    # Выполнение запроса для получения всех telegram_id из таблицы admins
    cursor.execute('SELECT telegram_id FROM admins')

    # Извлечение результатов запроса и сохранение их в список
    telegram_ids = [row[0] for row in cursor.fetchall()]

    # Закрытие соединения
    conn.close()

    if str(message.from_user.id) == Tokens.admin_id:
        return await message.answer("Добро пожаловать в панель админиистратора!", reply_markup=adminBtn_plus())
    elif message.from_user.id in telegram_ids:
        return await message.answer("Добро пожаловать в панель админиистратора!", reply_markup=adminBtn())
    else:
        await message.answer("Доступа к админ панели нет!")
        return await menu(message)
        

@dp.message_handler(lambda message: message.text.lower() == 'заказ автозапчастей', state='*')
async def process_order_parts(message: types.Message):
    await message.answer("Давайте познакомимся!\nКак вас зовут?", reply_markup=get_base_keyboard())
    await OrderForm.name.set()

@dp.message_handler(lambda message: message.text.lower() == 'заказ запчастей мото, вело, инструменты', state='*')
async def moto_process_order_parts(message: types.Message):
    await message.answer("Давайте познакомимся!\nКак вас зовут?", reply_markup=get_base_keyboard())
    await SecondForm.name.set()

@dp.message_handler(lambda message: message.text.lower() == 'акции', state='*')
async def process_promotions(callback_query: types.CallbackQuery):
    # Подключение к базе данных SQLite
    conn = sqlite3.connect('mag.db')
    cursor = conn.cursor()

    try:
        # Получение данных из таблицы sales
        cursor.execute("SELECT desc, imj FROM sales")
        data = cursor.fetchall()

        if data:
            for description, image_blob in data:
                # Отправка сообщения с изображением и описанием
                image = Image.open(BytesIO(image_blob))
                image_bytes = BytesIO()
                image.save(image_bytes, format='PNG')
                image_bytes.seek(0)

                await bot.send_photo(
                    callback_query.chat.id,
                    photo=image_bytes,
                    caption=description
                )
                

        else:
            await bot.send_message(callback_query.chat.id, 'Извините, акций пока нет.')

    except Exception as e:
        print(f"Error fetching promotions: {e}")

    finally:
        # Закрытие соединения с базой данных
        conn.close()


@dp.message_handler(lambda message: message.text.lower() == 'контакты', state='*')
async def process_contacts(message: types.Message):
    conn = sqlite3.connect('mag.db')
    cursor = conn.cursor()

    # Получение фото из таблицы
    cursor.execute("SELECT photo FROM contact_info")
    photo_data = cursor.fetchone()[0]

    # Закрытие соединения с базой данных
    conn.close()

    # Отправка фото пользователю
    await bot.send_photo(message.chat.id, photo_data, caption="*Наши контакты:*\n`ЛО, г.Волхов, Железнодорожный переулок 8`\n*Телефон:* `+7 952 224-33-22` (WhatsApp, Telegram)\n\
*Режим работы:*\n_Понедельник - пятница_ с 9.00 до 19.00\n_Суббота_ - с 9.00 до 18.00\n\
_Воскресенье_ - выходной\nwww.47moto.ru - Интернет магазин мото/вело/инструмент", reply_markup=menu_button(), parse_mode="markdown")


@dp.message_handler(state=OrderForm.name)
async def process_name(message: types.Message, state: FSMContext):
    if message.text.lower() == 'назад':
        await state.finish()
        await menu(message)
    else:
        if validate_russian_name(message.text):
            async with state.proxy() as data:
                data['name'] = message.text
            await message.answer("Напишите ваш номер телефона, на котором установлен телеграм!", reply_markup=get_base_keyboard())
            await OrderForm.phone.set()
        else:
            await message.answer("Ваше имя содержит латиницу либо цифры! Попробуйте еще раз!")
            await OrderForm.name.set()

@dp.message_handler(state=OrderForm.phone)
async def process_phone(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await bot.send_message(message.chat.id, 'Давайте познакомимся!\nКак вас зовут?', reply_markup=get_base_keyboard())
        await OrderForm.previous()
    else:
        if validate_russian_phone_number(message.text):
            async with state.proxy() as data:
                data['phone'] = message.text
            await message.answer("У Вас есть VIN код авто?", reply_markup=btn_from_vin())
            await OrderForm.vin_check.set()
        else:
            await message.answer("Неверный формат номера! Попробуйте еще раз!")
            await OrderForm.phone.set()


@dp.message_handler(state=OrderForm.vin_check)
async def process_vin(message:types.Message, state: FSMContext):
    if message.text.lower() == 'да':
        await message.answer("Введите VIN код Вашего авто:")
        await OrderForm.vin_code.set()
    elif message.text.lower() == 'нет':
        await message.answer("Напишите марку и модель Вашего авто, год выпуска, объем двигателя:", reply_markup=get_base_keyboard())
        await OrderForm.car_make.set()
    elif message.text.lower() == 'назад':
        await bot.send_message(message.chat.id, 'Напишите ваш номер телефона, на котором установлен телеграм!', reply_markup=get_base_keyboard())
        await OrderForm.previous()

@dp.message_handler(state=OrderForm.vin_code)
async def process_vin_code(message:types.Message, state: FSMContext):
    if message.text.lower() == "назад":
        await bot.send_message(message.chat.id, 'У вас есть VIN код?', reply_markup=get_base_keyboard())
        await OrderForm.previous()
    else:
        current_state = await state.get_state()
        await state.update_data(previous_state=current_state)
        async with state.proxy() as data:
            data['vin'] = message.text
        await message.answer("Напишите список необходимых запчастей:", reply_markup=get_base_keyboard())
        await OrderForm.parts_list.set()

@dp.message_handler(state=OrderForm.car_make)
async def process_vin_code(message:types.Message, state: FSMContext):
    if message.text.lower() == "назад":
        await bot.send_message(message.chat.id, 'У Вас есть VIN код авто?', reply_markup=btn_from_vin())
        await OrderForm.vin_check.set()
    else:
        current_state = await state.get_state()
        await state.update_data(previous_state=current_state)
        async with state.proxy() as data:
            data['car_make'] = message.text
        await message.answer("Напишите список необходимых запчастей:", reply_markup=get_base_keyboard())
        await OrderForm.parts_list.set()

@dp.message_handler(state=OrderForm.parts_list)
async def process_parts_list(message:types.Message, state: FSMContext):
    if message.text.lower() == "назад":
        user_data = await state.get_data()
        previous_state = user_data.get('previous_state')
        if previous_state == "OrderForm:vin_code":
            await bot.send_message(message.chat.id, 'Введите VIN код Вашего авто:', reply_markup=get_base_keyboard())
            await OrderForm.vin_code.set()
        elif previous_state == "OrderForm:car_make":
            await bot.send_message(message.chat.id, 'Напишите марку и модель Вашего авто, год выпуска, объем двигателя:', reply_markup=get_base_keyboard())
            await OrderForm.car_make.set()
    else:
        async with state.proxy() as data:
            data['parts_list'] = message.text
        await message.answer("Спасибо! Вскоре наши менеджеры свяжутся с Вами, для уточнения деталей.")
        user_data = await state.get_data()
        name = user_data.get('name')
        phone = user_data.get('phone')
        vin = user_data.get('vin', 'Не указан')
        car_make = user_data.get('car_make', 'Не указан')
        parts_list = user_data.get('parts_list')
        order_summary = (f"*Заказ автозапчастей:*\n"
                        f"*Имя:* {name}\n"
                        f"*Телефон:* `{phone}`\n"
                        f"*VIN:* {vin}\n"
                        f"*Марка авто:* {car_make}\n"
                        f"*Список запчастей:* {parts_list}")

        # Отправка сообщения администратору или другому пользователю
        await bot.send_message(Tokens.group_id, order_summary, parse_mode="markdown")
        await state.finish()


# Методы для 2 ветки

@dp.message_handler(state=SecondForm.name)
async def moto_process_name(message: types.Message, state: FSMContext):
    if message.text.lower() == 'назад':
        await state.finish()
        await menu(message)
    else:
        if validate_russian_name(message.text):
            async with state.proxy() as data:
                data['name'] = message.text
            await message.answer("Напишите ваш номер телефона, на котором установлен телеграм!", reply_markup=get_base_keyboard())
            await SecondForm.phone.set()
        else:
            await message.answer("Ваше имя содержит латиницу либо цифры! Попробуйте еще раз!")
            await SecondForm.name.set()


@dp.message_handler(state=SecondForm.phone)
async def moto_process_phone(message: types.Message, state: FSMContext):
    if message.text.lower() == "назад":
        await bot.send_message(message.chat.id, 'Давайте познакомимся!\nКак вас зовут?', reply_markup=get_base_keyboard())
        await SecondForm.previous()
    else:
        if validate_russian_phone_number(message.text):
            async with state.proxy() as data:
                data['phone'] = message.text
            await message.answer("Напишите вид Вашей техники или инструмента", reply_markup=get_base_keyboard())
            await SecondForm.view.set()
        else:
            await message.answer("Неверный формат номера! Попробуйте еще раз!")
            await SecondForm.phone.set()

@dp.message_handler(state=SecondForm.view)
async def moto_process_marka(message: types.Message, state: FSMContext):
    if message.text.lower() == "назад":
        await bot.send_message(message.chat.id, 'Напишите ваш номер телефона, на котором установлен телеграм!', reply_markup=get_base_keyboard())
        await SecondForm.previous()
    else:
        async with state.proxy() as data:
            data['view'] = message.text
        await message.answer("Укажите модель или марку", reply_markup=get_base_keyboard())
        await SecondForm.model.set()

@dp.message_handler(state=SecondForm.model)
async def moto_process_model(message: types.Message, state: FSMContext):
    if message.text.lower() == "назад":
        await bot.send_message(message.chat.id, 'Напишите вид Вашей техники или инструмента', reply_markup=get_base_keyboard())
        await SecondForm.previous()
    else:
        async with state.proxy() as data:
            data['model'] = message.text
        await message.answer("Напишите список необходимых запчастей", reply_markup=get_base_keyboard())
        await SecondForm.order.set()

@dp.message_handler(state=SecondForm.order)
async def moto_process_order(message: types.Message, state: FSMContext):
    if message.text.lower() == "назад":
        await bot.send_message(message.chat.id, 'Укажите модель или марку', reply_markup=get_base_keyboard())
        await SecondForm.previous()
    else:
        async with state.proxy() as data:
            data['order'] = message.text
        await message.answer("Спасибо! Вскоре наши менеджеры свяжутся с Вами, для уточнения деталей.")
        user_data = await state.get_data()
        name = user_data.get('name')
        phone = user_data.get('phone')
        view = user_data.get('view')
        model = user_data.get('model')
        order = user_data.get('order')
        order_summary = (f"*Заказ автозапчастей:*\n"
                        f"*Имя:* {name}\n"
                        f"*Телефон:* `{phone}`\n"
                        f"*Вид техники или инструмента:* {view}\n"
                        f"*Модель/марка:* {model}\n"
                        f"*Список запчастей:* {order}")

        # Отправка сообщения администратору или другому пользователю
        await bot.send_message(Tokens.group_id, order_summary, parse_mode="markdown")
        await state.finish()

if __name__ == '__main__':
    print("Bot started")
    executor.start_polling(dp, skip_updates=True)