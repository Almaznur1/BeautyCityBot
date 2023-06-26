import os
import re
from pprint import pprint

from aiogram import Bot, Dispatcher
from aiogram.types import (Message, KeyboardButton, ReplyKeyboardMarkup,
                           InlineKeyboardButton, InlineKeyboardMarkup,
                           ReplyKeyboardRemove, CallbackQuery)
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.filters import CommandStart, Text, StateFilter
from aiogram.filters.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beautycity.settings')
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'
import django
from django.conf import settings

if not settings.configured:
    django.setup()

from beautycity.settings import TG_BOT_TOKEN
from mainapp.models import Registration, Client, Master, Hairdressing


# os.environ['DJANGO_SETTINGS_MODULE'] = 'beautycity.settings'
# django.setup()


storage: MemoryStorage = MemoryStorage()
bot: Bot = Bot(TG_BOT_TOKEN)
dp: Dispatcher = Dispatcher(storage=storage)


class FSM(StatesGroup):
    master_selection = State()
    time_selection = State()
    fill_name = State()
    fill_phone = State()
    fill_feedback = State()


def get_masters_hours(masters, schedule):
    for master in masters:
        for day, hours in schedule.items():
            lst = []
            for hour in hours:
                if master in schedule[day][hour]:
                    lst.append(hour)
                    masters_schedule[master][day] = lst
    return masters_schedule


schedule = Registration.free_time()
# pprint(schedule)
existing_users = [client.telegram_id for client in Client.objects.all()]
masters = [master.name for master in Master.objects.all()]
# masters_schedule = get_masters_hours(masters, schedule)

procedures = {}
for entry in Hairdressing.objects.all():
    procedures[entry.named] = entry.price

users: dict = {}
feedbacks: dict = {}

about_us_button: KeyboardButton = KeyboardButton(text='О нас')
feedback_button: KeyboardButton = KeyboardButton(text='Оставить отзыв')
appointment_button: KeyboardButton = KeyboardButton(text='Записаться на процедуру')
choose_master_button: KeyboardButton = KeyboardButton(text='Выбрать мастера')
choose_date_button: KeyboardButton = KeyboardButton(text='Выбрать дату и время')
help_button: KeyboardButton = KeyboardButton(text='Возникли вопросы? Свяжитесь с нашим менеджером')
yes_button: KeyboardButton = KeyboardButton(text='Да')
no_button: KeyboardButton = KeyboardButton(text='Нет')

approval_button: InlineKeyboardButton = InlineKeyboardButton(
    text='Продолжить', callback_data='Продолжить')

main_page_keyboard: ReplyKeyboardMarkup = ReplyKeyboardMarkup(keyboard=[
    [appointment_button], [feedback_button], [about_us_button], [help_button]
    ], resize_keyboard=True)
main_page_keyboard_without_feedback: ReplyKeyboardMarkup = ReplyKeyboardMarkup(
    keyboard=[[appointment_button], [about_us_button], [help_button]],
    resize_keyboard=True)
choose_master_or_date_keyboard: ReplyKeyboardMarkup = ReplyKeyboardMarkup(
    keyboard=[
        [choose_master_button], [choose_date_button], [help_button]
        ], resize_keyboard=True)
yes_no_keyboard: ReplyKeyboardMarkup = ReplyKeyboardMarkup(
    keyboard=[[yes_button, no_button]], resize_keyboard=True)

approval_keyboard: InlineKeyboardMarkup = InlineKeyboardMarkup(
    inline_keyboard=[[approval_button]])


@dp.message(CommandStart())
async def process_start_command(message: Message, state: FSMContext):
    users[message.from_user.id] = {'procedure': None,
                                   'date': None,
                                   'hour': None,
                                   'master': None,
                                   'name': None,
                                   'phone': None,
                                   }
    if message.from_user.id in existing_users:
        keyboard = main_page_keyboard
    else:
        keyboard = main_page_keyboard_without_feedback
    await message.answer(text='Hello',
                         reply_markup=keyboard)
    await state.set_state(default_state)


@dp.message(StateFilter(default_state),
            Text(text='О нас'))
async def process_about_us_button(message: Message):
    await message.answer(text='Больше, чем салон красоты.\nПредлагает полный '
                         'спектр услуг.\nРежим работы салона с 10:00 до 19:00',
                         reply_markup=main_page_keyboard)


@dp.message(StateFilter(default_state),
            Text(text=['Записаться на процедуру', 'Да']))
