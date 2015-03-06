#! /usr/bin/env python
# -*- coding: UTF-8 -*-
#
"""Отправка RSS на E-mail

Требования:
- Python версии 3.0 и выше.
- config.py
- typo.py

Рекомендации:
- наличие в системе локали ru_RU.UTF-8

Использование:
- создать config.json
- (опционально) mkdir archive_<config name>; ARCHIVE -> True
- $ nohup nice -19 python3 rss.py &

Сайт проекта:
- <https://code.google.com/p/rss-email/>
- <http://rss-mail.blogspot.ru/>"""
__version__ = 1, 5, 0
__author__ = ["Александр <mono9lith@gmail.com>",]
__license__ = """\
Эта программа является свободным программным обеспечением: вы можете
использовать её согласно условиям открытого лицензионного соглашения GNU
(GNU GPL) версии 3 или, по вашему желанию, любой более поздней версии.

Эта программа распространяется в надежде, что она будет полезной, но без
каких-либо гарантий. Для получения более подробной информации смотрите
открытое лицензионное соглашение GNU: <https://gnu.org/licenses/gpl.html>."""
#
import html.entities
import html.parser
import datetime
import urllib.request
import re
import gzip
import typo
import json
import locale
import time
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.header import Header as MIMEHeader
from email.mime.multipart import MIMEMultipart

__all__ = ["getGen", "getRss", "getWebPage", "parseHtml"]
DEBUG = False
ARCHIVE = True
IO_CODING = "utf_8"    # кодировка по умолчанию зависит от системной!
UTF8 = "UTF-8"
JOIN = "".join
JOIN_N = "\n".join
RANGE = range
LEN = len
INT = int
CHR = chr
LIST = list
ENUMERATE = enumerate
RE_C = re.compile
DATE_TIME_FORMAT = "%d %b, %H:%M"
DATE_TIME_NOW = datetime.datetime.now
NAME_TO_CHR = html.entities.html5
ISINSTANCE = isinstance
HEADERS = {
    # Connection: close - передаёт сам urllib.request
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:31.0) Gecko/20100101 Firefox/31.0",
    "Accept-Language": "ru,ru-ru;q=0.8,en-us;q=0.5,en;q=0.3",
    "Accept-Encoding": "gzip, deflate",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
def subEnt(match):
    """замена именованных HTML символов на Unicode"""
    # для повторного прогона извлеченного текста
    try:
        return NAME_TO_CHR[match.group(1)]
    except KeyError:
        return ""
def subNum(match):
    """замена числовых HTML символов на Unicode"""
    # для повторного прогона извлеченного текста
    text = match.group(1)
    start = text[0]
    xStart = start == "x" or start == "X"
    try:
        return CHR(INT(text[1:] if xStart else text))
    except:
        return ""
HELLIP = "\u2026"    # многоточие (...)
HYP = "\u2010"    # дефис
NBHYP = "\u2011"    # дефис неразрывный (аб-вг)
NDASH = "\u2013"    # тире короткое (аб - вг)
MDASH = "\u2014"    # тире длинное (аб - вг)
SYM = HELLIP + HYP + NBHYP + NDASH + MDASH

# удаление знаков препинания с конца для обрезания текста
EXP_DEL = ((RE_C(r"[{0}\-.,!?:;/ ]+$".format(SYM)).sub, r""),)
EXP_CLEAN = (
    (RE_C(r"(?:^[^<]*>|<[^>]*>|<[^>]*$)").sub, r" "),    # удаляет HTML теги
    (RE_C(r"&(\w{1,8};)").sub, subEnt),    # заменяет HTML последовательности
    (RE_C(r"&#(\d{1,5});").sub, subNum),    # заменяет HTML последовательности

    # удаляет лишние пробелы и табы в начале и конце строки, переносы строки
    (RE_C(r"(?:(?<=\n)|^)[ \t]+|[ \t]+(?:(?=\n)|$)|(?<=\n\n)\n+").sub, r""),

    (RE_C(r"[ \t]{2,}").sub, r" "),    # удаляет лишние пробелы
    (RE_C(r" *[\n\r]+ *").sub, r" "),    # удаляет переносы строк
)
RULE_CLEAN = (
    ("\n", " "),
    ("\r", " "),
)

