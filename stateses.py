from aiogram.dispatcher.filters.state import StatesGroup, State


class User_state(StatesGroup):
    name = State()
    photo = State()
    phone = State()
    city_id = State()
    user_id = State()
    Adrole = State()
    Delrole = State()

class NewUser_state(StatesGroup):
    name = State()
    photo = State()
    phone = State()
    city_id = State()
    user_id = State()


class Game_state(StatesGroup):
    time = State()
    date = State()
    price = State()
    photo = State()

class NewGame_state(StatesGroup):
    time = State()
    date = State()
    price = State()
    photo = State()


class Place_state(StatesGroup):
    name = State()
    prepay = State()
    price = State()
    seats = State()


class City_state(StatesGroup):
    name = State()


class News_state(StatesGroup):
    reg_news = State()
    all_news = State()
