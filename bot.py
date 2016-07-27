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

API_HOST = "http://alexkorotkov.ru:8080"

NT_URL = API_HOST + "/exist/rest/db/nz/nz.xml"
BOOKS_URL = API_HOST + "/exist/rest/db/nz/books.xq"
STATS_URL = API_HOST + "/exist/rest/db/nz/stats.xq"

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

Команды:
/books - список доступных книг
/stats - статистика по количеству стихов в главах в книгах
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
        resultdict["book"] = resultdict["book"].lower()
        return """//book[short-title="{book}"]/chapter[{chapter}]/verse[position()={verse_from}{to_part}]""".format(
            to_part=" to {}".format(resultdict['verse_to']) if resultdict['verse_to'] is not None else "",
            **resultdict)


def get_url(myselector):
    return NT_URL + '?_query=' + myselector


def get_message(query):
    myselector = build_selector(query)
    url = NT_URL + '?_query=' + myselector
    result = etree.parse(url)
    verses = result.xpath("//verse/text()")
    if verses:
        message = "\n".join(verses)
        message += "\n_" + " ".join(query.split()).title() + "_"
        return message


def inlinequery(bot, update):
    query = update.inline_query.query.lower()
    if re.match(INDEX, query):
        message = get_message(query)
        if message:
            results = list()
            results.append(
                InlineQueryResultArticle(
                    id=uuid.uuid4(),
                    title=query,
                    input_message_content=InputTextMessageContent(
                    message, parse_mode=ParseMode.MARKDOWN),
                    parse_mode=ParseMode.MARKDOWN)
            )
            bot.answerInlineQuery(update.inline_query.id, results=results)


def books(bot, update):
    res = etree.parse(BOOKS_URL)
    message = "*НОВЫЙ ЗАВЕТ*\n\n"
    message += "\n".join(
        map(lambda book: "{}. - {}".format(book.get("abbr").title(), book.get("title")), res.xpath("/books/book")))
    bot.sendMessage(update.message.chat_id, text=message, parse_mode=ParseMode.MARKDOWN)


def stats(bot, update, args):
    if args:
        index = args[0].strip().lower()
        url = STATS_URL + "?book=" + args[0].strip().lower()
        res = etree.parse(url)
        message = "*СТАТИСТИКА*\n\n"
        message += "\n".join(
            map(
                lambda chapter: "{}. {} стихов {}".format(
                    index.title(),
                    chapter.get("number"),
                    chapter.get("verses")
                ), res.xpath("/chapters/chapter")))
        bot.sendMessage(update.message.chat_id, text=message, parse_mode=ParseMode.MARKDOWN)
    else:
        message = """
Через пробел определите идентификатор книги, чтобы получить статистику.\n
Например, _/stats Мф_
        """
        bot.sendMessage(update.message.chat_id, text=message, parse_mode=ParseMode.MARKDOWN)

def show(bot, update):
    query = update.message.text.lower()
    if re.match(INDEX, query):
        message = get_message(query)
        if message:
            bot.sendMessage(update.message.chat_id, text=message, parse_mode=ParseMode.MARKDOWN)
        else:
            bot.sendMessage(update.message.chat_id, text="По вашему запросу ничего не найдено.")
    else:
        bot.sendMessage(update.message.chat_id, text="Проверьте правильность сокращений!")


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def main(token):
    updater = Updater(token)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("books", books))
    dp.add_handler(CommandHandler("stats", stats, pass_args=True))

    dp.add_handler(MessageHandler([Filters.text], show))
    dp.add_handler(InlineQueryHandler(inlinequery))

    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main(sys.argv[1])