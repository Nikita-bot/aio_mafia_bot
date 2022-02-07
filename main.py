#! /usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import os
import re
import time
import datetime
#from numpy import delete
import yadisk
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.storage import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import inline_keyboard, message, user
from aiogram.types.callback_query import CallbackQuery
from aiogram.types.reply_keyboard import ReplyKeyboardRemove
from aiogram.utils.exceptions import (MessageToEditNotFound, MessageCantBeEdited, MessageCantBeDeleted,
                                      MessageToDeleteNotFound)
from contextlib import suppress
from config import TOKEN, YanToken
from stateses import User_state, Game_state, Place_state, City_state, News_state, NewUser_state, NewGame_state
import data_base
import keyboards.city as kb_city


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
y = yadisk.YaDisk(token=YanToken)


user_info = {}
place_info = {}
game_info = {}

db = data_base.Data()


async def btn_users(users, game_id, callback):
    users_id = []
    users_name = {}
    btns_users = {}
    keyboard = types.InlineKeyboardMarkup()
    for i in users:
        users_id.append(i[1])
        users_name[i[1]] = i[0]
    for i in users_id:

        btns_users['btn_%s' % i] = types.InlineKeyboardButton(
            text=f'{users_name[i]}', callback_data=f'{callback}_{i}_{game_id}')
        keyboard.add(btns_users['btn_%s' % i])
    return [keyboard, users_id]


async def btn_place(city_id, callback):
    plases = db.show_place_in_city(city_id)
    plases_id = []
    plases_name = {}

    for i in (plases):
        plases_id.append(i[0])
        plases_name[i[0]] = i[1]

    btns_places = {}
    places_keyboard = types.InlineKeyboardMarkup()
    for i in plases_id:
        btns_places['btn_%s' % i] = types.InlineKeyboardButton(
            text=f'{plases_name[i]}', callback_data=f'{callback}_{i}_{city_id}')
        places_keyboard.add(btns_places['btn_%s' % i])
    return [places_keyboard, plases_id]


async def btn_gameplace(city_id, game_id):
    plases = db.show_place_in_city(city_id)
    plases_id = []
    plases_name = {}
    for i in (plases):
        plases_id.append(i[0])
        plases_name[i[0]] = i[1]
    btns_places = {}
    places_keyboard = types.InlineKeyboardMarkup()
    for i in plases_id:
        btns_places['btn_%s' % i] = types.InlineKeyboardButton(
            text=f'{plases_name[i]}', callback_data=f'btn_gplace_{i}_{game_id}_{city_id}')
        places_keyboard.add(btns_places['btn_%s' % i])
    return [places_keyboard, plases_id]

# _____START_____


@dp.message_handler(commands=['start'])
async def reg_message(message: types.Message):

    user_id = message.from_user.id
    user_info[user_id] = [user_id]

    info = db.show_user(message.from_user.id)
    if info == None:
        logger.info(f"{message.from_user.id} начал регистрацию")
        logger.info(f"{message.from_user.id} на этапе подтверждения номера")
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True,)
        button_phone = types.KeyboardButton(
            text="Подтвердить номер📲", request_contact=True)
        keyboard.add(button_phone)
        await bot.send_message(message.chat.id,
                               text="Вы новый пользователь!\nПоэтому давайте пройдём регистрацию\nДля начала подтвердите свой номер телефона\n кнопкой на клавиатуре",
                               reply_markup=keyboard)
    else:
        logger.info(f"{message.from_user.id} ввел 'start'")
        msg = await bot.send_message(message.chat.id, "Загружаем фото...")
        y.download(f'/avatar/{user_id}.jpg', f'./img/avatar/{user_id}.jpg')
        await bot.delete_message(message.chat.id, msg.message_id)
        await bot.send_photo(message.chat.id, photo=open(
            f'./img/avatar/{user_id}.jpg', 'rb'), caption=f"Рады видеть вас снова  `{info[1]}`", parse_mode='Markdown')
        os.remove(f'./img/avatar/{user_id}.jpg')
    return user


@dp.message_handler(content_types=['contact'], state='*')
async def photo_step(message: types.Message, state: FSMContext):
    logger.info(f"{message.from_user.id} выбирает фото")
    user_info[message.from_user.id].append(message.contact.phone_number)

    await bot.send_message(message.chat.id, 'Теперь отправьте фотографию для вашего профиля', reply_markup=types.ReplyKeyboardRemove())
    await User_state.photo.set()


@dp.message_handler(state=User_state.photo, content_types=['photo'])
async def name_step(message: types.Message, state: FSMContext):
    logger.info(f"{message.from_user.id} придумывает никнейм")
    async with state.proxy() as user:
        user['photo'] = message.photo[-1]  # .file_id
    

    await user['photo'].download(f'./img/avatar/{message.from_user.id}.jpg')
    if y.exists(f'/avatar/{message.from_user.id}.jpg'):
        y.remove(f'/avatar/{message.from_user.id}.jpg')
    y.upload(f'./img/avatar/{message.from_user.id}.jpg',
             f'/avatar/{message.from_user.id}.jpg')
    os.remove(f'./img/avatar/{message.from_user.id}.jpg')
    await bot.send_message(message.chat.id, 'Теперь введите свой никнейм')
    await User_state.name.set()


@dp.message_handler(state=User_state.name)
async def photo_step(message: types.Message, state: FSMContext):
    logger.info(f"{message.from_user.id} выбирает город")
    async with state.proxy() as user:
        user['name'] = message.text
    user_info[message.from_user.id].append(user['name'])

    await state.finish()
    keybd = (await kb_city.keyboard_city('btn_reg'))[0]
    await bot.send_message(message.chat.id, 'Осталось только выбрать ваш город😉',
                           reply_markup=keybd)


@dp.callback_query_handler(text_contains='btn_reg')
async def callback_citys(call: CallbackQuery):
    
    city_id = call.data.split('_')[2]
    user_info[call.from_user.id].append(city_id)

    city_name = db.show_city_info(city_id)
    print(user_info[call.from_user.id])
    await bot.edit_message_text(f'Вы выбрали {city_name[0][0]}', call.from_user.id, call.message.message_id, reply_markup=None)
    db.Insert_user(user_info[call.from_user.id])
    await bot.send_message(call.message.chat.id,
                           "Регистрация прошла успешно\nРады видеть вас!")

# _______________


@dp.message_handler(commands=['about'])
async def about(message: types.Message):
    await bot.send_message(message.chat.id, "Клуб легендарной игры Мафия в городах:\n Кемерово;\n Новокузнецк;\n Новосибирск;\n 🎭Мы верны традициям Мафии\n 🔝Легендарная Мафия в Сибири\n 😈Новичкам - добро пожаловать\n ☺️Тысячи довольных игроков\n1️⃣1️⃣ лет играем вместе с вами")
# _____HELP_____


