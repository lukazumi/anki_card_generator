# -*- coding: utf-8 -*-
# Luke Jackson
import re
import urllib2
import urllib
from BeautifulSoup import *
from aqt.qt import *
from aqt.utils import showInfo
from anki.hooks import addHook
from japanese.notetypes import isJapaneseNoteType
from aqt import mw

# generate a card from kanji only.
# This plugin will easily break if Jisho changes its HTML or has pages that deviate from my test cases
# So the html classes stored are global variables
HTML_ENG_DIV = "meanings-wrapper"  # there are many (potentially), but only look at the top
HTML_ENG_SPAN = "meaning-meaning"
HTML_FURIGANA_SPAN = "furigana"
HTML_EXAMPLE_ENG_DIV =
HTML_EXAMPLE_JPN_DIV =
##########################################################################
SRC_FIELDS = '???'
DST_FIELDS_ENG = '???'
DST_FIELDS_EX = '???'
DST_FIELDS_READING = '???'  # japanese plugin already does this
HIRAGANA_REGEX = r'[ぁ-ゟ]'


# NOT finished. Bulk get examples method
def get_examples_from_jisho(nids):
    mw.checkpoint("Bulk-add Kanji Examples")
    mw.progress.start()
    failed = []
    for nid in nids:
        note = mw.col.getNote(nid)
        # Amend notetypes.py to add your note types
        _noteName = note.model()['name'].lower()
        if not isJapaneseNoteType(_noteName):
            mw.checkpoint("isJapaneseNoteType")
            continue

        src = None
        for field in srcFields:
            if field in note:
                src = field
                break
        if not src:
            continue
        dst = None
        for field in dstFields:
            if field in note:
                dst = field
                break
        if not dst:
            continue

        srcTxt = mw.col.media.strip(note[src])

        if note[dst]: 
            continue
        if not srcTxt.strip():
            continue

        try:
            stns = formatExamplesAsCSV( getExamples(srcTxt) )
            if len(stns) >0:
                note[dst] = stns
                note.flush()
        except Exception as e:
            failed.append(str(note))
            raise
        
    
    fs=""
    for m in failed:
        fs=fs+m+", "

    if len(fs)>0:
        showInfo(fs)

    mw.progress.finish()
    mw.reset()

# adds a button to ankis menu
def setup_menu(browser):
    a = QAction("Bulk-add Sentences from Jisho.org", browser)
    a.triggered.connect(lambda: onRegenerate(browser))
    browser.form.menuEdit.addSeparator()
    browser.form.menuEdit.addAction(a)


# after pressing the button, just calls (get_examples_from_jisho)
def onRegenerate(browser):
    getExamplesFromJisho(browser.selectedNotes())


# get all the example sentences from Jisho
def getExamples(key_word):
    results = []
    key_word = key_word.replace("~", "")
    if key_word[-1] == u"な":
        key_word = key_word[:-1]
        showInfo(key_word)

    has_more = True
    dictionary_url = "http://jisho.org/search/"   # https://jisho.org/searc/%E3%80%9C%E5%8F%B7%E8%BB%8A%20%23sentences
    dictionary_url = dictionary_url + urllib2.quote(key_word.encode('utf8'))+"%20%23sentences"
    while len(results) < 50 and has_more:
        page = urllib2.urlopen(dictionary_url).read()
        soup = BeautifulSoup(page)
        # find the section we want
        try:
            sentence_divs = soup.findAll("div", {"class": "sentence_content"})  # its a list
            # no results
            if len(sentence_divs) < 1:
                return results
            for div in sentence_divs:
                children = div.findChildren("li")
                sentence = ""
                for child in children:
                    reading = ""
                    for i in range(len(child.contents)):
                        span = child.contents[i]
                        append = ""
                        spn_class = span['class']
                        if spn_class[0] == "f":
                            reading = span.contents[0]
                        else:           
                            append = span.contents[0]
                            if key_word in append:
                                append = "<b>%s</b>" % append
                            #elif( len(re.sub(hiragana_full,"",append))>0 and re.sub(hiragana_full,"",append) == re.sub(hiragana_full,"",kanji) ):#kunyomi conjugations
                            #    append="<b>%s</b>" % (append)
                            elif reading != "":
                                append = " " + append + "[" + reading + "]"
                                reading = ""
                        sentence = sentence + append
                eng = div.find("span", {"class": "english"})
                english = str(eng.contents[0])
                results.append([sentence, english])
        except Exception as e:
            raise
        amore = soup.find("a", {"class": "more"})
        if amore is None:
            has_more = False
        else:
            dictionary_url = amore['href']
    return results