class MyHTMLParser(html.parser.HTMLParser):
    def __init__(self):
        html.parser.HTMLParser.__init__(self)
        self.items = []
        self.ITEMS_APPEND = self.items.append
        self.NAME_TO_CHR = html.entities.html5
        self.CHR = chr
        self.INT = int
    def handle_starttag(self, tag, attrs):
        self.ITEMS_APPEND((0, tag))
        self.items += [(1, attr) for attr in attrs]
    def handle_endtag(self, tag):
        self.ITEMS_APPEND((2, tag))
    def handle_data(self, data):
        self.ITEMS_APPEND((3, data))
    def unknown_decl(self, data):
        self.ITEMS_APPEND((4, data))
    def handle_entityref(self, name):
        """конвертирует именованные HTML символы в Unicode 'amp;' -> '&'"""
        try:
            c = self.NAME_TO_CHR[name]
        except KeyError:
            return
        self.ITEMS_APPEND((3, c))
    def handle_charref(self, name):
        """конвертирует числовые HTML символы в Unicode"""
        start = name[0]
        xStart = start == "x" or start == "X"
        try:
            c = self.CHR(self.INT(name[1:] if xStart else name))
        except:
            return
        self.ITEMS_APPEND((3, c))


def getRss(items, url, title_len, desc_len):
    """находит запись ленты и вынимает элементы"""
    NOW = DATE_TIME_NOW()
    NOW_DATE = INT(NOW.strftime("%Y%m%d"))
    NOW_SHORT = NOW.strftime(DATE_TIME_FORMAT)
    if not items:
        LOG_APPEND(NOW_SHORT + " getRss: no items: " + url)
        return {}

    # определяет тип ленты
    isRss = None
    if LEN(items) > 5:
        for i in RANGE(0, 5):
            if items[i][0] == 0:
                for txt in ("rss", "RSS"):
                    if items[i][1] == txt:
                        isRss = True
                        break
                if isRss is None:
                    for txt in ("feed", "FEED"):
                        if items[i][1] == txt:
                            isRss = False
                            break
    if isRss is None:
        LOG_APPEND(NOW_SHORT + " getRss: can't determ feed type: " + url)
        return {}
    ITEM = "item" if isRss else "entry"
    REPLACE = manyReplace
    LINK = "link"
    TITLE = "title"
    DESC = "description" if isRss else "summary"

    def getItemContent(items, name, index, atomLink=False):
        """вынимает содержимое элемента"""
        result = ""
        for i, j in findElement(items, name, index[0], index[1]):
            for k in RANGE(i, j):    # range(0, 9) -> 0,1,2,3,4,5,6,7,8
                if atomLink:
                    if (items[k][0] == 1 and items[k][1][0] == "rel" and
                        items[k][1][1] == "alternate"):
                        result = items[k + 2][1][1]
                        break
                else:
                    if items[k][0] == 3 and items[k][1]:
                        result = items[k][1]
                        break
                    elif items[k][0] == 4:
                        result = items[k][1].replace("CDATA[", "")
                        break
            break
        return result

    # собирает новые элементы
    result = {}
    for i, j in findElement(items, ITEM):
        title = getItemContent(items, TITLE, (i + 1, j - 1))
        desc = getItemContent(items, DESC, (i + 1, j - 1))
        link = getItemContent(items, LINK, (i + 1, j - 1), not isRss)
        if not link.strip():
            continue
        title = REPLACE(title, RULE_CLEAN)    # удаляет лишние символы
        title = title[:title_len + 500]    # обрезает (с учётом удалённых HTML тегов)
        desc = REPLACE(desc, RULE_CLEAN)    # удаляет лишние символы
        desc = desc[:desc_len + 500]    # обрезает (с учётом удалённых HTML тегов)
        result[link] = {TITLE: title, "date": NOW_DATE, "desc": desc}
    if not result:
        LOG_APPEND(NOW_SHORT + " getRss: nothing extracted: " + url)
    return result


