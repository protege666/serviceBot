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

storage = MemoryStorage()

dotenv = dotenv.load_dotenv("config/.env")

class Tokens():
    bot_token = os.environ['TOKEN']
    admin_id = os.environ['ADMIN_ID']

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
    marka = State()
    model = State()
    order = State()

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


@dp.message_handler(commands=['menu'])
async def menu(message: types.Message):
    await message.answer("Выберите опцию:", reply_markup=menu_button())

@dp.message_handler(commands=['start'])
async def start_message(message: types.Message):
    await bot.send_message(message.from_user.id, "*Наш БОТ, может вам предложить:*\n\
Подбор запчастей не выходя из дома, на многие виды техники и инструмента.\n\
Оригинальные и бюджетные аналоги.\n\
Доступные цены и гарантия качества.\n\
Удобный способ оплаты.\n\
*А так же при заказе запчастей через БОТ, бесплатная доставка в пределах города Волхов!!!*\n\
1. Для подбора запчастей выберите соответствующий раздел\n\
2. Заполните форму заявки\n\
3. Ожидайте, наши менеджеры с Вами свяжутся", parse_mode="markdown")
    await menu(message)


@dp.message_handler(commands=['admin'])
async def admin_menu(message: types.Message):
    if str(message.from_user.id) == Tokens.admin_id:
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
                    callback_query.from_user.id,
                    photo=image_bytes,
                    caption=description
                )
                

        else:
            await bot.send_message(callback_query.from_user.id, 'Извините, акций пока нет.')

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
    await bot.send_photo(message.from_user.id, photo_data, caption="*Наши контакты:*\n`ЛО, г.Волхов, Железнодорожный переулок 8`\n*Телефон:* `+7 952 224-33-22` (WhatsApp, Telegram)\n\
*Режим работы:*\n_Понедельник - пятница_ с 9.00 до 19.00\n_Суббота_ - с 9.00 до 18.00\n\
_Воскресенье_ - выходной\nwww.47moto.ru - Интернет магазин мото/вело/инструмент", reply_markup=menu_button(), parse_mode="markdown")


@dp.message_handler(state=OrderForm.name)
async def process_name(message: types.Message, state: FSMContext):
    if message.text.lower() == 'назад':
        await state.finish()
        await menu(message)
    else:    
        async with state.proxy() as data:
            data['name'] = message.text
        await message.answer("Напишите ваш номер телефона, на котором установлен телеграм!", reply_markup=get_base_keyboard())
        await OrderForm.phone.set()

