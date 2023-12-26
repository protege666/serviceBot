from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import dotenv
import os
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# Инициализация хранилища
storage = MemoryStorage()

# Использование хранилища при создании Dispatcher



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

# Кнопки меню
menu_kb = InlineKeyboardMarkup()
keybtn = ReplyKeyboardMarkup()
menu_kb.add(InlineKeyboardButton('Заказ автозапчастей', callback_data='order_parts'))
menu_kb.add(InlineKeyboardButton('Контакты', callback_data='contacts'))
menu_kb.add(InlineKeyboardButton('Акции', callback_data='promotions'))

@dp.message_handler(commands=['start', 'menu'])
async def menu(message: types.Message):
    await message.answer("Выберите опцию:", reply_markup=menu_kb)

@dp.callback_query_handler(lambda c: c.data == 'order_parts')
async def process_order_parts(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id, 'Как вас зовут?')
    await OrderForm.name.set()

@dp.callback_query_handler(lambda c: c.data == 'contacts')
async def process_contacts(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id, 'Контактная информация...')
    

@dp.callback_query_handler(lambda c: c.data == 'promotions')
async def process_promotions(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id, 'Информация об акциях...')

@dp.message_handler(state=OrderForm.name)
async def process_name(message: types.Message, state: FSMContext):
    if checkBtn:
        keybtn.add("Назад")
        checkBtn = False
    async with state.proxy() as data:
        data['name'] = message.text
    await message.answer("Ваш номер телефона?", reply_markup=keybtn)
    await OrderForm.next()

@dp.message_handler(state=OrderForm.phone)
async def process_phone(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        a = types.ReplyKeyboardRemove()
        await bot.send_message(message.from_user.id, 'Как вас зовут?', reply_markup=a)
        await OrderForm.previous()
    else:
        async with state.proxy() as data:
            data['phone'] = message.text
        await message.answer("У вас есть VIN код? (Да/Нет)", reply_markup=keybtn)
        await OrderForm.next()

@dp.message_handler(state=OrderForm.vin_check)
async def process_vin_check(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await message.answer("Ваш номер телефона?", reply_markup=keybtn)
        await OrderForm.previous()
    else:
        if message.text.lower() == 'да':
            await message.answer("Введите VIN код:")
            await OrderForm.vin_code.set()
        else:
            await message.answer("Напишите марку вашего авто:")
            await OrderForm.car_make.set()
@dp.message_handler(state=OrderForm.vin_code)
async def process_vin(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await message.answer("У вас есть VIN код? (Да/Нет)", reply_markup=keybtn)
        await OrderForm.previous()
    else:
        async with state.proxy() as data:
            data['vin'] = message.text
        await message.answer("Напишите список необходимых запчастей:")
        await OrderForm.parts_list.set()

@dp.message_handler(state=OrderForm.car_make)
async def process_make(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await message.answer("У вас есть VIN код? (Да/Нет)", reply_markup=keybtn)
        await OrderForm.previous()
    else:
        async with state.proxy() as data:
            data['car_make'] = message.text
        await message.answer("Напишите список необходимых запчастей:")
        await OrderForm.parts_list.set()

@dp.message_handler(state=OrderForm.parts_list)
async def process_parts_list(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        pass
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
        admin_id = '894294239'
        await bot.send_message(admin_id, order_summary)
        await state.finish()

@dp.message_handler(lambda message: message.text.lower() == 'назад', state='*')
async def go_back(message: types.Message, state: FSMContext):
    await OrderForm.previous()
    

if __name__ == '__main__':
    print("Bot started")
    executor.start_polling(dp, skip_updates=True)