async def process_appointment_button(message: Message):
    kb_builder: ReplyKeyboardBuilder = ReplyKeyboardBuilder()
    buttons = [KeyboardButton(text=procedure) for procedure in procedures]
    kb_builder.row(*buttons, width=1)
    await message.answer(text='Выберите процедуру:',
                         reply_markup=kb_builder.as_markup(resize_keyboard=True))


@dp.message(StateFilter(default_state),
            lambda msg: msg.text in procedures)
async def show_prices(message: Message):
    users[message.from_user.id]['procedure'] = message.text
    await message.answer(text=f'Стоимость услуги {procedures[message.text]} рублей.',
                         reply_markup=approval_keyboard)


@dp.callback_query(StateFilter(default_state),
                   Text(text='Продолжить'))
async def process_approval(callback: CallbackQuery):
    await callback.answer(text='Принято!')
    await callback.message.answer(text='Выберите мастера и дату',
                                  reply_markup=choose_master_or_date_keyboard)


# случай, когда сначала выбираем мастера
@dp.message(StateFilter(default_state),
            Text(text='Выбрать мастера'))
async def process_master_selection(message: Message, state: FSMContext):
    kb_builder: ReplyKeyboardBuilder = ReplyKeyboardBuilder()
    buttons = [KeyboardButton(text=master) for master in masters]
    kb_builder.row(*buttons, width=2)
    kb_builder.row(help_button)
    await message.answer(text='Выберите мастера:',
                         reply_markup=kb_builder.as_markup(resize_keyboard=True))
    await state.set_state(FSM.master_selection)


# случай, когда сначала выбираем мастера
@dp.message(StateFilter(FSM.master_selection),
            lambda msg: msg.text in masters)
async def process_master_date_selection(message: Message):
    users[message.from_user.id]['master'] = message.text

    kb_builder: ReplyKeyboardBuilder = ReplyKeyboardBuilder()
    buttons = [KeyboardButton(text=date) for date in masters_schedule[message.text]]
    kb_builder.row(*buttons, width=4)
    kb_builder.row(help_button)
    await message.answer(text='Выберите день:',
                         reply_markup=kb_builder.as_markup(resize_keyboard=True))


# случай, когда сначала выбираем мастера
@dp.message(StateFilter(FSM.master_selection),
            lambda msg: re.fullmatch(r'\d\d\.\d\d \D\D', msg.text))
async def process_master_time_selection(message: Message):
    users[message.from_user.id]['date'] = message.text
    master = users[message.from_user.id]['master']
    date = message.text

    kb_builder: ReplyKeyboardBuilder = ReplyKeyboardBuilder()
    buttons = []
    for hour in schedule[date].keys():
        if hour in masters_schedule[master][date]:
            buttons.append(KeyboardButton(text=hour))
        else:
            buttons.append(KeyboardButton(text=f'{hour} - н/д'))
    kb_builder.row(*buttons, width=4)
    kb_builder.row(help_button)
    await message.answer(text='Выберите свободное время:',
                         reply_markup=kb_builder.as_markup(resize_keyboard=True))


# случай, когда сначала выбираем мастера
@dp.message(StateFilter(FSM.master_selection),
            lambda msg: re.fullmatch(r'\d\d\:\d\d', msg.text))
async def process_contact_inf(message: Message, state: FSMContext):
    users[message.from_user.id]['hour'] = message.text
    await message.answer(text='Введите ваше имя:', reply_markup=ReplyKeyboardRemove())
    await state.set_state(FSM.fill_name)


# случай, когда сначала выбираем время
@dp.message(StateFilter(default_state),
            Text(text='Выбрать дату и время'))
async def process_date_selection(message: Message, state: FSMContext):
    kb_builder: ReplyKeyboardBuilder = ReplyKeyboardBuilder()
    buttons = [KeyboardButton(text=date) for date in schedule.keys()]
    kb_builder.row(*buttons, width=3)
    kb_builder.row(help_button)
    await message.answer(text='Выберите день:',
                         reply_markup=kb_builder.as_markup(resize_keyboard=True))
    await state.set_state(FSM.time_selection)


# случай, когда сначала выбираем время
@dp.message(StateFilter(FSM.time_selection),
            lambda msg: re.fullmatch(r'\d\d\.\d\d \D\D', msg.text))
async def process_time_selection(message: Message):
    users[message.from_user.id]['date'] = message.text
    kb_builder: ReplyKeyboardBuilder = ReplyKeyboardBuilder()
    buttons = []
    for hour in schedule[message.text].keys():
        if schedule[message.text][hour]:
            buttons.append(KeyboardButton(text=hour))
        else:
            buttons.append(KeyboardButton(text=f'{hour} - н/д'))
    kb_builder.row(*buttons, width=4)
    kb_builder.row(help_button)
    await message.answer(text='Выберите свободное время:',
                         reply_markup=kb_builder.as_markup(resize_keyboard=True))


