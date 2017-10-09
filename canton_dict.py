#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Simple Bot to reply to Telegram messages
# This program is dedicated to the public domain under the CC0 license.
"""
This Bot uses the Updater class to handle the bot.

First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Basic inline bot example. Applies different text transformations.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
import ast
from uuid import uuid4

import re
from urllib.request import urlopen
from telegram import InlineQueryResultArticle, InlineQueryResultAudio, ParseMode, InputTextMessageContent
from telegram.ext import Updater, InlineQueryHandler, CommandHandler
import logging
from telegram.ext.dispatcher import run_async
import pymysql

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
re_square_brackets = r"<[^<]*?>"
re_nothing = r''
re_cangjie = r'<th>倉頡碼</th>\s*<td>.*?&nbsp;</td>'
re_brief_explain = r'略說:</span>\s*.*?<br />'
re_audios = r'sound/.*?Mp3'
re_examples = r'<div style="overflow-y: auto; overflow-x: hidden; width: 100%; height: 40px">\s*.*?</div>'
re_can_note = '<td class="char_can_note">\s*.*?</td>'
re_eng_pos = r'<td class="char_eng_pos">*.*?</td>'
re_eng_meaning = r'<td class="char_eng_meaning">*.*?</td>'
re_can_phon = '<td class="char_can_phon" colspan="3" rowspan="2">\s*.*?<\/td>'
connection = pymysql.connect(host='',
                             user='',
                             password='',
                             connect_timeout=1209600,
                             db='',
                             use_unicode=True,
                             charset="utf8")


class CantonDict:
    def __init__str(self, word):
        try:
            word = word.encode('utf8')
            url = 'http://humanum.arts.cuhk.edu.hk/Lexis/lexi-mf/search.php?word={0}'.format(
                str(word)[2:-1].replace('\\x', '%').upper())
            contents = str(urlopen(url).read().decode('utf-8'))
            contents_no_newline = contents.replace("\r", "").replace("\n", "")
            # if no this word
            if "字未收錄於本資料庫" in contents:
                print("This word is not recorded.")
                return
            # 倉頡碼
            cangjie_pattern = re.findall(re_cangjie, contents_no_newline)[0].replace(" ", "")[16:-11]
            # 略說
            brief_explain = re.findall(re_brief_explain, contents_no_newline)
            brief_explains = list()
            for explanation in brief_explain:
                while True:
                    b_new = re.sub(re_square_brackets, re_nothing, explanation)
                    if b_new == explanation:
                        brief_explains.append(explanation.encode().strip())
                        break
                    explanation = b_new
            # 粵音
            pronunciation = re.findall(re_audios, contents_no_newline)
            # 詞例
            word_example = re.findall(re_examples, contents_no_newline)
            char_can_notes = re.findall(re_can_note, contents_no_newline)
            notes = list()
            examples = list()
            for example in word_example:
                while True:
                    e_new = re.sub(re_square_brackets, re_nothing, example)
                    if e_new == example:
                        examples.append(example.strip())
                        break
                    example = e_new

            for note in char_can_notes:
                while True:
                    e_new = re.sub(re_square_brackets, re_nothing, note)
                    if e_new == note:
                        while True:
                            e_new = re.sub(r'\tphonetic.*?;', re_nothing, note)
                            if e_new == note:
                                break
                            else:
                                note = e_new
                        notes.append(note.strip())
                        break
                    note = e_new

            # 英文
            eng_pos = re.findall(re_eng_pos, contents_no_newline)
            eng_meaning = re.findall(re_eng_meaning, contents_no_newline)
            eng_meanings = list()
            for i in range(len(eng_pos)):
                eng_meanings.append("({0}) {1}".format(re.sub(re_square_brackets, re_nothing, eng_pos[i]),
                                                       re.sub(re_square_brackets, re_nothing, eng_meaning[i])))
            # 同音
            homonyms = re.findall(re_can_phon, contents_no_newline)
            homonyms_list = list()
            for row in homonyms:
                while True:
                    e_new = re.sub(re_square_brackets, re_nothing, row)
                    if e_new == row:
                        homonyms_list.append(row.strip())
                        break
                    row = e_new

            self.homonyms = homonyms_list
            self.url = url
            self.examples = examples
            self.brief_explains = brief_explains
            self.audios = pronunciation
            self.cangjie_pattern = cangjie_pattern
            self.char_can_notes = notes
            self.eng_meanings = '\n'.join(eng_meanings)
            self.word_example = word_example
            self.word = word
        except UnicodeEncodeError:  # no this word in utf8
            print("no this word in utf8")  # Define a few command handlers. These usually take the two arguments bot and

    def __init__(self, input):
        if type(input) == str:
            self.__init__str(input)
            return
        elif type(input) == tuple:
            self.url = input[1]
            self.examples = input[2].split(',')
            self.brief_explains = input[3]
            self.audios = input[4][1:-1].replace("'", "").split(',')
            self.cangjie_pattern = input[5]
            self.char_can_notes = input[6][1:-1].split(',')
            self.eng_meanings = input[7]
            self.word_example = input[8][1:-1].split(',')
            self.homonyms = input[9][1:-1].split(',')
            self.word = input[0]


@run_async
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    update.message.reply_text('請使用行內模式\nPlease use inline mode\nhttps://github.com/tlyeung/cantondict')


@run_async
def help(bot, update):
    update.message.reply_text('請使用行內模式\nPlease use inline mode\nhttps://github.com/tlyeung/cantondict')


@run_async
def escape_markdown(text):
    """Helper function to escape telegram markup symbols"""
    escape_chars = '\*_`\['
    return re.sub(r'([%s])' % escape_chars, r'\\\1', text)


@run_async
def inline_query(bot, update):
    word = update.inline_query.query
    results = list()

    if len(word) >= 1:
        with connection.cursor() as cursor:
            sql = "select * from CantonDict where word=%s limit 1"
            cursor.execute(sql, (word[0]))
            result = cursor.fetchone()

        if result:
            canton_dict = CantonDict(result)
        else:
            canton_dict = CantonDict(word[0])
            with connection.cursor() as cursor:
                sql = "INSERT INTO `CantonDict`" \
                      " (`word`, `url`,`examples`,`brief_explains`,`audios`" \
                      ",`cangjie_pattern`,`char_can_notes`,`eng_meanings`,`word_example`,`homonyms`)" \
                      " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                cursor.execute(sql,
                               (word[0],
                                canton_dict.url,
                                str(canton_dict.examples).replace("[", "").replace("]", ""),
                                str(canton_dict.brief_explains).replace("[", "").replace("]", ""),
                                str(canton_dict.audios).replace("[", "").replace("]", ""),
                                canton_dict.cangjie_pattern,
                                str(canton_dict.char_can_notes).replace("[", "").replace("]", ""),
                                canton_dict.eng_meanings,
                                str(canton_dict.word_example).replace("[", "").replace("]", ""),
                                str(canton_dict.homonyms).replace("[", "").replace("]", "")))
            connection.commit()

        if len(canton_dict.audios) == len(canton_dict.char_can_notes):
            for index in range(len(canton_dict.audios)):
                both = canton_dict.char_can_notes[index] and canton_dict.examples[index]
                results.append(InlineQueryResultAudio(
                    id=uuid4(),
                    title="「{0}」讀音：{1},{2}".format(
                        word[0], canton_dict.char_can_notes[index], canton_dict.examples[index])
                    if both else
                    "「{0}」讀音：{1}{2}".format(
                        word[0], canton_dict.char_can_notes[index], canton_dict.examples[index]),
                    audio_url='http://humanum.arts.cuhk.edu.hk/Lexis/lexi-mf/{0}'.format(canton_dict.audios[index])))

        if canton_dict.word_example:
            example_line = list()
            empty = True
            for example in canton_dict.examples:
                example_line.append(example.replace("'", "").strip())
                if example.replace("'", "").strip():
                    empty = False
            if len(example_line) > 0 and not empty:
                results.append(InlineQueryResultArticle(
                    id=uuid4(),
                    title="「{0}」例子".format(word[0]),
                    input_message_content=InputTextMessageContent(
                        "「{0}」例子\n{1}".format(word[0], "\n".join(example_line)))))

        if canton_dict.brief_explains:
            is_str = type(canton_dict.brief_explains) is str
            results.append(InlineQueryResultArticle(
                id=uuid4(),
                title="「{0}」略說".format(word[0]),
                input_message_content=InputTextMessageContent(
                    "「{0}」{1}".format(word[0],
                                      ast.literal_eval(canton_dict.brief_explains.replace('\\\\', '\\')).decode())
                    if is_str else canton_dict.brief_explains[0].decode('utf8'))))

        if canton_dict.eng_meanings:
            results.append(InlineQueryResultArticle(
                id=uuid4(),
                title="「{0}」English meaning".format(word[0]),
                input_message_content=InputTextMessageContent(
                    "「{0}」English meaning\n{1}".format(word[0], canton_dict.eng_meanings))))

        if len(canton_dict.audios) == len(canton_dict.homonyms):
            for index in range(len(canton_dict.audios)):
                results.append(InlineQueryResultArticle(
                    id=uuid4(),
                    title="「{0}」({1})同音字".format(word[0],
                                                 canton_dict.audios[index][6:-4]),
                    input_message_content=InputTextMessageContent(
                        "「{0}」{1} 同音字\n{2}".format(word[0], canton_dict.audios[index][6:-4],
                                                   canton_dict.homonyms[index]))))

        if canton_dict.cangjie_pattern:
            results.append(InlineQueryResultArticle(
                id=uuid4(),
                title="「{0}」倉頡碼".format(word[0]),
                input_message_content=InputTextMessageContent(
                    "「{0}」倉頡碼：{1}".format(word[0], canton_dict.cangjie_pattern))))

        if canton_dict.url:
            results.append(InlineQueryResultArticle(
                id=uuid4(),
                title="「{0}」更多".format(word[0]),
                input_message_content=InputTextMessageContent(canton_dict.url)))

    update.inline_query.answer(results)


@run_async
def error_handle(bot, update, error):
    logger.warning('Update "%s" caused error "%s"' % (update, error))


@run_async
def process(word):
    pass


def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater("")

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))

    # on non-command i.e message - echo the message on Telegram
    dp.add_handler(InlineQueryHandler(inline_query))

    # log all errors
    dp.add_error_handler(error_handle)

    # Start the Bot
    updater.start_polling()

    # Block until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
