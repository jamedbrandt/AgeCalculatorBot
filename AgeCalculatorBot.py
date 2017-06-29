#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import yaml
import traceback
import Calculate
from telegram import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler


def custom_str_constructor(loader, node):
    return loader.construct_scalar(node).encode('utf-8')


def log():
    form = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    if get_yml('./config.yml')['agecalculator']['debug']:
        logging.basicConfig(format=form, level=logging.DEBUG)
    else:
        logging.basicConfig(format=form, level=logging.INFO, filename='error.log')
    logger = logging.getLogger(__name__)


def get_yml(file):
    result = {}
    with open(os.path.join(os.path.dirname(__file__), file), 'rb') as ymlfile:
        values = yaml.load(ymlfile)
        for k, v in values.items():
            result[k.decode('utf-8')] = dict_byte_to_str(v)
    return result


def dict_byte_to_str(v):
    result = {}
    if hasattr(v, 'items'):
        for key, value in v.items():
            if isinstance(value, bytes):
                value = value.decode('utf-8')
                value = str.replace(value, "\\n", "\n")
            result[key.decode('utf-8')] = value
    else:
        result = v.decode('utf-8')
        result = str.replace(result, "\\n", "\n")
    return result


def get_year_kb(c, r, year, arg, chat_data):
    row = []
    std_year = year
    for i in range(r):
        column = []
        for j in range(c):
            column.append(InlineKeyboardButton(str(year), callback_data=arg + ' ' + str(year)))
            year = 1 + year
        row.append(column)
    row.append([InlineKeyboardButton("⬅️ " + strings[chat_data["lang"]]["early"],
                                     callback_data=arg[0:1] + "prev" + ' ' + str(std_year)),
                InlineKeyboardButton(strings[chat_data["lang"]]["late"] + " ➡️",
                                     callback_data=arg[0:1] + "next" + ' ' + str(std_year))])
    return InlineKeyboardMarkup(row)


def get_number_kb(c, r, callback, limit=99, name_list=(), start_one=True):
    row = []
    for i in range(r):
        column = []
        for j in range(c):
            pos = str(i * c + (j + int(start_one)))
            full_name = "0" + pos if int(pos) < 10 else pos
            name = full_name if not name_list else name_list[int(pos) - 1]
            if int(pos) < limit + 1:
                column.append(InlineKeyboardButton(name, callback_data=callback + ' ' + full_name))
        row.append(column)
    return InlineKeyboardMarkup(row)


def get_language(user):
    if user.language_code:
        language_code = user.language_code[:2]
        return language_code if language_code in strings else 'en'
    return 'en'


def start(bot, update, chat_data):
    user = update.callback_query.from_user if update.callback_query else update.message.from_user
    if not "lang" in chat_data:
        chat_data["lang"] = get_language(user)
    name = user.first_name if update.callback_query else user.first_name
    reply = update.callback_query.message.edit_text if update.callback_query else update.message.reply_text
    text = strings[chat_data["lang"]]["ok"] + " 😁" if "confirmed" in chat_data else strings[chat_data["lang"]][
        "question"]
    reply(strings[chat_data["lang"]]["greeting"] + " " + name
          + " ✌🏻\n" + text, reply_markup=get_lang_keyboard(chat_data))


def send(bot, update, chat_data):
    try:
        keyboard = get_number_kb(8, 4, "sday", limit=31)
        delete_date(chat_data, 's')
        delete_date(chat_data, 'g')
        chat_data.pop("bhour", None)
        chat_data.pop("bmin", None)
        update.message.reply_text(get_text(chat_data) + get_action("sday", chat_data),
                                  reply_markup=keyboard,
                                  parse_mode=ParseMode.MARKDOWN)
    except KeyError:
        user = update.callback_query.from_user if update.callback_query else update.message.from_user
        if not "lang" in chat_data:
            chat_data["lang"] = get_language(user)
        send(bot, update, chat_data)