def findElement(items, name, start=0, end=0):
    """ищет элементы в диапозоне"""
    #TODO возвращает без конечного </элемента>
    if not end:
        end = LEN(items)
    else:
        end += 1    # компенсация range()
    # ищет начальный <item>
    index = start
    for i in RANGE(start, end):    # range(0, 9) -> 0,1,2,3,4,5,6,7,8
        if i < index:    # пропуск лишних элементов
            continue
        if items[i][0] == 0 and items[i][1] == name:
            # ищет конечный </item>
            for j in RANGE(i + 1, end):
                if items[j][0] == 2 and items[j][1] == name:
                    yield i, j
                    index = j + 1
                    break    # переходит к следующему начальному <item>


def getGen(items, root, url, width):
    """находит root элемент и вынимает ссылки"""
    #TODO
    #TODO обрезание и чистка
    NOW = DATE_TIME_NOW()
    NOW_DATE = INT(NOW.strftime("%Y%m%d"))
    NOW_SHORT = NOW.strftime(DATE_TIME_FORMAT)
    result = {}
    for i, j in findElement(items, root[0]):    # находит все <div></div>
        # запускает извлечение
        # если есть нужный атрибут в root
        for k in RANGE(i + 1, j - 1):
            if (
                items[k][0] == 1 and
                items[k][1][0] == root[1] and
                (
                    items[k][1][1] == root[2] or
                    " " + root[2] + " " in items[k][1][1] or
                    items[k][1][1].startswith(root[2]) or
                    items[k][1][1].endswith(root[2])
                )
            ):
                # вынимает ссылки из элементов внутри root
                for id, data in linkExtract(items, k, j - 1, url, width, NOW_DATE):
                    result[id] = data
                break    # завершает поиск по атрибутам
    if not result:
        LOG_APPEND(NOW_SHORT + " getGen: nothing extracted: " + url)
    return result


def linkExtract(items, i, j, url, width, date):
    """вынимает ссылки из HTML"""
    RE_SUB = reSub
    CUT_TEXT = cutText
    #TODO root-element is a
    for k, m in findElement(items, "a", i, j):
        title = ""
        addr = ""
        for n in RANGE(k, m):
            if items[n][0] == 1 and items[n][1][0] == "href" and not addr:
                addr = items[n][1][1]
            if items[n][0] == 3 and not title:
                title = items[n][1]
        if addr:
            title = RE_SUB(title, EXP_CLEAN)    # удаляет лишние символы
            title = CUT_TEXT(title, width, EXP_DEL)    # обрезает заголовок
            yield (
                addr if addr.startswith("http") else URL_JOIN(url, addr),
                {"title": title, "date": date, "desc": ""},
            )