@dp.message_handler(commands=['rules'])
async def rule(message: types.Message):
    info = db.show_user(message.from_user.id)
    if info == None:
        await bot.send_message(message.chat.id, "Вас не в нашей базе пользователей, чтобы зарегитрироваться введите: /start")
    else:
        await bot.send_message(message.chat.id, "Доброго времени суток, друзья\nИгра в мафию очень простая и делится на 2 этапа день и ночь, эти этапы чередуются\nДнем каждый по очереди высказывает свое мнение(У кого микрофон, тот и высказывается), кто же мафия за этим столом?\nВы можете выдвигать сколько угодно кандидатур, но в итоге проголосовать только за одного\nКогда все высказались у нас наступает голосование\nЛидер-тот,кто набирает больше всего голосов, показывает свою карту\nПосле этого наступает ночь\nГород засыпает, все плотно надевают свои маски и никто не подсматривает, если вас поймали за подглядыванием, вас удаляют из-за стола без оъяснения причины!\nПо команде просыпается Мафия, они снимают свои маски, за столом может быть от 2-х до 5-ти членов мафии\nМафия жестами договориваются, кого убить, в слух ничего говорить нельзя!\nПосле мафии просыпается Доктор\nЕсли вы доктор, то ваша задача угадать и вылечить того, кого убила мафия\nСебя доктор может вылечить 1 раз за игру\nПосле доктора просыпается волшебник\nЕсли вам досталась карта 'волшебник', вы можете выбрать одну из 3-х ролей ночью\nЖестом вы можете убить кого-то, проверить является ли человек мафией,или же стать доктором\nЕсли ведущий подтвердил, что это мафия, ваша задача днем подсказать людям, кто же является мафией, раскрывать, что вы волшебник, запрещено, поэтому выкручиваем ораторское искуство на максимум и даём людям подсказки\nПосле волшебника просыпается Камикадзе\nКамикадзе не делает ничего, но если вас убили, вы можете забрать с собой любого участника игры\nТакже у нас есть еще 2 интересных персонажа - Маньяк и Путана\nЭто мирные жители, которые могут по ночам убивать\nОни просыпаются по ночам и пытаются убить мафию\nЖертвы Маньяка умирают сразу\nЖертва Путаны еще день живет, но на следующее утро все равно помирает, болезнь не обратима и Доктору лечить жертв Путаны бесполезно\nИ последняя, но не по значению - карта 'Бомба'\nЕсли вам попалась эта карта, вы просыпаетесь один раз за игру и минируете от 3х до 5-ти человек\nЕсли кто угодно убивает бомбу, она взрывается и забирает с собой всех заминированных\nИ на последок правила за столом:\nЗа столом запрещено клясться, божиться, материться, переходить на личности\nТакже запрещено говорить свои роли, или прямо намекать на них, едиственное бомба может сказать 'Я бомба', устроить самоподрыв и забрать с собой заминированных")
    # правила


@dp.message_handler(commands=['help'])
async def help_message(message: types.Message):
    info = db.show_user(message.from_user.id)
    if info == None:
        await bot.send_message(message.chat.id, "Вас не в нашей базе пользователей, чтобы зарегитрироваться введите: /start")
    else:
        city = db.show_user(message.from_user.id)[3]
        if city == 0:
            await bot.send_message(message.chat.id, "Для начала выберите город в настройках профиля")
        else:
            admin = db.find_admin(city)
            if(admin is None):
                main = db.find_main()
                mention = []
                mention.append(f"[{main[2]}](tg://user?id={main[0]})")
                await bot.send_message(message.chat.id, "Администратора в вашем городе пока не назвачили, по всем вопросам пишите главному:\n" +
                                       '\n'.join(mention), parse_mode="Markdown")
            else:
                mention = []
                mention.append(f"[{admin[2]}](tg://user?id={admin[0]})")
                await bot.send_message(message.chat.id, "По всем вопросам пишите админу города:\n" +
                                       '\n'.join(mention), parse_mode="Markdown")
# _______________
# _____CORPORATE____


@dp.message_handler(commands=['corporate'])
async def corporate_message(message: types.Message):
    info = db.show_user(message.from_user.id)
    if info == None:
        await bot.send_message(message.chat.id, "Вас не в нашей базе пользователей, чтобы зарегитрироваться введите: /start")
    else:
        logger.info(f"{message.from_user.id} смотрит корпорат")
        keyboad_corp = types.InlineKeyboardMarkup()
        btn_yes = types.InlineKeyboardButton(
            text='Да', callback_data='yes')
        btn_no = types.InlineKeyboardButton(
            text='Нет', callback_data='no')
        keyboad_corp.add(btn_yes)
        keyboad_corp.add(btn_no)
        await bot.send_message(
            message.chat.id, 'Вы хотите заказать корпоративную игру?', reply_markup=keyboad_corp)


@dp.callback_query_handler(text_contains='yes')
async def callback_yes(call: CallbackQuery):
    info = db.show_user(call.from_user.id)
    if info == None:
        await bot.send_message(call.message.chat.id, "Вас не в нашей базе пользователей, чтобы зарегитрироваться введите: /start")
    else:
        await bot.edit_message_text("С вами скоро свяжется админ вашего города", call.from_user.id, call.message.message_id)
        user = db.show_user(call.from_user.id)
        if user[3] == 0:
            await bot.send_message(call.message.chat.id, "Для начала выберите город в настройках профиля")
        else:
            admin = db.find_admin(user[3])

            main = db.find_main()
            mention = []
            mention.append(f"[{user[1]}](tg://user?id={user[0]})")
            await bot.send_message(main[0], "Кто-то хочет заказать корпоративную игру:\n" +
                                   '\n'.join(mention), parse_mode="Markdown")
            await bot.send_message(admin[0], "Кто-то хочет заказать корпоративную игру:\n" +
                                   '\n'.join(mention), parse_mode="Markdown")


@dp.callback_query_handler(text_contains='no')
async def callback_no(call: CallbackQuery):
    await bot.edit_message_text("Хорошо, ждем вас на близжайших играх", call.from_user.id, call.message.message_id)

# _______________
# _____Afisha_____


@dp.message_handler(commands=['afisha'])
async def show_game(message: types.Message):
    info = db.show_user(message.from_user.id)

    
    if info == None:
        logger.info(f" {message.from_user.id} пытается посмотреть игры без регистрации")
        await bot.send_message(message.chat.id, "Вас не в нашей базе пользователей, чтобы зарегитрироваться введите: /start")
    else:
        logger.info(f" {message.from_user.id} смотрит игры")
        city_id = db.show_user(message.from_user.id)[3]
        if city_id == 0:
            await bot.send_message(message.chat.id, "Для начала выберите город в настройках профиля")
        else:
            result_game = db.show_game(city_id)
            result_pre_reg = db.show_prereg_game(message.from_user.id)
            count_user = 0
            if(len(result_pre_reg) == 0):
                result_pre_reg.append([0, 0])
            if(len(result_game) == 0):
                await bot.send_message(message.chat.id, 'В ближайшее время игр пока нет')
            else:

                game_id = []

                for i in result_pre_reg:
                    game_id.append(i[0])
                msg = await bot.send_message(message.chat.id, "Загружаем игры..")
                for i in result_game:

                    confirm_keyboard = None
                    time = i[3].strftime("%H:%M")
                    date = i[2].strftime("%d.%m.%Y")
                    day = int(date.split(".")[0])
                    month = int(date.split(".")[1])
                    year = int(date.split(".")[2])
                    hour = int(time.split(":")[0])
                    minute = int(time.split(":")[1])
                    date_del = datetime.datetime(
                        year, month, day, hour, minute)+datetime.timedelta(hours=4)
                    print(f"Дата удаления:{date_del}")
                    print("Сейчас:", datetime.datetime.now())
                    print(datetime.datetime.now() > date_del)
                    if datetime.datetime.now() > date_del:
                        db.del_prereg(i[0])
                        db.del_game(i[0])
                        if y.exists(f'/afisha/{str(city_id)+"_"+str(i[7])+"_"+str(i[2])}.jpg'):
                            y.remove(
                                f'/afisha/{str(city_id)+"_"+str(i[7])+"_"+str(i[2])}.jpg')
                            file_name = os.path.join(
                                f'img/afisha/{str(city_id)+"_"+str(i[7])+"_"+str(i[2])}.jpg')
                            os.remove(file_name)

                        if(len(db.show_game(city_id)) == 0):
                            await bot.send_message(message.chat.id, 'В ближайшее время игр пока нет')
                    else:

                        confirm_keyboard = types.InlineKeyboardMarkup()
                        who_goes = types.InlineKeyboardButton(
                            text="Кто идёт?", callback_data=f"who_goes_{i[0]}_{date}")
                        confirm_keyboard.add(who_goes)

                        if i[0] in game_id:

                            x = game_id[game_id.index(i[0])]
                            count_user = db.show_count_prereg_game(x)[0][0]

                        else:
                            if db.show_count_prereg_game(i[0])[0][0] is None:
                                count_user = 0
                            else:
                                count_user = db.show_count_prereg_game(i[0])[
                                    0][0]
                            place_left = i[4]-i[6]
                            confirm_keyboard = types.InlineKeyboardMarkup()
                            confirm_btn = types.InlineKeyboardButton(
                                text="Я иду ✔️", callback_data=f"confirm_1_{i[0]}_{i[8]}_{place_left}")
                            confirm_btn1 = types.InlineKeyboardButton(
                                text="Я иду + 1 ✔️", callback_data=f"confirm_2_{i[0]}_{i[8]}_{place_left}")
                            confirm_btn2 = types.InlineKeyboardButton(
                                text="Я иду + 2 ✔️", callback_data=f"confirm_3_{i[0]}_{i[8]}_{place_left}")
                            confirm_btn3 = types.InlineKeyboardButton(
                                text="Я иду + 3 ✔️", callback_data=f"confirm_4_{i[0]}_{i[8]}_{place_left}")
                            who_goes = types.InlineKeyboardButton(
                                text="Кто идёт?", callback_data=f"who_goes_{i[0]}_{date}")
                            confirm_keyboard.add(who_goes)
                            confirm_keyboard.add(confirm_btn)
                            confirm_keyboard.add(confirm_btn1)
                            confirm_keyboard.add(confirm_btn2)
                            confirm_keyboard.add(confirm_btn3)

                        y.download(f'afisha/{str(city_id)+"_"+str(i[7])+"_"+str(i[2])}.jpg',
                                   f'img/afisha/{str(city_id)+"_"+str(i[7])+"_"+str(i[2])}.jpg')

                        await bot.send_photo(message.chat.id, photo=open(
                            f'img/afisha/{str(city_id)+"_"+str(i[7])+"_"+str(i[2])}.jpg', 'rb'), caption=f"Заведение: `{i[1]}`\nДата проведения: `{date}`\nВремя: `{time}`\nЦена: `{i[5]}`\nПредоплата: `{i[8]}`\nОсталось мест: `{i[4]-i[6]}`\nУже идёт: `{i[6]}`\nПредварительно записались: `{count_user-i[6]}`", parse_mode='Markdown', reply_markup=confirm_keyboard)
                await bot.delete_message(message.chat.id, msg.message_id)