# случай, когда сначала выбираем время
@dp.message(StateFilter(FSM.time_selection),
            lambda msg: re.fullmatch(r'\d\d\:\d\d', msg.text))
async def process_time_master_selection(message: Message):
    users[message.from_user.id]['hour'] = message.text
    date = users[message.from_user.id]['date']
    hour = message.text
    kb_builder: ReplyKeyboardBuilder = ReplyKeyboardBuilder()
    buttons = [KeyboardButton(text=master) for master in schedule[date][hour]]
    kb_builder.row(*buttons, width=4)
    kb_builder.row(help_button)
    await message.answer(text='Выберите свободного мастера:',
                         reply_markup=kb_builder.as_markup(resize_keyboard=True))


# случай, когда сначала выбираем время
@dp.message(StateFilter(FSM.time_selection),
            lambda msg: msg.text.isalpha())
async def process_contact_inf_2(message: Message, state: FSMContext):
    users[message.from_user.id]['master'] = message.text
    await message.answer(text='Введите ваше имя:\nВводя данные вы даете '
                         'согласие на обработку ваших персональных данных',
                         reply_markup=ReplyKeyboardRemove())
    await state.set_state(FSM.fill_name)


@dp.message(StateFilter(FSM.fill_name),
            lambda msg: msg.text.replace(' ', '').isalpha())
async def process_name_input(message: Message, state: FSMContext):
    users[message.from_user.id]['name'] = message.text
    await message.answer(text='Введите ваш номер:')
    await state.set_state(FSM.fill_phone)


@dp.message(StateFilter(FSM.fill_phone))
async def process_phone_input(message: Message, state: FSMContext):
    users[message.from_user.id]['phone'] = message.text
    users[message.from_user.id]['telegram_id'] = message.from_user.id
    await message.answer(
        text=f'Вы записаны на услугу:\n"{users[message.from_user.id]["procedure"]}"\nв '
        f'{users[message.from_user.id]["date"]} {users[message.from_user.id]["hour"]}\n\n'
        f'Имя мастера:\n{users[message.from_user.id]["master"]}')
    await state.set_state(default_state)
    Registration.create(users[message.from_user.id])
    # TODO: send_appointment(users[message.from_user.id]) - Функция, которая отправляет собранные в словарь users данные в БД для текущего пользователя


@dp.message(StateFilter(default_state),
            Text(text='Оставить отзыв'))
async def process_feedback_master(message: Message, state: FSMContext):
    kb_builder: ReplyKeyboardBuilder = ReplyKeyboardBuilder()
    buttons = [KeyboardButton(text=master) for master in masters]
    kb_builder.row(*buttons, width=3)
    await message.answer(
        text='Выберите мастера:',
        reply_markup=kb_builder.as_markup(resize_keyboard=True))
    await state.set_state(FSM.fill_feedback)


@dp.message(StateFilter(FSM.fill_feedback),
            lambda msg: msg.text in masters)
async def process_feedback(message: Message, state: FSMContext):
    await message.answer(text='Оставьте ваш отзыв:',
                         reply_markup=ReplyKeyboardRemove())


@dp.message(StateFilter(FSM.fill_feedback),
            ~Text(text=['Записаться на процедуру', 'О нас', 'Возникли вопросы? Свяжитесь с нашим менеджером', 'Оставить отзыв']))
async def send_feedback(message: Message, state: FSMContext):
    feedbacks[message.from_user.id] = message.text
    await message.answer(text='Спасибо за отзыв!')
    await message.answer(text='Желаете записаться на новую процедуру?',
                         reply_markup=yes_no_keyboard)
    await state.set_state(default_state)
    # TODO send_feedback(feedbacks[message.from_user.id]) - Функция, которая отправляет отзыв в БД


@dp.message(Text(text='Возникли вопросы? Свяжитесь с нашим менеджером'))
async def process_help_button(message: Message):
    await message.answer(text='У вас возникли вопросы?\nПожалуйста, свяжитесь '
                         'с нашим менеджером по номеру: +7(ххх)ххх-хх-хх')


@dp.message(~Text(text='Нет'))
async def process_incorrect_input(message: Message):
    await message.answer(text='Ошибка ввода! Пожалуйста, введите корректные данные.')


# StateFilter(default_state)
# ReplyKeyboardRemove()
if __name__ == '__main__':
    dp.run_polling(bot)