def navigate_year(update, chat_data, arg):
    new_year = int(update.callback_query.data.split(" ")[1])
    new_year = new_year + 12 if arg == "gnext" or arg == "snext" else new_year - 12
    update.callback_query.message.edit_text(get_text(chat_data) + get_action(arg[0:1] + "year", chat_data),
                                            reply_markup=get_year_kb(4, 3, new_year, arg[0:1] + "year", chat_data),
                                            parse_mode=ParseMode.MARKDOWN)


def get_text(chat_data, time=False):
    result = strings[chat_data["lang"]]["birthday"] + ": *"
    result = result + str(chat_data["sday"]) + "." if "sday" in chat_data else result + "xx."
    result = result + str(chat_data["smonth"]) + "." if "smonth" in chat_data else result + "xx."
    result = result + str(chat_data["syear"]) + "*" if "syear" in chat_data else result + "xxxx*"
    if time or "bhour" in chat_data or "bmin" in chat_data:
        result = result + " *xx:xx*" if not "bhour" in chat_data else result
        result = result + " *" + str(chat_data["bhour"]) + ":xx*" if "bhour" in chat_data else result
        result = result[:-4] + ":" + str(chat_data["bmin"]) + "*" if "bmin" in chat_data else result
    result = result + "\n" + strings[chat_data["lang"]]["todays_date"] + ": *"
    result = result + str(chat_data["gday"]) + "." if "gday" in chat_data else result + "xx."
    result = result + str(chat_data["gmonth"]) + "." if "gmonth" in chat_data else result + "xx."
    result = result + str(chat_data["gyear"]) + "*" if "gyear" in chat_data else result + "xxxx*"
    return result


def get_lang_keyboard(chat_data):
    if "confirmed" in chat_data:
        chat_data.pop("confirmed", None)
        return None
    else:
        if chat_data["lang"] == "de":
            emoji = "🇬🇧"
            callback = "en"
        else:
            emoji = "🇩🇪"
            callback = "de"
        keyboard = [[InlineKeyboardButton("✔️ " + strings[chat_data["lang"]]["ja"], callback_data="yes")],
                    [InlineKeyboardButton(
                        strings[chat_data["lang"]]["nein"] + ", " + strings[chat_data["lang"]][
                            "other_lang"] + " " + emoji,
                        callback_data=callback)]]
        return InlineKeyboardMarkup(keyboard)


def get_result_keyboard(selected, chat_data):
    current = [" ", " ", " ", " "]
    current[selected] = " ☑️"
    keyboard = [[InlineKeyboardButton("⏳ " + strings[chat_data["lang"]]["age"] + current[0], callback_data="calc"),
                 InlineKeyboardButton("📊 " + strings[chat_data["lang"]]["total"] + current[1], callback_data="total")],
                [InlineKeyboardButton("📆 " + strings[chat_data["lang"]]["next"] + current[2],
                                      callback_data="next_birthdays"),
                 InlineKeyboardButton("🎊 " + strings[chat_data["lang"]]["events"] + current[3],
                                      callback_data="special_events")],
                [InlineKeyboardButton("👨‍🏫 " + strings[chat_data["lang"]]["contribute"],
                                      url='https://github.com/Andre0512/AgeCalculatorBot/'),
                 InlineKeyboardButton("🌟 " + strings[chat_data["lang"]]["rate"],
                                      url='https://telegram.me/storebot?start=AgeCalculatorBot'),
                 InlineKeyboardButton("➕ " + strings[chat_data["lang"]]["new"], callback_data="new")]]
    return InlineKeyboardMarkup(keyboard) if not 'new' in chat_data else None


def get_calc_keyboard(chat_data):
    birth_time = "➕ " + strings[chat_data["lang"]]["add_time"] if not "bhour" in chat_data else "✏️ " + strings[
        chat_data["lang"]]["correct_time"]
    keyboard = [[InlineKeyboardButton("🎛 " + strings[chat_data["lang"]]["calc"], callback_data="calc")],
                [InlineKeyboardButton("✏️ " + strings[chat_data["lang"]]["correct_bday"],
                                      callback_data="correct_start")],
                [InlineKeyboardButton("✏️ " + strings[chat_data["lang"]]["correct_today"],
                                      callback_data="correct_goal")],
                [InlineKeyboardButton(birth_time, callback_data="add_time")]]
    return InlineKeyboardMarkup(keyboard)