def getWebPage(url, xml=True):
    # используется urllib вместо socket для обхода
    # обработки "Transfer-Encoding: chunked" в сыром ответе
    # и обхода обработки HTTPS
    NOW_SHORT = DATE_TIME_NOW().strftime(DATE_TIME_FORMAT)
    MAX_SIZE = 1048576    # 1 МиБ
    data = None
    contentType = b""
    req = urllib.request.Request(url, headers=HEADERS)

    # получает данные из интернета
    try:
        with urllib.request.urlopen(req, timeout=7) as inFile:
            data = inFile.read()
            contentType = inFile.getheader("Content-Type", "").encode("ascii")
            contentEncoding = inFile.getheader("Content-Encoding", "")
        if DEBUG:
            LOG_APPEND(NOW_SHORT + " getWebPage: downloaded: " + url)
    except Exception as ex:
        LOG_APPEND(NOW_SHORT + " getWebPage: " + str(ex) + ": " + url)
        return None
    if LEN(data) > MAX_SIZE:
        LOG_APPEND(NOW_SHORT + " getWebPage: too big: " + url)
        return None
    if contentEncoding == "gzip":
        data = gzip.decompress(data)
    elif contentEncoding != "":    # другое сжатие
        return None
    data = contentType + data

    # определяет тип кодировки
    coding = None
    tmp = data[:500 if xml else 1200]
    for enc in (b"utf-8", b"UTF-8", b"utf8", b"UTF8"):
        if enc in tmp:
            coding = "utf_8"
            break
    if not coding:
        for enc in (b"windows-1251", b"WINDOWS-1251", b"cp1251", b"CP1251"):
            if enc in tmp:
                coding = "cp1251"
                break
    if not coding:
        for enc in (b"koi8-r", b"KOI8-R"):
            if enc in tmp:
                coding = "koi8_r"
                break
    if not coding:
        for enc in (b"windows-1252", b"WINDOWS-1252", b"cp1252", b"CP1252",
                    b"iso-8859-1", b"ISO-8859-1", b"iso8859-1", b"ISO8859-1",
                    b"cp819", b"CP819", b"latin1", b"LATIN1",):
            if enc in tmp:
                coding = "cp1252"
                break
    if coding:
        return data.decode(coding, errors="replace")
    else:
        LOG_APPEND(NOW_SHORT + " getWebPage: can't determine enc: " + url)
        return None


def reSub(text, reList):
    """замена текста для re"""
    for sub, repl in reList:
        text = sub(repl, text)
    return text


def manyReplace(text, rules):
    """заменяет части в тексте"""
    for sub, repl in rules:
        text = text.replace(sub, repl)
    return text

def cutText(text, width, expCut):
    """Обрезает текст до нужной длины"""
    if LEN(text) < width:
        return text
    HELLIP = "\u2026"    # многоточие (...)
    WORD_WIDTH = 20
    text = text[:width]
    index = text.rfind(" ", -WORD_WIDTH, -1)
    if index != -1:
        text = text[:index]
    return reSub(text, expCut) + HELLIP


