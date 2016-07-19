#!/usr/bin/env python
import sys
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.keyboardbutton import KeyboardButton
from telegram import InlineKeyboardButton, CallbackQuery, InlineKeyboardMarkup
from telegram.replykeyboardmarkup import ReplyKeyboardMarkup
import logging
from lxml import etree
import re

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


NT_URL = "http://127.0.0.1:8080/exist/rest/db/nz/nz.xml"


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    bot.sendMessage(update.message.chat_id, text='Здравствуй! Это навигатор по Библии!')


def help(bot, update):
    bot.sendMessage(update.message.chat_id, text='Help!')


def build_selector(query):
    expr = re.compile("^\s*(?P<book>\w+)\.\s*(?P<chapter>\d+)\s*:\s*(?P<verse_from>\d+)\s*(\-\s*(?P<verse_to>\d+)\s*)?")
    result = re.search(expr, query)
    if result:
        resultdict = result.groupdict()
        return """//book[short-title="{book}"]/chapter[{chapter}]/verse[position()={verse_from}{to_part}]""".format(
            to_part=" to {}".format(resultdict['verse_to']) if resultdict['verse_to'] is not None else "",
            **resultdict)


def get_url(myselector):
    return NT_URL + '?_query=' + myselector


def show(bot, update):
    query = update.message.text
    myselector = build_selector(query)
    if myselector:
        url = NT_URL + '?_query=' + myselector
        result = etree.parse(url)
        message = "\n".join(result.xpath("//verse/text()"))
        message = message[0:4000] + "..." if len(message) > 4000 else message
        if message:
            bot.sendMessage(update.message.chat_id, text=message)
        else:
            bot.sendMessage(update.message.chat_id, text="По вашему запросу ничего не найдено.")
    else:
        bot.sendMessage(update.message.chat_id, text="Проверьте правильность сокращений!")

def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))

def main(token):
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler([Filters.text], show))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main(sys.argv[1])