@dp.callback_query_handler(text_contains='who_goes')
async def callback_btn_who_goes(call: CallbackQuery):
    game_info = call.data.split("_")
    mention = []
    date = game_info[3]
    users = db.show_who_goes(game_info[2], 1)
    c = 1
    for i in users:
        mention.append(f"{c}. {i[0]}")
        c+=1
    if len(mention) == 0:
        await bot.send_message(
            call.message.chat.id, "Пока никто не регистрировался\nНо ты можешь стать первым(ой)!")
    else:
        await bot.send_message(call.message.chat.id, f"Запись на игру {date}:\n" +
                               '\n'.join(mention), parse_mode="Markdown")


@ dp.callback_query_handler(text_contains='confirm')
async def call_btn_confirm(call: CallbackQuery):

    user_id = call.from_user.id
    logger.info(f"{user_id} хочет подать заявку на игру")
    game_info = call.data.split("_")
    game_id = game_info[2]
    check_game = db.show_info_game(game_id)
    if len(check_game) == 0:
        await bot.send_message(call.message.chat.id, "Эта игра уже прошла,вы можете записаться на новые, введя команду: /afisha")
    else:
        count = int(game_info[1])
        place_left = int(game_info[4])
        if(place_left >= count):
            city_id = db.show_user(call.from_user.id)[3]
            prepay = game_info[3]

            result_pre_reg = db.show_prereg_game(call.from_user.id)
            if(len(result_pre_reg) == 0):
                result_pre_reg.append([0, 0])
            for i in result_pre_reg:
                if(int(game_id) == int(i[0])):
                    await bot.edit_message_caption(chat_id=call.message.chat.id,
                                                   message_id=call.message.message_id, caption='Вы уже подали заявку на данную игру', reply_markup=None)
                    break
                else:
                    admin = db.find_admin(city_id)

                    db.Insert_prereg_game(game_id, user_id, count)
                    await bot.edit_message_caption(chat_id=call.message.chat.id,
                                                   message_id=call.message.message_id, caption=f'Для записи на игру от вас необходима предоплата {prepay}р с человека.\nПеревод на карту Сбербанк по номеру телефона:{admin[1]}.\n В переводе укажите ваш ник\n В случае отказа от игры за 24 часа до игры, предоплата возвращается.', reply_markup=None)
                    admin_id = db.find_admin(city_id)[0]
                    if admin_id is None:
                        admin_id = db.find_main()[0]
                    user = db.show_user(user_id)
                    mention = []
                    mention.append(f"[{user[1]}](tg://user?id={user[0]})")
                    await bot.send_message(admin_id, f"Кто-то зарегистрировался на игру {check_game[0][2].strftime('%d.%m.%Y')}:\n" +
                                           '\n'.join(mention), parse_mode="Markdown")
                    break
        else:
            await bot.send_message(call.message.chat.id, "Свободных мест на столько человек не осталось!")

# ________________
# _____ADMIN_____


@dp.message_handler(commands=['admin'])
async def admin_panel(message: types.Message):
    user_id = message.from_user.id
    role = db.show_user(user_id)[4]
    if role > 0:  # главный админ панель
        if role == 2:
            keyboad_adm = types.InlineKeyboardMarkup()
            btn_game = types.InlineKeyboardButton(
                text='Игры🎲', callback_data='btn_game')
            btn_news = types.InlineKeyboardButton(
                text='Общая рассылка', callback_data='btn_news_0')
            btn_rnews = types.InlineKeyboardButton(
                text='Рассылка по городу', callback_data='btn_rnews_0')
            btn_user = types.InlineKeyboardButton(
                text='Пользователи👨', callback_data='btn_user')
            btn_city = types.InlineKeyboardButton(
                text='Города🏙', callback_data='btn_adm_city')

            keyboad_adm.add(btn_game)
            keyboad_adm.add(btn_user)
            keyboad_adm.add(btn_city)
            keyboad_adm.add(btn_news)
            keyboad_adm.add(btn_rnews)
            await bot.send_message(
                message.chat.id, 'Добро пожаловать в главную админ панель', reply_markup=keyboad_adm)
        else:
            keyboad_adm = types.InlineKeyboardMarkup()
            btn_game = types.InlineKeyboardButton(
                text='Игры🎲', callback_data='btn_game')
            btn_user = types.InlineKeyboardButton(
                text='Пользователи👨', callback_data='btn_user')
            btn_rnews = types.InlineKeyboardButton(
                text='Рассылка по городу', callback_data='btn_rnews_0')
            keyboad_adm.add(btn_game)
            keyboad_adm.add(btn_user)
            keyboad_adm.add(btn_rnews)
            await bot.send_message(
                message.chat.id, 'Добро пожаловать в главную админ панель', reply_markup=keyboad_adm)

    else:
        await bot.send_message(message.chat.id, 'Вы не администратор данного бота')

# _____ADMIN/NEWS_____


@dp.callback_query_handler(text_contains='btn_rnews')
async def callback_btn_rnews(call: CallbackQuery):
    news = call.data.split('_')[2]
    if(int(news) == 0):
        keyboad = types.InlineKeyboardMarkup()
        btn_photo = types.InlineKeyboardButton(
            text='Новость с фото', callback_data='btn_rnews_1')
        btn_text = types.InlineKeyboardButton(
            text='Новость без фото', callback_data='btn_rnews_2')
        keyboad.add(btn_photo)
        keyboad.add(btn_text)
        await bot.edit_message_text('Выберите тип новости', call.message.chat.id, call.message.message_id, reply_markup=keyboad)
    if(int(news) == 1):
        await bot.edit_message_text("Какую новость разослать?", call.from_user.id, call.message.message_id)
        await News_state.reg_news_photo.set()
    if(int(news) == 2):
        await bot.edit_message_text("Какую новость разослать?", call.from_user.id, call.message.message_id)
        await News_state.reg_news_text.set()


