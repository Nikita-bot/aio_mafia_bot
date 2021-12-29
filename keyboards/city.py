
from aiogram import types
import data_base
db = data_base.Data()


async def keyboard_city(parametr):
    citys = db.show_city()
    citys_name = {}
    citys_id = []
    for i in citys:
        citys_id.append(i[0])
        citys_name[i[0]] = i[1]
    btn_citys = {}
    btn_reg_keyboard = types.InlineKeyboardMarkup(row_width=1)
    for i in citys_id:
        btn_citys[f'{parametr}_%s' % i] = types.InlineKeyboardButton(
            text=f'{citys_name[i]}', callback_data=f'{parametr}_{i}')
        btn_reg_keyboard.add(btn_citys[f'{parametr}_%s' % i])
    # btn_reg
    # btn_change_city
    return [btn_reg_keyboard, citys_id]