def formContent(new_file, header, title_len, desc_len, source):
    """собирает HTML"""
    #TODO markdown, json
    #TODO костыльно
    RECORD_FORMAT = "<br>\n<br>\n<a target=\"_blank\" href=\"{1}\"><b>{0}</b></a><br>\n{2}".format
    RECORD_FORMAT_NODESC = "<br>\n<br>\n<a target=\"_blank\" href=\"{1}\"><b>{0}</b></a>{2}".format
    RECORD_FORMAT_FIRST = "\n<a target=\"_blank\" href=\"{1}\"><b>{0}</b></a><br>\n{2}".format
    RECORD_FORMAT_NODESC_FIRST = "\n<a target=\"_blank\" href=\"{1}\"><b>{0}</b></a>{2}".format
    STYLE = (
        "\n<style>\n"
        "html {\n"
        "    background-color: #f6f5f3;\n"
        "    font-family: sans-serif;\n"
        "    font-size: .8em;\n"
        "    line-height: 1.4;\n"
        "    color: #222;\n"
        "    margin: 0;\n"
        "    padding: 1em;\n"
        "}\n"
        "body {\n"
        "    background-color: #fff;\n"
        "    max-width: 600px;\n"
        "    margin: 2em auto;\n"
        "    padding: 2em 4em;\n"
        "    border: 1px solid #e6e6e6;\n"
        "    border-radius: 2px;\n"
        "}\n"
        "a {\n"
        "    text-decoration: none;\n"
        "}\n"
        "a:link {\n"
        "    color: #22c;\n"
        "}\n"
        "a:hover {\n"
        "    text-decoration: underline;\n"
        "}\n"
        "</style>"
    )
    HTML = "<!DOCTYPE html>\n<meta charset={0}>\n<title>~t~</title>".format(UTF8) + STYLE + "\n\n<h1>~t~</h1>\n~c~"
    CAPTION_FORMAT = "\n<h2 class=\"first\">{0}</h2>\n<hr>\n".format
    CAPTION_FORMAT2 = ("\n<h2><a href=\"{1}\">{0}</a> ({2})</h2>\n" if DEBUG
                        else "\n\n<h2>{0}</h2>\n").format
    CUT_TEXT = cutText
    REPLACE = manyReplace
    RE_SUB = reSub
    EXP_ESC = (
        ("&", "&amp;"),
        ("<", "&lt;"),
        (">", "&gt;"),
    )
    result = []
    RESULT_APPEND = result.append
    groups = LIST(new_file)
    groups.sort()
    for group in groups:
        escaped_group = REPLACE(group, EXP_ESC)
        RESULT_APPEND(CAPTION_FORMAT(escaped_group))    # добавляет раздел
        firstFeed = True    #TODO
        for feed in new_file[group]:
            leng = LEN(new_file[group][feed])
            escaped_feed = REPLACE(feed, EXP_ESC)
            source_feed = source[group][feed]
            if not ISINSTANCE(source_feed, str):
                source_url = source_feed["url"]
            else:
                source_url = source_feed
            escaped_url = REPLACE(source_url, EXP_ESC)
            RESULT_APPEND(CAPTION_FORMAT2(escaped_feed, escaped_url, leng))    # добавляет ленту
            firstFeed = False
            firstRecord = True
            for record in new_file[group][feed]:

                title = RE_SUB(new_file[group][feed][record]["title"], EXP_CLEAN)    # удаляет лишнее
                title = TYPO(title)    # типографизирует
                title = CUT_TEXT(title, title_len, EXP_DEL)    # обрезает
                desc = RE_SUB(new_file[group][feed][record]["desc"], EXP_CLEAN)    # удаляет лишнее
                desc = TYPO(desc)    # типографизирует
                desc = CUT_TEXT(desc, desc_len, EXP_DEL)    # обрезает

                escaped_title = REPLACE(title, EXP_ESC)
                escaped_link = REPLACE(record, EXP_ESC)
                escaped_desc = REPLACE(desc, EXP_ESC)

                if not escaped_title:
                    escaped_title = "(нет заголовка)"

                RE_FO = RECORD_FORMAT
                if not escaped_desc and not firstRecord:
                    RE_FO = RECORD_FORMAT_NODESC
                elif escaped_desc and not firstRecord:
                    RE_FO = RECORD_FORMAT
                elif escaped_desc and firstRecord:
                    RE_FO = RECORD_FORMAT_FIRST
                elif not escaped_desc and firstRecord:
                    RE_FO = RECORD_FORMAT_NODESC_FIRST
                if DEBUG:
                    escaped_desc = str(len(escaped_desc)) + ", "  + escaped_desc

                RESULT_APPEND(RE_FO(escaped_title, escaped_link, escaped_desc))    # добавляет ссылку
                firstRecord = False
    return HTML.replace("~t~", header).replace("~c~", JOIN(result))


