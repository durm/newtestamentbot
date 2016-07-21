#!/usr/bin/env python
import sys
from telegram.ext import Updater, CommandHandler, MessageHandler, InlineQueryHandler, Filters
from telegram import InlineQueryResultArticle, InputTextMessageContent, ParseMode
import logging
from lxml import etree
import re
import uuid


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

NT_URL = "http://127.0.0.1:8080/exist/rest/db/nz/nz.xml"

PATTERN_SINGLE = "<Книга>. <Глава>:<Стих>"
PATTERN_RANGE = "<Книга>. <Глава>:<Стих>-<Стих>"

INDEX = re.compile("^(?P<book>\w+)\.\s(?P<chapter>\d+):(?P<verse_from>\d+)(\-(?P<verse_to>\d+))?")
HELP = """
Синтаксис запросов:
*{}* для конкретного стиха
или
*{}* для диапазона стихов
(максимальное количество стихов в диапазоне равно 10)
Например: _Мф. 5:3-12_
""".format(PATTERN_SINGLE, PATTERN_RANGE)

def start(bot, update):
    WELCOME = """
Здравствуй! Это навигатор по Библии!\n
Вы можете получить выдержки из Нового Завета по запросам.\n
{}
    """.format(HELP)
    bot.sendMessage(update.message.chat_id, text=WELCOME, parse_mode=ParseMode.MARKDOWN)


def help(bot, update):
    bot.sendMessage(update.message.chat_id, text=HELP, parse_mode=ParseMode.MARKDOWN)


def build_selector(query):
    result = re.search(INDEX, query)
    if result:
        resultdict = result.groupdict()
        return """//book[short-title="{book}"]/chapter[{chapter}]/verse[position()={verse_from}{to_part}]""".format(
            to_part=" to {}".format(resultdict['verse_to']) if resultdict['verse_to'] is not None else "",
            **resultdict)


def get_url(myselector):
    return NT_URL + '?_query=' + myselector


def get_text_by_selector(myselector):
    url = NT_URL + '?_query=' + myselector
    result = etree.parse(url)
    message = "\n".join(result.xpath("//verse/text()"))
    return message[0:4000] + "..." if len(message) > 4000 else message


def inlinequery(bot, update):
    query = update.inline_query.query
    if re.match(INDEX, query):
        myselector = build_selector(query)
        message = get_text_by_selector(myselector)
        message += "\n_" + " ".join(query.split()) + "_"
        results = list()
        results.append(
            InlineQueryResultArticle(id=uuid.uuid4(),
                                     title=query,
                                     input_message_content=InputTextMessageContent(
                                         message, parse_mode=ParseMode.MARKDOWN),
                                     parse_mode=ParseMode.MARKDOWN)
        )
        bot.answerInlineQuery(update.inline_query.id, results=results)


def show(bot, update):
    query = update.message.text
    myselector = build_selector(query)
    if myselector:
        message = get_text_by_selector(myselector)
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

    #dp.add_handler(MessageHandler([Filters.text], show))
    dp.add_handler(InlineQueryHandler(inlinequery))

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