def format_examples_as_csv(examples, style):  # style 1 is jap,eng, otherwise jap,jap,...,jap,eng,eng,..,eng
    examples_csv = ""
    if len(examples) > 0:
        if style == 1:
            for r in examples:
                kanj = r[0]
                eng = r[1]
                # showInfo(kanj) #why do some sentences fail? what is the character that is tripping up python???
                # i still dont know so sayounara un-handable sentences.
                try:
                    examples_csv = examples_csv + kanj + " , " + eng + "<br>"
                except Exception as e:
                    continue
        else:
            examples_eng_bubun=""
            itr = 1
            for r in examples:
                kanj = r[0]
                eng = r[1]
                try:
                    examples_csv = examples_csv + str(itr) + ") " + + kanj + "<br>"
                    examples_eng_bubun = examples_eng_bubun + str(itr) + ") " + eng + "<br>"
                    itr = irt + 1
                except Exception as e:
                    continue
            examples_csv = examples_csv + "<br>" + examples_eng_bubun
    return examples_csv


def get_reading_and_english(keyword):  # gets the english definition and reading for a kanji
    results = []
    keyword = keyword.replace("~", "")
    dictionary_url = "http://jisho.org/search/"
    dictionary_url = dictionary_url + urllib2.quote(keyword.encode('utf8'))
    page = urllib2.urlopen(dictionary_url).read()
    soup = BeautifulSoup(page)

    try:

        furigana_html = soup.find("span", {"class": HTML_FURIGANA_SPAN})
        reading = ""
        for s in furigana_html:
            reading = reading+ s.contents[0]
        english = ""
        english_html_div = soup.find("div", {"class": HTML_ENG_DIV})
        english_html_span = english_html_div.find("span", {"class": HTML_ENG_SPAN})
        for s in english_html_span:
            if isinstance(s.contents[0], basestring):
                english = english + s + "; "

        results.append(reading, english)
    except Exception as e:
        raise

    return results


# Focus lost hook
##########################################################################
# SRC_FIELDS
# DST_FIELDS_ENG
# DST_FIELDS_EX
# DST_FIELDS_READING
##########################################################################
def on_focus_lost(flag, n, fidx):
    from aqt import mw

    # japanese model?
    if not isJapaneseNoteType(n.model()['name']):
        return flag
    # have src and dst fields?
    fields = mw.col.models.fieldNames(n.model())
    src = fields[fidx]

    if not src:
        return flag
    # dst field exists?
    if DST_FIELDS_ENG not in n or DST_FIELDS_EX not in n or DST_FIELDS_READING not in n:
        return flag
    # dst field already filled?
    if n[DST_FIELDS_ENG]:
        return flag
    if n[DST_FIELDS_EX]:
        return flag
    if n[DST_FIELDS_READING]:
        return flag


    # grab source text as keyword
    keyword = mw.col.media.strip(n[src])
    if not keyword:
        return flag
    # update field
    try:
        reading_and_english = get_reading_and_english(keyword)
        n[dstEng] = reading_and_english[0]  # array: first element is english, second element is reading
        n[dstEx] = format_examples_as_csv( getExamples(keyword) )
        # reading not filling as the Japanese plugin already takes care of it (but its availible in readingAndEnglish[0][0])

        n.setTagsFromStr("jishoExamples")  # this doesnt work
    except Exception as e:
        raise
    return True

# Init
##########################################################################
addHook('editFocusLost', on_focus_lost)
addHook("browser.setupMenus", setup_menu)