def parseHtml(text, url):
    """возвращает <list>(<tuple>(<int>, <str>)) список найденных элементов
    тип, значение
    """
    NOW_SHORT = DATE_TIME_NOW().strftime(DATE_TIME_FORMAT)
    #TODO? from xml.etree.ElementTree import parse
    #TODO удаление (3, '\n\n')
    if not text:
        return []
    parser = MyHTMLParser()
    itemsP = parser.items
    try:
        parser.feed(text)
        parser.close()
    except html.parser.HTMLParseError as ex:
        LOG_APPEND(NOW_SHORT + " parseHtml: " + str(ex) + ": " + url)
        return []

    #TODO оптимизировать
    # находит идущие подряд элементы данных
    # для сбора в одно целое текста и элементов типа &amp; и &#62;
    # текст, текст, ... -> текст
    leng = LEN(itemsP)
    result = []
    RESULT_APPEND = result.append
    for i in RANGE(0, leng):
        if (
            (
                itemsP[i][0] == 3 and    # item - текст
                i < leng - 1 and    # item не последний и не предпоследний
                itemsP[i + 1][0] == 3 and    # следующий item - текст
                i != 0 and    # item не первый элемент
                itemsP[i - 1][0] != 3    # предыдущий item - не текст
            ) or
            (
                itemsP[i][0] == 3 and    # item - текст
                i < leng - 1 and    # item не последний и не предпоследний
                itemsP[i + 1][0] == 3 and    # следующий item - текст
                i == 0    # item - первый элемент
            )
        ):
            indexEnd = i
            for j in RANGE(i, leng):
                if itemsP[j][0] == 3:
                    indexEnd += 1    # ищет конечный элемент текста подряд
                else:
                    RESULT_APPEND((i, indexEnd - 1))
                    break

    # удаляет лишнее (элементы типа &amp; и &#62;)
    # собирает в одно целое
    for i, j in result[::-1]:
        ll = (itemsP[k][1] for k in RANGE(i, j + 1))
        itemsP[i] = (3, JOIN(ll))
        for k in RANGE(i + 1, j + 1)[::-1]:
            del itemsP[k]
    return itemsP


def delEnt(current, dumped, changed):
    """удаляет записи, отсутствующие в текущем конфиге"""
    for group in LIST(dumped):
        if group not in current:
            del dumped[group]
            changed = True
            LOG_APPEND("delEnt: del group: " + group)
            continue
        for feed in LIST(dumped[group]):
            if feed not in current[group]:
                del dumped[group][feed]
                changed = True
                LOG_APPEND("delEnt: del feed: " + feed)
    return changed


def sendThrough(mailfrom, mailto, mailsubj, mailtext, server, port, login,
                password, tls=True, filename="news.html"):
    """Собственно делает отправку"""
    # может пригодиться
    #TEXT_CODING = "utf_8"
    #SUBJ_CODING = "utf_8"
    #try:
    #    mailtext.encode("cp1251")
    #    TEXT_CODING = "cp1251"
    #except:
    #    pass
    #try:
    #    mailsubj.encode("cp1251")
    #    SUBJ_CODING = "cp1251"
    #except:
    #    pass

    # собирает сообщение
    msg = MIMEMultipart()
    msg["Subject"] = MIMEHeader(mailsubj, UTF8, 76)
    msg["From"] = "\"{0}\" <{1}>".format(mailfrom.split("@")[0], mailfrom)
    msg["To"] = "\"{0}\" <{1}>".format(mailto.split("@")[0], mailto)
    msg.attach(MIMEText("новости:", "plain", UTF8))
    a = MIMEText(mailtext, "html", UTF8)
    a.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(a)
    if DEBUG:
        print(msg)
        return

    # отправляет
    smtpserver = smtplib.SMTP(server, port, timeout=7)
    smtpserver.ehlo("localhost.localdomain")
    if tls:
        smtpserver.starttls()
        smtpserver.ehlo("localhost.localdomain")
    smtpserver.login(login, password)
    smtpserver.sendmail(mailfrom, mailto, msg.as_string())
    smtpserver.quit()


def main(config_name, config):
    NOW = DATE_TIME_NOW()
    NOW_HOUR = NOW.hour
#    loc = locale.getlocale()
    try:
        # необходимо наличие локали в системе
        locale.setlocale(locale.LC_ALL, ("ru_RU","UTF8"))
        HEADER = "Новости {0}".format(NOW.strftime("%-d %b %Y"))
