FROM python:3.6

RUN pip install lxml python-telegram-bot --upgrade

WORKDIR /newtestamentbot
COPY newtestamentbot /newtestamentbot

ENTRYPOINT ["python", "/newtestamentbot/bot.py", "249463893:AAHYVBc7uBHq7H9CyJ12CqWo5ao33z1mCu8"]
