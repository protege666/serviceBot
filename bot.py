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

bot = Bot(token=os.environ['TOKEN'])
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

class OrderForm(StatesGroup):
    name = State()
    phone = State()
    vin_check = State()
    vin_code = State()
    parts_list = State()
    car_make = State()

def menu_button():
    menu_btn = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
    menu_btn.add(KeyboardButton("Заказ автозапчастей"), KeyboardButton("Заказ запчастей мото, вело, инструменты"))
    menu_btn.add(KeyboardButton("Контакты"), KeyboardButton("Акции"))
    return menu_btn

# menu_kb = InlineKeyboardMarkup()
# menu_kb.add(InlineKeyboardButton('Заказ автозапчастей', callback_data='order_parts'))
# menu_kb.add(InlineKeyboardButton('Контакты', callback_data='contacts'))
# menu_kb.add(InlineKeyboardButton('Акции', callback_data='promotions'))

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

@dp.message_handler(commands=['start', 'menu'])
async def menu(message: types.Message):
    await message.answer("Выберите опцию:", reply_markup=menu_button())


@dp.message_handler(lambda message: message.text.lower() == 'заказ автозапчастей', state='*')
async def process_order_parts(message: types.Message):
    await message.answer("Как вас зовут?", reply_markup=get_base_keyboard())
    await OrderForm.name.set()

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

# @dp.callback_query_handler(lambda c: c.data == 'order_parts')
# async def process_order_parts(callback_query: types.CallbackQuery):
#     await bot.send_message(callback_query.from_user.id, 'Как вас зовут?')
#     await OrderForm.name.set()

@dp.callback_query_handler(lambda c: c.data == 'contacts')
async def process_contacts(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id, 'Контактная информация...')
    

# @dp.callback_query_handler(lambda c: c.data == 'promotions')
# async def process_promotions(callback_query: types.CallbackQuery):
#     await bot.send_message(callback_query.from_user.id, 'Информация об акциях...')

@dp.message_handler(state=OrderForm.name)
async def process_name(message: types.Message, state: FSMContext):
    if message.text.lower() == 'назад':
        await state.finish()
        await menu(message)
    else:    
        async with state.proxy() as data:
            data['name'] = message.text
        await message.answer("Ваш номер телефона?", reply_markup=get_base_keyboard())
        await OrderForm.phone.set()

@dp.message_handler(state=OrderForm.phone)
async def process_phone(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await bot.send_message(message.from_user.id, 'Как вас зовут?', reply_markup=get_base_keyboard())
        await OrderForm.previous()
    else:
        async with state.proxy() as data:
            data['phone'] = message.text
        await message.answer("У вас есть VIN код?", reply_markup=btn_from_vin())
        await OrderForm.vin_check.set()

@dp.message_handler(state=OrderForm.vin_check)
async def process_vin(message:types.Message, state: FSMContext):
    if message.text.lower() == 'да':
        await message.answer("Введите VIN код:")
        await OrderForm.vin_code.set()
    elif message.text.lower() == 'нет':
        await message.answer("Напишите марку вашего авто:", reply_markup=get_base_keyboard())
        await OrderForm.car_make.set()
    elif message.text.lower() == 'назад':
        await bot.send_message(message.from_user.id, 'Ваш номер телефона?', reply_markup=get_base_keyboard())
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
        await bot.send_message(message.from_user.id, 'У вас есть VIN код?', reply_markup=btn_from_vin())
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
            await bot.send_message(message.from_user.id, 'Введите VIN код:', reply_markup=get_base_keyboard())
            await OrderForm.vin_code.set()
        elif previous_state == "OrderForm:car_make":
            await bot.send_message(message.from_user.id, 'Напишите марку вашего авто:', reply_markup=get_base_keyboard())
            await OrderForm.car_make.set()
    else:
        async with state.proxy() as data:
            data['parts_list'] = message.text
        await message.answer("Спасибо за заказ, скоро с вами свяжутся!")
        user_data = await state.get_data()
        name = user_data.get('name')
        phone = user_data.get('phone')
        vin = user_data.get('vin', 'Не указан')
        car_make = user_data.get('car_make', 'Не указан')
        parts_list = user_data.get('parts_list')
        order_summary = (f"Заказ автозапчастей:\n"
                        f"Имя: {name}\n"
                        f"Телефон: {phone}\n"
                        f"VIN: {vin}\n"
                        f"Марка авто: {car_make}\n"
                        f"Список запчастей: {parts_list}")

        # Отправка сообщения администратору или другому пользователю
        admin_id = os.environ['ADMIN_ID']
        await bot.send_message(admin_id, order_summary)
        await state.finish()


if __name__ == '__main__':
    print("Bot started")
    executor.start_polling(dp, skip_updates=True)