#        locale.setlocale(locale.LC_ALL, loc)
    except:
        HEADER = "Новости {0}".format(NOW.strftime("%d.%m.%Y"))
    DUMP_F = config_name + "_dump.json"
    NEW_F = config_name + "_new.json"
    NOW_SHORT = NOW.strftime(DATE_TIME_FORMAT)
    LOG_APPEND(NOW_SHORT + " ==================== " + config_name + ": Starting RSS to E-mail!")

    # загружает файлы
    try:
        dump_file = loadJson(DUMP_F)
    except:
        dump_file = {}
        LOG_APPEND(NOW_SHORT + " main: can't load DUMP_F")
    try:
        new_file = loadJson(NEW_F)
    except:
        new_file = {}
        LOG_APPEND(NOW_SHORT + " main: can't load NEW_F")
    MAX_ITEMS = config["RECORDS_MAX"]    # длиннее длины самой длинной ленты

    # формирует текущий дамп из Rss лент
    dump = {}    # новые, не отправленные
    for group in config["FEEDS"]:
        if group not in dump:
            dump[group] = {}
        for feed in config["FEEDS"][group]:
            url = config["FEEDS"][group][feed]
            if ISINSTANCE(url, str):
                dump[group][feed] = getRss(
                    parseHtml(getWebPage(url), url),
                    url,
                    config["TITLE_LENGTH_MAX"],
                    config["DESC_LENGTH_MAX"]
                )
            else:
                dump[group][feed] = getGen(
                    parseHtml(getWebPage(url["url"], False), url["url"]),
                    url["root"],
                    url["url"],
                    config["TITLE_LENGTH_MAX"]
                )

    # формирует дамп новых записей, отсутствующих в файле старых записей
    # для записи в файл новых или отправки
    # ! дополняет (формирует) структуру new_file и dump_file
    # new_file = (dump - dump_file) + new_file
    new_file_changed = False
    for group in dump:

        # новая группа в конфиге
        if group not in new_file:
            new_file[group] = {}
        if group not in dump_file:
            dump_file[group] = {}

        for feed in dump[group]:

            # новая лента в конфиге
            if feed not in new_file[group]:
                new_file[group][feed] = {}
            if feed not in dump_file[group]:
                dump_file[group][feed] = {}

            for record in dump[group][feed]:
                if record not in dump_file[group][feed]:
                    new_file[group][feed][record] =\
                        dump[group][feed][record]
                    new_file_changed = True

    # удаляет из new_file группы и ленты, отсутствующие в config-rss
    new_file_changed = delEnt(dump, new_file, new_file_changed)

    # сохраняет дамп новых перед отправкой
    if new_file_changed:
        try:
            dumpJson(new_file, NEW_F)
        except:
            LOG_APPEND(NOW_SHORT + " main: can't dump new file")
            return 1

    # делает отправку
    # первый запуск
    if not config_name in sendState:
        sendState[config_name] = False
    # вышли из часа для отправки
    if config["HOUR"] != NOW_HOUR:
        sendState[config_name] = False
    if (config["HOUR"] == NOW_HOUR and not sendState[config_name]) or DEBUG:
#    if True:
        # собирает HTML, отправляет
        result = formContent(new_file, HEADER, config["TITLE_LENGTH_MAX"],
                             config["DESC_LENGTH_MAX"], config["FEEDS"])
        try:
            sendThrough(
                config["FROM"], config["TO"], HEADER, result, config["SMTP"],
                config["SMTP_PORT"], config["LOGIN"], config["PASSWORD"],
                tls=config["TLS"], filename="news-" + NOW.strftime("%Y%m%d") + ".html"
            )
            LOG_APPEND(NOW_SHORT + " *** E-mail sended!")
            sendState[config_name] = True    # отправили
        except Exception as ex:
            LOG_APPEND(NOW_SHORT + " main: can't send e-mail! Error: " + str(ex))
            if DEBUG:
                raise
            return 1

        # пишет результат в файл
        if ARCHIVE:
            arcName = "archive_" + config_name + "/news-" + NOW.strftime("%Y%m%d")
            try:
                with open(arcName + ".html", "w", encoding=IO_CODING) as outFile:
                    outFile.write(result)
                dumpJson(new_file, arcName + ".json", True)
            except Exception as ex:
                LOG_APPEND(NOW_SHORT + " main: can't write archive html: " + str(ex))

        # формирует новый дамп старых записей для записи в файл после отправки
        # dump_file = dump_file + new_file (отправленный)
        for group in new_file:
            for item in new_file[group]:
                for record in new_file[group][item]:
                    dump_file[group][item][record] =\
                        new_file[group][item][record]

        # записывает дамп старых
        try:
            dumpJson(dump_file, DUMP_F)
        except:
            LOG_APPEND(NOW_SHORT + " main: can't dump old file")
            return 1

        # очищает дамп новых
        try:
            with open(NEW_F, "w") as outFile:
                outFile.write("{}")
        except:
            LOG_APPEND(NOW_SHORT + " main: can't write clean new")

    # делает очистку
    # первый запуск
    if not config_name in cleanState:
        cleanState[config_name] = False
    # вышли из часа для отправки
    if config["HOUR"] + 1 != NOW_HOUR:
        cleanState[config_name] = False
    if config["HOUR"] + 1 == NOW_HOUR and not cleanState[config_name]:
        dump_file_changed = False

        # удаляет из dump_file группы и ленты, отсутствующие в config-rss
        dump_file_changed = delEnt(dump, dump_file, dump_file_changed)

        # удаляет из dump_file старые записи (усекает)
        for group in dump_file:
            for feed in dump_file[group]:
                records = dump_file[group][feed]
                i = LEN(records)
                delta = i - MAX_ITEMS
                if delta > 0:
                    # from operator import itemgetter
                    # rows = list(records)
                    # rows_by_date = sorted(rows, key=itemgetter('date'))
                    lst = [(rc, records[rc]["date"]) for rc in records]
                    lst.sort(key=lambda i:i[1])
                    lst = lst[:delta]
                    for uid, date in lst:
                        del records[uid]
                    LOG_APPEND(NOW_SHORT + " main: del records: " + feed + " " + str(delta))
                    dump_file_changed = True

        # записывает дамп старых
        if dump_file_changed:
            try:
                dumpJson(dump_file, DUMP_F)
            except:
                LOG_APPEND(NOW_SHORT + " main: can't dump old file")

        LOG_APPEND(NOW_SHORT + " *** Cleaned!")
        cleanState[config_name] = True    # очистили

    if DEBUG:
        result = formContent(new_file, "HEADER", config["TITLE_LENGTH_MAX"],
                             config["DESC_LENGTH_MAX"], config["FEEDS"])
        try:
            with open(config_name + "_test_index.html", "w", encoding=IO_CODING) as outFile:
                outFile.write(result)
        except:
            LOG_APPEND(NOW_SHORT + " main: can't write debug html")


def dumpJson(data, name, human=DEBUG):
    dumped = json.dumps(
        data,
        ensure_ascii=False,
        separators=(",", ":") if not human else None,
        indent=None if not human else 4,
    )
    with open(name, "w", encoding=IO_CODING) as outFile:
        outFile.write(dumped)


def loadJson(name):
    with open(name, encoding=IO_CODING) as inFile:
        return(json.loads(inFile.read(), encoding=IO_CODING))


if __name__ == "__main__":
    # кеширующие переменные - для _нагруженных_ циклов
    TYPO = typo.typographize
    URL_JOIN = urllib.parse.urljoin
    sendState = {}    # статус: отправлено ли уже письмо
    cleanState = {}    # статус: очищено ли уже
    while 1:
        # перечитывает конфиг при каждом запуске
        # без конфига - падает
        CONFIG = loadJson("config.json")

        for config in CONFIG:
            log = []
            LOG_APPEND = log.append
            try:    #TODO костыль чтобы программа не упала целиком
                main(config, CONFIG[config])
            except Exception as ex:
                LOG_APPEND("EE: _loop_: error in main: " + str(ex))
                if DEBUG:
                    raise

            # пишет лог
            try:
                with open("rss.log", "a", encoding=IO_CODING) as outFile:
                    outFile.write(JOIN_N(log) + "\n")
            except Exception as ex:
                print("EE: can't write log: " + str(ex))
        if DEBUG:
           print("end of job")
        time.sleep(600)