@dp.message_handler(state=OrderForm.phone)
async def process_phone(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await bot.send_message(message.from_user.id, 'Давайте познакомимся!\nКак вас зовут?', reply_markup=get_base_keyboard())
        await OrderForm.previous()
    else:
        async with state.proxy() as data:
            data['phone'] = message.text
        await message.answer("У Вас есть VIN код авто?", reply_markup=btn_from_vin())
        await OrderForm.vin_check.set()

@dp.message_handler(state=OrderForm.vin_check)
async def process_vin(message:types.Message, state: FSMContext):
    if message.text.lower() == 'да':
        await message.answer("Введите VIN код Вашего авто:")
        await OrderForm.vin_code.set()
    elif message.text.lower() == 'нет':
        await message.answer("Напишите марку и модель Вашего авто, год выпуска, объем двигателя:", reply_markup=get_base_keyboard())
        await OrderForm.car_make.set()
    elif message.text.lower() == 'назад':
        await bot.send_message(message.from_user.id, 'Напишите ваш номер телефона, на котором установлен телеграм!', reply_markup=get_base_keyboard())
        await OrderForm.previous()

@dp.message_handler(state=OrderForm.vin_code)
async def process_vin_code(message:types.Message, state: FSMContext):
    if message.text.lower() == "назад":
        await bot.send_message(message.from_user.id, 'У вас есть VIN код?', reply_markup=get_base_keyboard())
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
        await bot.send_message(message.from_user.id, 'У Вас есть VIN код авто?', reply_markup=btn_from_vin())
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
            await bot.send_message(message.from_user.id, 'Введите VIN код Вашего авто:', reply_markup=get_base_keyboard())
            await OrderForm.vin_code.set()
        elif previous_state == "OrderForm:car_make":
            await bot.send_message(message.from_user.id, 'Напишите марку и модель Вашего авто, год выпуска, объем двигателя:', reply_markup=get_base_keyboard())
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
        await bot.send_message(Tokens.admin_id, order_summary, parse_mode="markdown")
        await state.finish()


# Методы для 2 ветки

@dp.message_handler(state=SecondForm.name)
async def moto_process_name(message: types.Message, state: FSMContext):
    if message.text.lower() == 'назад':
        await state.finish()
        await menu(message)
    else:    
        async with state.proxy() as data:
            data['name'] = message.text
        await message.answer("Напишите ваш номер телефона, на котором установлен телеграм!", reply_markup=get_base_keyboard())
        await SecondForm.phone.set()

@dp.message_handler(state=SecondForm.phone)
async def moto_process_phone(message: types.Message, state: FSMContext):
    if message.text.lower() == "назад":
        await bot.send_message(message.from_user.id, 'Давайте познакомимся!\nКак вас зовут?', reply_markup=get_base_keyboard())
        await SecondForm.previous()
    else:
        async with state.proxy() as data:
            data['phone'] = message.text
        await message.answer("Напишите вид Вашей техники или инструмента", reply_markup=get_base_keyboard())
        await SecondForm.marka.set()

@dp.message_handler(state=SecondForm.marka)
async def moto_process_marka(message: types.Message, state: FSMContext):
    if message.text.lower() == "назад":
        await bot.send_message(message.from_user.id, 'Напишите ваш номер телефона, на котором установлен телеграм!', reply_markup=get_base_keyboard())
        await SecondForm.previous()
    else:
        async with state.proxy() as data:
            data['marka'] = message.text
        await message.answer("Укажите модель или марку", reply_markup=get_base_keyboard())
        await SecondForm.model.set()

@dp.message_handler(state=SecondForm.model)
async def moto_process_model(message: types.Message, state: FSMContext):
    if message.text.lower() == "назад":
        await bot.send_message(message.from_user.id, 'Напишите вид Вашей техники или инструмента', reply_markup=get_base_keyboard())
        await SecondForm.previous()
    else:
        async with state.proxy() as data:
            data['model'] = message.text
        await message.answer("Напишите список необходимых запчастей", reply_markup=get_base_keyboard())
        await SecondForm.order.set()

@dp.message_handler(state=SecondForm.order)
async def moto_process_order(message: types.Message, state: FSMContext):
    if message.text.lower() == "назад":
        await bot.send_message(message.from_user.id, 'Укажите модель или марку', reply_markup=get_base_keyboard())
        await SecondForm.previous()
    else:
        async with state.proxy() as data:
            data['order'] = message.text
        await message.answer("Спасибо! Вскоре наши менеджеры свяжутся с Вами, для уточнения деталей.")
        user_data = await state.get_data()
        name = user_data.get('name')
        phone = user_data.get('phone')
        marka = user_data.get('marka')
        model = user_data.get('model')
        order = user_data.get('order')
        order_summary = (f"*Заказ автозапчастей:*\n"
                        f"*Имя:* {name}\n"
                        f"*Телефон:* `{phone}`\n"
                        f"*Вид техники или инструмента:* {marka}\n"
                        f"*Модель/марка:* {model}\n"
                        f"*Список запчастей:* {order}")

        # Отправка сообщения администратору или другому пользователю
        await bot.send_message(Tokens.admin_id, order_summary, parse_mode="markdown")
        await state.finish()


if __name__ == '__main__':
    print("Bot started")
    executor.start_polling(dp, skip_updates=True)