def get_action(arg, chat_data):
    if arg[1:] == "day":
        period = strings[chat_data["lang"]]["t_day"]
    elif arg[1:] == "month":
        period = strings[chat_data["lang"]]["t_month"]
    else:
        period = strings[chat_data["lang"]]["t_year"]
    if arg[0:1] == "s":
        day = strings[chat_data["lang"]]["t_birthday"]
    else:
        day = strings[chat_data["lang"]]["t_todays_date"]
    return "\n\n💡 " + strings[chat_data["lang"]]["action_start"] + " " + period + " " + day + ":"


def delete_date(chat_data, arg):
    chat_data.pop(arg + "year", None)
    chat_data.pop(arg + "month", None)
    chat_data.pop(arg + "day", None)

def try_button(bot, update, chat_data):
    try:
        button(bot, update, chat_data)
    except KeyError:
        chat_data.pop("new", None)
        if not "lang" in chat_data:
            chat_data["lang"] = get_language(update.callback_query.from_user)
        send(bot, update.callback_query, chat_data)


def log_user(user, chat_data):
    language_code = user.language_code if user.language_code else ''
    name = user.first_name + " " + user.last_name if user.last_name else user.first_name
    log = ("\n" + name + " " + str(user.id) + " " + language_code +
           " (" + str(chat_data['sday']) + "." + str(chat_data['smonth']) + "." + str(chat_data['syear']) + ")")
    file = open("age_log.txt", "a")
    file.write(log)
    file.close()