@dp.message_handler(state=News_state.reg_news_text)
async def rnews_state(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text
    city_id = db.show_user(message.from_user.id)[3]
    await state.finish()
    for i in db.show_all_users(city_id):
        await bot.send_message(i[0], data['text'])


@dp.message_handler(state=News_state.reg_news_photo, content_types=['photo'])
async def news_state(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.caption
        photo = message.photo[-1].file_id
    city_id = db.show_user(message.from_user.id)[3]
    await state.finish()
    for i in db.show_all_users(city_id):
        await bot.send_photo(i[0], photo=photo, caption=data['text'])


@ dp.callback_query_handler(text_contains='btn_news')
async def callback_btn_news(call: CallbackQuery):
    news = call.data.split('_')[2]

    if(int(news) == 0):
        keyboad = types.InlineKeyboardMarkup()
        btn_photo = types.InlineKeyboardButton(
            text='Новость с фото', callback_data='btn_news_1')
        btn_text = types.InlineKeyboardButton(
            text='Новость без', callback_data='btn_news_2')
        keyboad.add(btn_photo)
        keyboad.add(btn_text)
        await bot.edit_message_text('Выберите тип новости', call.message.chat.id, call.message.message_id, reply_markup=keyboad)
    if(int(news) == 1):
        await bot.edit_message_text("Какую новость разослать?", call.from_user.id, call.message.message_id)
        await News_state.all_news_photo.set()
    if(int(news) == 2):
        await bot.edit_message_text("Какую новость разослать?", call.from_user.id, call.message.message_id)
        await News_state.all_news_text.set()


@dp.message_handler(state=News_state.all_news_text)
async def rnews_state(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text
    await state.finish()
    for i in db.show_all_users('city_id'):
        await bot.send_message(i[0], data['text'])


@dp.message_handler(state=News_state.all_news_photo, content_types=['photo'])
async def news_state(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.caption
        photo = message.photo[-1].file_id
    await state.finish()
    for i in db.show_all_users('city_id'):
        await bot.send_photo(i[0], photo=photo, caption=data['text'])

# _____ADMIN/NEWS_____

# _____ADMIN/USERS_____


@dp.callback_query_handler(text_contains='btn_user')
async def callback_btn_user(call: CallbackQuery):
    user_id = call.from_user.id
    role = db.show_user(user_id)[4]
    if role == 2:
        keyboard = types.InlineKeyboardMarkup()
        btn_role = types.InlineKeyboardButton(
            text="Настройки ролей", callback_data="btn_edit_role")
        btn_allUsers = types.InlineKeyboardButton(
            text="Вывести всех пользователей", callback_data="btn_allUser")
        keyboard.add(btn_allUsers)
        keyboard.add(btn_role)
        await bot.edit_message_text("Что вы хотите сделать с пользователями?", call.from_user.id, call.message.message_id, reply_markup=keyboard)
    elif role == 1:
        keyboard = types.InlineKeyboardMarkup()
        btn_allUsers = types.InlineKeyboardButton(
            text="Вывести всех пользователей", callback_data="btn_allUser")
        keyboard.add(btn_allUsers)

        await bot.edit_message_text("Что вы хотите сделать с пользователями?", call.from_user.id, call.message.message_id, reply_markup=keyboard)


@dp.callback_query_handler(text_contains='btn_allUser')
async def callback_btn_allUser(call: CallbackQuery):
    city_id = db.show_user(call.from_user.id)[3]
    users = db.show_all_users(city_id)
    mention = []
    for i in users:
        mention.append(f"[{i[1]}](tg://user?id={i[0]}) : Сыграл {i[3]} раз(а)")
    if len(mention) == 0:
        await bot.send_message(call.message.chat.id, "Пока никого нет")
    else:
        await bot.send_message(call.message.chat.id, "Список пользователей в вашем городе:\n" + '\n'.join(mention), parse_mode="Markdown")


@dp.callback_query_handler(text_contains='btn_cum')
async def callback_btn_cum(call: CallbackQuery):
    city_id = db.show_user(call.from_user.id)[3]
    games = db.show_game(city_id)
    keyboard = types.InlineKeyboardMarkup()
    btns_games = {}
    games_date = {}
    games_id = []
    for i in (games):
        games_id.append(i[0])
        games_date[i[0]] = i[2].strftime('%d.%m.%Y')

    for i in games_id:
        btns_games['btn_%s' % i] = types.InlineKeyboardButton(
            text=f'{games_date[i]}', callback_data=f'btn_cgame_{i}')
        keyboard.add(btns_games['btn_%s' % i])
    await bot.edit_message_text("Выберете игру", call.from_user.id, call.message.message_id,
                                reply_markup=keyboard)


@dp.callback_query_handler(text_contains='btn_cgame')
async def callback_btn_cgame(call: CallbackQuery):
    game_id = call.data.split('_')[2]
    users = db.show_who_goes(game_id, 1)
    if(len(users) == 0):
        await bot.edit_message_text('Все отмечены!', call.from_user.id, call.message.message_id, reply_markup=None)
    else:
        user = (await btn_users(users, game_id, "btn_сusers"))[0]
        await bot.edit_message_text('Кто пришел на игру?', call.from_user.id, call.message.message_id, reply_markup=user)


@dp.callback_query_handler(text_contains='btn_сusers')
async def callback_btn_сusers(call: CallbackQuery):
    user_id = call.data.split('_')[2]
    game_id = call.data.split('_')[3]
    db.update_count(user_id, game_id)
    user = db.show_user(user_id)
    count = int(user[5])

    if (count == 25) or (count == 28):
        mention = []
        mention.append(f"[{user[1]}](tg://user?id={user[0]})")
        city_id = db.show_user(call.from_user.id)[3]
        admin = db.find_admin(city_id)[0]
        await bot.send_message(admin, f"Этот пользователь сыграл {count} раз(а) :\n" +
                               '\n'.join(mention), parse_mode="Markdown")
    users = db.show_who_goes(game_id, 1)
    if(len(users) == 0):
        await bot.edit_message_text('Все, кто хотел, пришли!', call.from_user.id, call.message.message_id, reply_markup=None)
    else:
        user = (await btn_users(users, game_id, "btn_сusers"))[0]
        await bot.edit_message_text('Кто пришел на игру?', call.from_user.id, call.message.message_id, reply_markup=user)


@dp.callback_query_handler(text_contains='btn_edit_role')
async def callback_btn_edit_role(call: CallbackQuery):
    keyboard = types.InlineKeyboardMarkup()
    btn_add_admin = types.InlineKeyboardButton(
        text="Назначить админа", callback_data="btn_add_admin")
    btn_del_admin = types.InlineKeyboardButton(
        text="Убрать админа", callback_data="btn_del_admin")
    keyboard.add(btn_add_admin, btn_del_admin)
    await bot.edit_message_text("Настройки ролей", call.from_user.id, call.message.message_id, reply_markup=keyboard)


@ dp.callback_query_handler(text_contains='btn_add_admin')
async def callback_btn_add_admin(call: CallbackQuery):
    await bot.edit_message_text("Введите ник пользователя", call.from_user.id, call.message.message_id, reply_markup=None)
    await User_state.Adrole.set()


@dp.message_handler(state=User_state.Adrole)
async def step_add_admin(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text

    db.change_role(data['text'], 1)
    await bot.send_message(
        message.chat.id, f"{data['text']} теперь админ своего города")
    await state.finish()


@dp.callback_query_handler(text_contains='btn_del_admin')
async def callback_del_add_admin(call: CallbackQuery):
    await bot.edit_message_text("Введите ник пользователя", call.from_user.id, call.message.message_id, reply_markup=None)
    await User_state.Delrole.set()


@dp.message_handler(state=User_state.Delrole)
async def step_del_admin(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text

    db.change_role(data['text'], 0)
    await bot.send_message(
        message.chat.id, f"{data['text']} теперь не админ своего города")
    await state.finish()


# ____ADMIN/USERS_____
# ____ADMIN/CITY____

@ dp.callback_query_handler(text_contains='btn_adm_city')
async def callback_adm_city(call: CallbackQuery):
    citys_menu = types.InlineKeyboardMarkup()
    btn_add_city = types.InlineKeyboardButton(
        text='Добавить город', callback_data='adm_add_city')
    btn_add_place_in_city = types.InlineKeyboardButton(
        text='Добавить заведение', callback_data='adm_add_place')
    btn_del_city = types.InlineKeyboardButton(
        text='Удалить город', callback_data='adm_del_city')
    btn_del_place_in_city = types.InlineKeyboardButton(
        text='Удалить заведение', callback_data='adm_del_place')
    citys_menu.add(btn_add_city)
    citys_menu.add(btn_add_place_in_city)
    citys_menu.add(btn_del_city)
    citys_menu.add(btn_del_place_in_city)

    await bot.edit_message_text("Меню города", call.from_user.id, call.message.message_id, reply_markup=citys_menu)


@ dp.callback_query_handler(text_contains='adm_add_city')
async def callback_adm_add_city(call: CallbackQuery):
    await bot.edit_message_text("Введите название города", call.from_user.id, call.message.message_id, reply_markup=None)
    await City_state.name.set()


@dp.message_handler(state=City_state.name)
async def add_city(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text
    db.Insert_city(data['text'])
    await bot.send_message(message.chat.id, f'Город {data["text"]} добавлен')
    await state.finish()


@ dp.callback_query_handler(text_contains='adm_del_city')
async def callback_adm_del_city(call: CallbackQuery):
    keybd = (await kb_city.keyboard_city('btn_dcity'))[0]
    await bot.edit_message_text("Какой город хотите удалить?", call.from_user.id, call.message.message_id, reply_markup=keybd)


@ dp.callback_query_handler(text_contains='btn_dcity')
async def callback_btn_dcity(call: CallbackQuery):
    city_id = call.data.split("_")[2]
    plases = db.show_place_in_city(city_id)
    if(len(plases) == 0):
        await bot.send_message(call.message.chat.id, 'Город удалён', reply_markup=None)
        users = db.show_all_users(city_id)
        for i in users:
            if(i[2] == 2):
                db.Change_city(0, i[0], 2)
            else:
                db.Change_city(0, i[0], 0)
            await bot.send_message(i[0], "В вашем городе временно не будут проводиться игры, вы можете изменить город в настройках профиля")

        db.del_city(city_id)
    else:
        place_id = []
        for i in plases:
            place_id.append(i[0])
        for i in place_id:
            result_game = db.show_game_in_place(i)
            if(len(result_game) == 0):
                db.del_place(i)
            else:
                game_id = []
                for j in result_game:
                    game_id.append(j[0])
                for j in game_id:
                    info = db.show_info_game(j)
                    old_info = []
                    old_info.append(info[0][0])
                    old_info.append(info[0][1])
                    old_info.append(info[0][2])
                    file_name = os.path.join(
                        "./img/afisha/", f"{old_info[0]}_{old_info[1]}_{old_info[2]}.jpg")
                    os.remove(file_name)
                    y.remove(
                        f'/afisha/{old_info[0]}_{old_info[1]}_{old_info[2]}.jpg')
                db.del_place(i)
        users = db.show_all_users(city_id)
        for i in users:
            if(i[2] == 2):
                db.Change_city(0, i[0], 2)
            else:
                db.Change_city(0, i[0], 0)
            await bot.send_message(i[0], "В вашем городе временно не будут проводиться игры, вы можете изменить город в настройках профиля")
        db.del_city(city_id)
        await bot.edit_message_text('Город удалён', call.message.chat.id, call.message.message_id, reply_markup=None)


@ dp.callback_query_handler(text_contains='adm_del_place')
async def callback_adm_del_place(call: CallbackQuery):
    keybd = (await kb_city.keyboard_city('btn_dplace'))[0]
    await bot.edit_message_text("Выберете город в котором находится заведение", call.from_user.id, call.message.message_id, reply_markup=keybd)


@ dp.callback_query_handler(text_contains='btn_dplace')
async def callback_btn_dplace(call: CallbackQuery):
    city_id = call.data.split("_")[2]
    places = (await btn_place(city_id, 'btn_delplace'))[0]
    await bot.edit_message_text('Какое заведение удалить?', call.from_user.id, call.message.message_id, reply_markup=places)


@ dp.callback_query_handler(text_contains='btn_delplace')
async def callback_btn_dplace(call: CallbackQuery):
    place_id = call.data.split('_')[2]
    result_game = db.show_game_in_place(place_id)
    if(len(result_game) == 0):
        db.del_place(place_id)
    else:
        game_id = []
        for i in result_game:
            game_id.append(i[0])
        for i in game_id:
            info = db.show_info_game(i)
            old_info = []
            old_info.append(info[0][0])
            old_info.append(info[0][1])
            old_info.append(info[0][2])
            file_name = os.path.join(
                "./img/afisha/", f"{old_info[0]}_{old_info[1]}_{old_info[2]}.jpg")
            os.remove(file_name)
            y.remove(f"afisha/{old_info[0]}_{old_info[1]}_{old_info[2]}.jpg")

        db.del_place(place_id)
    await bot.edit_message_text('Заведение удалено', call.from_user.id, call.message.message_id, reply_markup=None)


@ dp.callback_query_handler(text_contains='adm_add_place')
async def callback_adm_add_place(call: CallbackQuery):
    keybd = (await kb_city.keyboard_city('btn_aplace'))[0]
    await bot.edit_message_text("Выберете город в котором находится заведение", call.from_user.id, call.message.message_id, reply_markup=keybd)


@ dp.callback_query_handler(text_contains='btn_aplace')
async def callback_btn_aplace(call: CallbackQuery):
    place_info['city_id'] = call.data.split("_")[2]
    await bot.edit_message_text("Введите название заведения", call.message.chat.id, call.message.message_id)
    await Place_state.name.set()


@dp.message_handler(state=Place_state.name)
async def take_name_place(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text

    place_info['name'] = data['text']
    await bot.send_message(message.chat.id,
                           "Введите цену игры в заведении")
    await Place_state.price.set()


@dp.message_handler(state=Place_state.price)
async def take_price_place(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text
    place_info['price'] = data['text']
    await bot.send_message(message.chat.id,
                           "Введите кол-во мест в заведении")
    await Place_state.seats.set()


@dp.message_handler(state=Place_state.seats)
async def take_seats_place(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text
    place_info['seats'] = data['text']
    await bot.send_message(message.chat.id,
                           "Введите предоплату в заведении\nЕсли её не будет отправьте `0`", parse_mode="Markdown")
    await Place_state.prepay.set()


@dp.message_handler(state=Place_state.prepay)
async def add_places(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text
    place_info['prepay'] = data['text']
    db.insert_place(place_info)
    await bot.send_message(message.chat.id, 'Заведение добавлено')
    await state.finish()
# _____ADMIN/CITY_____
# _____ADMIN/GAME_____


@dp.callback_query_handler(text_contains='btn_game')
async def callback_admin_btn_game(call: CallbackQuery):  # админ меню

    keyboard = types.InlineKeyboardMarkup()
    btn_create_game = types.InlineKeyboardButton(
        text='Создать игру', callback_data='btn_create_game')
    btn_edit_game = types.InlineKeyboardButton(
        text='Настроить игру', callback_data='btn_edit_game')
    btn_pay_game = types.InlineKeyboardButton(
        text='Подтверждение оплаты игры', callback_data='btn_pay_game')
    btn_cume = types.InlineKeyboardButton(
        text="Отметить пришедших на игру", callback_data="btn_cum")

    keyboard.add(btn_create_game)
    keyboard.add(btn_edit_game)
    keyboard.add(btn_pay_game)
    keyboard.add(btn_cume)

    await bot.edit_message_text("Меню игр", call.from_user.id, call.message.message_id, reply_markup=keyboard)

# ____CREATE_GAME_____


@dp.callback_query_handler(text_contains='btn_create_game')
async def callback_admin_btn_creategame(call: CallbackQuery):
    admin = db.show_user(call.from_user.id)
    if admin[4] == 2:
        keybd = (await kb_city.keyboard_city('btn_cplace'))[0]
        await bot.edit_message_text("В каком городе?", call.from_user.id, call.message.message_id, reply_markup=keybd)
    else:
        city_id = db.show_user(call.from_user.id)[3]
        places = (await btn_place(city_id, 'btn_place'))[0]
        await bot.edit_message_text('В каком Заведении создать игру?', call.from_user.id, call.message.message_id, reply_markup=places)


@dp.callback_query_handler(text_contains='btn_cplace')
async def callback_admin_btn_creategame(call: CallbackQuery):
    city_id = call.data.split("_")[2]
    places = (await btn_place(city_id, 'btn_place'))[0]
    await bot.edit_message_text('В каком Заведении создать игру?', call.from_user.id, call.message.message_id, reply_markup=places)


@ dp.callback_query_handler(text_contains='btn_place')
async def call_btn_place_i(call: CallbackQuery):
    city_id = call.data.split("_")[3]
    game_info[call.from_user.id] = [city_id]
    game_info[call.from_user.id].append(call.data.split("_")[2])
    await bot.edit_message_text("Введите дату игры через '-', не раньше сегодняшнего дня\n Пример: 01-01-2022", call.message.chat.id, call.message.message_id)
    await Game_state.date.set()


@dp.message_handler(state=Game_state.date)
async def take_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text
        data = data['text']
    try:
        data = re.split(";|,|\n|-|:|\.", data)
        date = datetime.date(int(data[2]), int(data[1]), int(data[0]))
    except:
        await bot.send_message(chat_id=message.from_user.id,
                               text="Введите правильно дату\nПример  `01-01-2022`", parse_mode='Markdown')
        await Game_state.date.set()
    if (int(data[0]) < 0 or int(data[0]) > 31) or (int(data[1]) > 12 or int(data[1]) <= 0) or date < datetime.date.today():
        await bot.send_message(chat_id=message.from_user.id,
                               text="Введите правильно дату, не раньше сегодняшнего дня\nПример  `01-01-2022`", parse_mode='Markdown')
        await Game_state.date.set()
    else:
        game_info[message.from_user.id].append(data[2]+'-' +
                                               data[1]+'-'+data[0])
        await bot.send_message(message.chat.id, "Введите время проведения игры через :")
        await Game_state.time.set()


@dp.message_handler(state=Game_state.time)
async def take_time(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text
        time = data['text']
    time = re.split(";|,|\n|-|:|\.", time)

    if (int(time[0]) < 0 or int(time[0]) >= 23) or int(time[1]) >= 59:
        await bot.send_message(message.chat.id, "Введите правильно время\nПример  `22:22`", parse_mode='Markdown')
        await Game_state.time.set()

    else:
        game_info[message.from_user.id].append(time[0]+':'+time[1])
        await bot.send_message(message.chat.id, "Отправте фото игры")
        await Game_state.photo.set()


@dp.message_handler(state=Game_state.photo, content_types=['photo'])
async def name_step(message: types.Message, state: FSMContext):
    async with state.proxy() as game:
        game['photo'] = message.photo[-1]  # .file_id
    await game['photo'].download(f'./img/afisha/{game_info[message.from_user.id][0]}_{game_info[message.from_user.id][1]}_{game_info[message.from_user.id][2]}.jpg')
    if y.exists(f'/afisha/{game_info[message.from_user.id][0]}_{game_info[message.from_user.id][1]}_{game_info[message.from_user.id][2]}.jpg'):
        y.remove(
            f'/afisha/{game_info[message.from_user.id][0]}_{game_info[message.from_user.id][1]}_{game_info[message.from_user.id][2]}.jpg')
    y.upload(f'./img/afisha/{game_info[message.from_user.id][0]}_{game_info[message.from_user.id][1]}_{game_info[message.from_user.id][2]}.jpg',
             f'/afisha/{game_info[message.from_user.id][0]}_{game_info[message.from_user.id][1]}_{game_info[message.from_user.id][2]}.jpg')
    db.Insert_game(game_info[message.from_user.id])
    await bot.send_message(message.chat.id, "Игра создана")
    users = db.show_all_users(game_info[message.from_user.id][0])
    for i in users:
        place = db.show_info_place(game_info[message.from_user.id][1])

        y.download(f'/afisha/{str(game_info[message.from_user.id][0])+"_"+str(game_info[message.from_user.id][1])+"_"+str(game_info[message.from_user.id][2])}.jpg',
                   f'img/afisha/{str(game_info[message.from_user.id][0])+"_"+str(game_info[message.from_user.id][1])+"_"+str(game_info[message.from_user.id][2])}.jpg')
        date = re.split(";|,|\n|-|:|\.", game_info[message.from_user.id][2])
        date = date[2]+'-' + \
            date[1]+'-'+date[0]
        await bot.send_photo(i[0], photo=open(
            f'img/afisha/{str(game_info[message.from_user.id][0])+"_"+str(game_info[message.from_user.id][1])+"_"+str(game_info[message.from_user.id][2])}.jpg', 'rb'), caption=f"В вашем городе новая игра,\nУспей записаться!\nЗаведение: `{place[1]}`\nДата проведения: `{date}`\nВремя: `{game_info[message.from_user.id][3]}`\nЦена: `{place[2]}`\nПредоплата: `{place[5]}`\nКол-во мест: `{place[3]}`\nДля записи на игру нажми /afisha", parse_mode='Markdown')
    del game_info[message.from_user.id]
    await state.finish()

# _____EDIT_GAME______


@dp.callback_query_handler(text_contains='btn_edit_game')
async def callback_admin_btn_editgame(call: CallbackQuery):
    city_id = db.show_user(call.from_user.id)[3]
    result_game = db.show_game(city_id)
    if(len(result_game) == 0):
        # await bot.send_message(call.message.chat.id, 'Игр пока нет')
        await bot.edit_message_text('Игр пока нет', call.from_user.id, call.message.message_id, reply_markup=None)
    game_id = []
    await bot.delete_message(chat_id=call.message.chat.id,
                             message_id=call.message.message_id)
    msg = await bot.send_message(call.message.chat.id, "Загружаем игры")
    for i in result_game:

        game_id.append(i[0])
        times = i[3].strftime("%H:%M")
        date = i[2].strftime("%d.%m.%Y")
        keyboard = types.InlineKeyboardMarkup()
        btn_edit_game = types.InlineKeyboardButton(
            text="Настроить эту игру", callback_data=f"btn_edit_{i[0]}")
        keyboard.add(btn_edit_game)
        y.download(f'afisha/{str(city_id)+"_"+str(i[7])+"_"+str(i[2])}.jpg',
                   f'img/afisha/{str(city_id)+"_"+str(i[7])+"_"+str(i[2])}.jpg')
        await bot.send_photo(call.message.chat.id, photo=open(
            f'img/afisha/{str(city_id)+"_"+str(i[7])+"_"+str(i[2])}.jpg', 'rb'), caption=f"Заведение: {i[1]}\nДата проведения: {date}\nВремя: {times}\nЦена: `{i[5]}`\nОсталось мест: {i[4]-i[6]}\nУже идёт: {i[6]}", parse_mode='Markdown', reply_markup=keyboard)
    await bot.delete_message(call.message.chat.id, msg.message_id)


@dp.callback_query_handler(text_contains='btn_edit')
async def callback_admin_btn_this_game(call: CallbackQuery):
    game_id = call.data.split("_")[2]
    keyboard = types.InlineKeyboardMarkup()
    btn_edit_time = types.InlineKeyboardButton(
        text="Настроить время", callback_data=f"btn_ed_time_{game_id}")
    btn_edit_date = types.InlineKeyboardButton(
        text="Настроить дату", callback_data=f"btn_ed_date_{game_id}")
    btn_edit_place = types.InlineKeyboardButton(
        text="Настроить место", callback_data=f"btn_ed_place_{game_id}")
    btn_delete_game = types.InlineKeyboardButton(
        text="Удалить игру", callback_data=f"btn_deletegame_{game_id}")
    keyboard.add(btn_edit_time)
    keyboard.add(btn_edit_date)
    keyboard.add(btn_edit_place)
    keyboard.add(btn_delete_game)
    await bot.edit_message_caption(chat_id=call.message.chat.id,
                                   message_id=call.message.message_id, caption='',  reply_markup=keyboard)


@dp.callback_query_handler(text_contains="btn_ed_time")
async def callback_admin_btn_edit_time(call: CallbackQuery):
    game_id = call.data.split("_")[3]  # game_id
    game_info[call.from_user.id] = [game_id]

    await bot.delete_message(chat_id=call.message.chat.id,
                             message_id=call.message.message_id)
    await bot.send_message(call.message.chat.id, "Введите время")
    await NewGame_state.time.set()


@dp.message_handler(state=NewGame_state.time)
async def new_take_time(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text
        time = data['text']

    time = re.split(";|,|\n|-|:|\.", time)

    if (int(time[0]) < 0 or int(time[0]) >= 23) or int(time[1]) >= 59:

        await bot.send_message(message.chat.id, "Введите правильно время\nПример  `22:22`", parse_mode='Markdown')
        await NewGame_state.time.set()

    else:
        times = time[0]+':'+time[1]
        await state.finish()
        db.change_game(times, 'time', game_info[message.from_user.id][0])
        del game_info[message.from_user.id]
        await bot.send_message(message.chat.id, "Время изменено")
        await state.finish()


@dp.callback_query_handler(text_contains='btn_ed_date')
async def callback_admin_btn_edit_date(call: CallbackQuery):
    game_id = call.data.split("_")[3]
    game_info[call.from_user.id] = [game_id]
    await bot.delete_message(chat_id=call.message.chat.id,
                             message_id=call.message.message_id)
    await bot.send_message(
        call.message.chat.id, "Введите дату в формате `день-месяц-год`", parse_mode='Markdown')
    await NewGame_state.date.set()


@dp.message_handler(state=NewGame_state.date)
async def new_take_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text

    data = data['text']
    info = db.show_info_game(game_info[message.from_user.id][0])
    old_info = []
    old_info.append(info[0][0])
    old_info.append(info[0][1])
    old_info.append(info[0][2])

    try:
        data = re.split(";|,|\n|-|:|\.", data)
        date = datetime.date(int(data[2]), int(data[1]), int(data[0]))
    except:
        await bot.send_message(chat_id=message.from_user.id,
                               text="Введите правильно дату\nПример  `01-01-2022`", parse_mode='Markdown')
        await NewGame_state.date.set()
    if (int(data[0]) < 0 or int(data[0]) > 31) or (int(data[1]) > 12 or int(data[1]) <= 0) or date < datetime.date.today():
        await bot.send_message(chat_id=message.from_user.id,
                               text="Введите правильно дату, не раньше сегодняшней\nПример  `01-01-2022`", parse_mode='Markdown')
        await NewGame_state.date.set()

    else:
        dates = data[2]+'-' + \
            data[1]+'-'+data[0]

        y.download(f'/afisha/{old_info[0]}_{old_info[1]}_{old_info[2]}.jpg',
                   f"./img/afisha/{old_info[0]}_{old_info[1]}_{old_info[2]}.jpg")
        file_oldname = os.path.join(
            "./img/afisha/", f"{old_info[0]}_{old_info[1]}_{old_info[2]}.jpg")
        file_newname_newfile = os.path.join(
            "./img/afisha/", f"{old_info[0]}_{old_info[1]}_{dates}.jpg")
        os.rename(file_oldname, file_newname_newfile)
        y.remove(f'/afisha/{old_info[0]}_{old_info[1]}_{old_info[2]}.jpg')
        y.upload(f"./img/afisha/{old_info[0]}_{old_info[1]}_{dates}.jpg",
                 f'/afisha/{old_info[0]}_{old_info[1]}_{dates}.jpg')

        await state.finish()
        db.change_game(dates, 'date_of_games',
                       game_info[message.from_user.id][0])
        await bot.send_message(message.chat.id, "Дата изменена")
        del game_info[message.from_user.id]
        await state.finish()


@dp.callback_query_handler(text_contains='btn_ed_place')
async def callback_admin_btn_edit_place(call: CallbackQuery):
    game_id = call.data.split("_")[3]
    city_id = db.show_info_game(game_id)[0][0]
    await bot.delete_message(chat_id=call.message.chat.id,
                             message_id=call.message.message_id)
    keybd = (await btn_gameplace(city_id, game_id))[0]
    await bot.send_message(call.message.chat.id, "Выберите место", reply_markup=keybd)


@ dp.callback_query_handler(text_contains='btn_gplace')
async def callback_admin_editplace(call: CallbackQuery):
    game_id = call.data.split("_")[3]
    place_id = call.data.split("_")[2]
    info = db.show_info_game(game_id)
    old_info = []
    old_info.append(info[0][0])
    old_info.append(info[0][1])
    old_info.append(info[0][2])
    y.download(f'/afisha/{old_info[0]}_{old_info[1]}_{old_info[2]}.jpg',
               f"./img/afisha/{old_info[0]}_{old_info[1]}_{old_info[2]}.jpg")
    file_oldname = os.path.join(
        "./img/afisha/", f"{old_info[0]}_{old_info[1]}_{old_info[2]}.jpg")
    file_newname_newfile = os.path.join(
        "./img/afisha/", f"{old_info[0]}_{place_id}_{old_info[2]}.jpg")
    os.rename(file_oldname, file_newname_newfile)
    y.remove(f"/afisha/{old_info[0]}_{old_info[1]}_{old_info[2]}.jpg")
    y.upload(f"./img/afisha/{old_info[0]}_{place_id}_{old_info[2]}.jpg",
             f'/afisha/{old_info[0]}_{place_id}_{old_info[2]}.jpg')
    db.change_game(place_id, 'place_id', game_id)
    await bot.send_message(call.message.chat.id, "Место изменено")


@ dp.callback_query_handler(text_contains='btn_deletegame')
async def callback_admin_btn_delete_game(call: CallbackQuery):
    game_id = call.data.split("_")[2]
    info = db.show_info_game(game_id)
    if(len(info) == 0):
        await bot.send_message(call.message.chat.id, "Этой игры уже нет, удалена")
    else:
        old_info = []
        old_info.append(info[0][0])
        old_info.append(info[0][1])
        old_info.append(info[0][2])
        file_name = os.path.join(
            "./img/afisha/", f"{old_info[0]}_{old_info[1]}_{old_info[2]}.jpg")
        os.remove(file_name)
        y.remove(f'/afisha/{old_info[0]}_{old_info[1]}_{old_info[2]}.jpg')
        db.del_prereg(game_id)
        db.del_game(game_id)
        await bot.delete_message(call.message.chat.id, call.message.message_id)
        await bot.send_message(call.message.chat.id, "Игра удалена")

# ______PAY_____


@ dp.callback_query_handler(text_contains='btn_pay_game')
async def call_btn_pay_game(call: CallbackQuery):
    city_id = db.show_user(call.from_user.id)[3]
    games = db.show_game(city_id)
    keyboard = types.InlineKeyboardMarkup()
    btns_games = {}
    games_date = {}
    games_id = []
    if(len(games) == 0):
        bot.send_message(call.message.chat.id, "Игр пока нет")
    for i in (games):
        games_id.append(i[0])
        games_date[i[0]] = i[2].strftime('%d.%m.%Y')

    for i in games_id:
        btns_games['btn_%s' % i] = types.InlineKeyboardButton(
            text=f'{games_date[i]}', callback_data=f'btn_pgame_{i}')
        keyboard.add(btns_games['btn_%s' % i])
    await bot.edit_message_text("Выберете игру", call.from_user.id, call.message.message_id,
                                reply_markup=keyboard)


@ dp.callback_query_handler(text_contains='btn_pgame')
async def call_btn_btn_pgame(call: CallbackQuery):
    game_id = call.data.split('_')[2]
    users = db.show_who_goes(game_id, 0)
    if(len(users) == 0):
        await bot.edit_message_text('Больше никто не записался!', call.from_user.id, call.message.message_id, reply_markup=None)
    else:
        user = (await btn_users(users, game_id, "btn_gusers"))[0]
        await bot.edit_message_text("Выберете человека который оплатил", call.from_user.id, call.message.message_id,
                                    reply_markup=user)


@ dp.callback_query_handler(text_contains='btn_gusers')
async def call_btn_btn_gusers(call: CallbackQuery):
    user_id = call.data.split('_')[2]
    game_id = call.data.split('_')[3]
    db.update_prepayment(user_id, game_id)
    users = db.show_who_goes(game_id, 0)
    if(len(users) == 0):
        await bot.edit_message_text('Больше никто не записался!', call.from_user.id, call.message.message_id, reply_markup=None)
    else:
        user = (await btn_users(users, game_id, "btn_gusers"))[0]
        await bot.edit_message_text("Выберете человека который оплатил", call.from_user.id, call.message.message_id,
                                    reply_markup=user)
    await bot.send_message(user_id, "Оплата подтверждена")
# _____ADMIN/GAME_____
# _____ADMIN________

# _____PROFILE______


@ dp.message_handler(commands=['profile'])
async def show_profile(message: types.Message):
    info = db.show_user(message.from_user.id)
    if info == None:
        logger.info(f" {message.from_user.id} пытается посмотреть профиль без регистрации")
        await bot.send_message(message.chat.id, "Вас не в нашей базе пользователей, чтобы зарегитрироваться введите: /start")
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        btn_edit_profile = types.KeyboardButton('Редактировать профиль✏️')
        btn_show_profile = types.KeyboardButton('Показать профиль🖼')
        btn_back = types.KeyboardButton('Выйти из меню 🔚')
        markup.add(btn_show_profile, btn_edit_profile, btn_back)
        await bot.send_message(message.chat.id, 'Что вы хотите сделать с профилем?', reply_markup=markup)


@ dp.message_handler(content_types=['text'])
async def edit_profile(message: types.Message):
    info = db.show_user(message.from_user.id)
    if message.text == 'Показать профиль🖼':
        if info == None:
            await bot.send_message(message.chat.id, "Вас не в нашей базе пользователей, чтобы зарегитрироваться введите: /start")
        else:
            user_id = message.from_user.id
            logger.info(f"{user_id} смотрит профиль")
            info = db.show_user(user_id)
            if info[3] == 0:
                await bot.send_message(message.chat.id, "Для начала выберите город в настройках профиля")
            else:
                msg = await bot.send_message(message.chat.id, "Подгружаем ваш профиль...")
                result = db.search_city(info[3])
                y.download(f'/avatar/{user_id}.jpg',
                           f'./img/avatar/{user_id}.jpg')
                await bot.delete_message(message.chat.id, msg.message_id)
                await bot.send_photo(message.chat.id, photo=open(
                    f'./img/avatar/{user_id}.jpg', 'rb'), caption=f"*Профиль*\n- _Имя_: `{info[1]}`\n- _Город_: `{result[0]}`\n- _Телефон_: `{info[2]}`\n- _Кол-во игр_: `{info[5]}`", parse_mode='Markdown')
                os.remove(f'./img/avatar/{user_id}.jpg')
    if message.text == 'Редактировать профиль✏️':
        if info == None:
            await bot.send_message(message.chat.id, "Вас не в нашей базе пользователей, чтобы зарегитрироваться введите: /start")
        else:
            logger.info(
                f"{message.from_user.id} хочет отредактировать профиль")

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True, row_width=2)
            btn_edit_name = types.KeyboardButton('Изменить имя(ник) ✏️')
            btn_edit_city = types.KeyboardButton('Изменить город 🏙')
            btn_edit_avatar = types.KeyboardButton('Изменить фото профиля👨')
            btn_back = types.KeyboardButton('Выйти из меню 🔚')
            markup.add(btn_edit_name, btn_edit_city, btn_edit_avatar, btn_back)
            await bot.send_message(
                message.chat.id, "Давайте изменим ваш профиль 😉", reply_markup=markup)
    if message.text == 'Выйти из меню 🔚':
        logger.info(f"{message.from_user.id} вышел из меню профиля")
        markup = types.ReplyKeyboardRemove()
        await bot.send_message(
            message.chat.id, "Надеюсь вы точно настроили профиль 😉", reply_markup=markup)

    if message.text == 'Изменить имя(ник) ✏️':
        if info == None:
            await bot.send_message(message.chat.id, "Вас не в нашей базе пользователей, чтобы зарегитрироваться введите: /start")
        else:

            markup = types.ReplyKeyboardRemove()
            await bot.send_message(message.chat.id, "Введите новое *имя(ник)*",
                                   parse_mode='markdown', reply_markup=markup)
            await NewUser_state.name.set()

    if message.text == 'Изменить фото профиля👨':
        if info == None:
            await bot.send_message(message.chat.id, "Вас не в нашей базе пользователей, чтобы зарегитрироваться введите: /start")
        else:
            user_id = message.from_user.id
            markup = types.ReplyKeyboardRemove()
            await bot.send_message(
                message.chat.id, "Отправьте новое фото профиля", reply_markup=markup)
            await NewUser_state.photo.set()

    if message.text == 'Изменить город 🏙':
        if info == None:
            await bot.send_message(message.chat.id, "Вас не в нашей базе пользователей, чтобы зарегитрироваться введите: /start")
        else:

            await bot.send_message(message.chat.id, "Хорошо подгружаем города",
                                   parse_mode='markdown', reply_markup=types.ReplyKeyboardRemove())
            time.sleep(1)
            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id+1)
            keybd = (await kb_city.keyboard_city('btn_changecity'))[0]
            await bot.send_message(message.chat.id, "Выберете новый *город*",
                                   parse_mode='markdown', reply_markup=keybd)


@dp.message_handler(state=NewUser_state.name)
async def take_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text
    logger.info(f"{message.from_user.id} меняет ник на {data['text']}")
    db.Change_nickName(message.from_user.id, data['text'])
    await state.finish()
    await bot.send_message(message.chat.id, "Имя пользователя изменено")


@dp.message_handler(state=NewUser_state.photo, content_types=['photo'])
async def take_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['photo'] = message.photo[-1]

    await data['photo'].download(f'./img/avatar/{message.from_user.id}.jpg')
    if y.exists(f'/avatar/{message.from_user.id}.jpg'):
        y.remove(f'/avatar/{message.from_user.id}.jpg')
    y.upload(f'./img/avatar/{message.from_user.id}.jpg',
             f'/avatar/{message.from_user.id}.jpg')
    os.remove(f'./img/avatar/{message.from_user.id}.jpg')
    logger.info(f"{message.from_user.id} поменял фото")
    await bot.send_message(message.chat.id, "Фотография изменена")
    await state.finish()


@dp.callback_query_handler(text_contains='btn_changecity')
async def change_citys(call: CallbackQuery):
    users_id = call.from_user.id
    city_id = call.data.split("_")[2]
    logger.info(f"{users_id} меняет город на city_id:{city_id}")
    await bot.edit_message_text(chat_id=call.message.chat.id,
                                message_id=call.message.message_id, text=f'Город изменен')
    role = db.show_user(users_id)[4]
    if role < 2:
        db.Change_city(city_id, users_id, 0)
    else:
        db.Change_city(city_id, users_id, 2)

# _____PROFILE_____


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