def button(bot, update, chat_data):
    update.callback_query.answer()
    arg_one = update.callback_query.data.split(" ")[0] if not 'new' in chat_data  else chat_data['cur']
    if arg_one == "sday" or arg_one == "gday":
        chat_data[arg_one] = update.callback_query.data.split(" ")[1]
        month = strings[chat_data["lang"]]["month_list"].split(", ")
        update.callback_query.message.edit_text(get_text(chat_data) + get_action(arg_one[0:1] + "month", chat_data),
                                                reply_markup=get_number_kb(3, 4, arg_one[0:1] + "month",
                                                                           name_list=month),
                                                parse_mode=ParseMode.MARKDOWN)
    elif arg_one == "smonth" or arg_one == "gmonth":
        chat_data[arg_one] = update.callback_query.data.split(" ")[1]
        update.callback_query.message.edit_text(get_text(chat_data) + get_action(arg_one[0:1] + "year", chat_data),
                                                reply_markup=get_year_kb(4, 3, 1980, arg_one[0:1] + "year",
                                                                         chat_data),
                                                parse_mode=ParseMode.MARKDOWN)
    elif arg_one == "syear" or arg_one == "gyear" or arg_one == "bmin":
        chat_data[arg_one] = update.callback_query.data.split(" ")[1]
        if not "gday" in chat_data and not "gmonth" in chat_data and not "gyear" in chat_data:
            Calculate.set_today(chat_data)
        update.callback_query.message.edit_text(
            get_text(chat_data) + "\n\n💡 " + strings[chat_data["lang"]]["action"] + ":",
            reply_markup=get_calc_keyboard(chat_data), parse_mode=ParseMode.MARKDOWN)
    elif arg_one == "snext" or arg_one == "sprev" or arg_one == "gnext" or arg_one == "gprev":
        navigate_year(update, chat_data, arg_one)
    elif arg_one == "correct_start" or arg_one == "correct_goal":
        delete_date(chat_data, arg_one.split("correct_")[1][0:1])
        keyboard = get_number_kb(8, 4, arg_one.split("correct_")[1][0:1] + "day", limit=31)
        update.callback_query.message.edit_text(
            get_text(chat_data) + get_action(arg_one.split("correct_")[1][0:1] + "day", chat_data),
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN)
    elif arg_one == "calc":
        chat_data['cur'] = arg_one
        log_user(update.callback_query.from_user, chat_data)
        try:
            update.callback_query.message.edit_text(get_text(chat_data) + "\n\n" + Calculate.calculate(chat_data),
                                                    parse_mode=ParseMode.MARKDOWN,
                                                    reply_markup=get_result_keyboard(0, chat_data))
        except ValueError:
            update.callback_query.message.edit_text(
                get_text(chat_data) + "\n\n‼️ " + strings[chat_data["lang"]]["error"] + " ‼️" + "\n💡 " +
                strings[chat_data["lang"]]["try_again"] + ":",
                reply_markup=get_calc_keyboard(chat_data), parse_mode=ParseMode.MARKDOWN)
    elif arg_one == "total":
        chat_data['cur'] = arg_one
        text = strings[chat_data["lang"]]["total"] + ":\n" + Calculate.total_time(chat_data)
        update.callback_query.message.edit_text(get_text(chat_data) + "\n\n" + text, parse_mode=ParseMode.MARKDOWN,
                                                reply_markup=get_result_keyboard(1, chat_data))
    elif arg_one == "next_birthdays":
        chat_data['cur'] = arg_one
        text = Calculate.weekdays(chat_data)
        update.callback_query.message.edit_text(get_text(chat_data) + "\n\n" + text, parse_mode=ParseMode.MARKDOWN,
                                                reply_markup=get_result_keyboard(2, chat_data))
    elif arg_one == "yes":
        chat_data["confirmed"] = "yes"
        start(bot, update, chat_data)
        send(bot, update.callback_query, chat_data)
    elif arg_one == "new":
        chat_data['new'] = True
        button(bot, update, chat_data)
        chat_data.pop("new", None)
        chat_data.pop("cur", None)
        send(bot, update.callback_query, chat_data)
    elif arg_one == "add_time":
        update.callback_query.message.edit_text(
            get_text(chat_data, time=True) + "\n\n💡 " + strings[chat_data["lang"]]["action_start"] + " " +
            strings[chat_data["lang"]]["b_hour"] + ":",
            reply_markup=get_number_kb(6, 4, 'bhour', limit=24, start_one=False),
            parse_mode=ParseMode.MARKDOWN)
    elif arg_one == "bhour":
        chat_data[arg_one] = update.callback_query.data.split(" ")[1]
        update.callback_query.message.edit_text(
            get_text(chat_data) + "\n\n💡 " + strings[chat_data["lang"]]["action_start"] + " " +
            strings[chat_data["lang"]]["b_min"] + ":",
            reply_markup=get_number_kb(8, 8, 'bmin', limit=59, start_one=False), parse_mode=ParseMode.MARKDOWN)
    elif arg_one == "special_events":
        chat_data['cur'] = arg_one
        text = Calculate.calculate_special_events(chat_data)
        update.callback_query.message.edit_text(get_text(chat_data) + "\n" + text, parse_mode=ParseMode.MARKDOWN,
                                                reply_markup=get_result_keyboard(3, chat_data))
    elif arg_one in strings:
        chat_data["confirmed"] = "yes"
        chat_data["lang"] = arg_one
        start(bot, update, chat_data)
        send(bot, update.callback_query, chat_data)


def main():
    yaml.add_constructor(u'tag:yaml.org,2002:str', custom_str_constructor)
    log()

    global strings
    strings = get_yml("./strings.yml")
    Calculate.set_strings(strings)

    updater = Updater(get_yml('./config.yml')['agecalculator']['bottoken'])

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start, pass_chat_data=True))
    dp.add_handler(MessageHandler(Filters.text, send, pass_chat_data=True))
    dp.add_handler(CallbackQueryHandler(try_button, pass_chat_data=True))

    updater.start_polling()
    updater.idle()


def err():
    bot = Bot(get_yml('./config.yml')['agecalculator']['bottoken'])
    try:
        bot.sendMessage(chat_id=get_yml('./config.yml')['agecalculator']['errorid'],
                        text='Crawler fehlgeschalgen: ```' + traceback.format_exc() + '```',
                        disable_notification=True, parse_mode=ParseMode.MARKDOWN)
    except:
        bot.sendMessage(chat_id=get_yml('./config.yml')['agecalculator']['errorid'],
                        text='Crawler fehlgeschalgen: \n' + traceback.format_exc(),
                        disable_notification=True)


if __name__ == '__main__':
    while True:
        try:
            main()
            err()
        except:
            err()
