from robocorp.tasks import task
from RPA.Excel.Files import Files
from RPA.Browser.Selenium import Selenium
import time, os, sys
from deep_translator import GoogleTranslator
import validators
from DOP.RPA.Asset import Asset
from DOP.RPA.ProcessArgument import ProcessArgument
import logging
from RPA.Desktop.Windows import Windows

# Constants
LYRICS_URL = 'https://www.lyrics.com/'
RETRIES_COUNT = 4

# Initialize components
browser = Selenium()
assets = Asset()
args = ProcessArgument()
windows = Windows()
stdout = logging.StreamHandler(sys.stdout)

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="[{%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
    handlers=[stdout],
)
LOGGER = logging.getLogger(__name__)

class LoginError(Exception):
    """Raised when login fails after retries."""
    pass
@task
def main():
    try:
        get_browser()
        if check_login():
            attempt_login()
        get_lyrics()
    except Exception as e:
        LOGGER.error(f"Error when running task: {e}")
    finally:
        browser.close_all_browsers()
    
def get_browser():
    """Opens a new browser window."""
    try: 
        browser.open_available_browser(LYRICS_URL)
    except Exception as e:
        LOGGER.error(f"Error opening browser: {e}")
        return SystemError(f"Error opening browser: {e}")

################################################################
# LOGIN
def check_login():
    """Checks if the user is already logged in."""
    return browser.is_element_visible("id:user-login")

def perform_login(username, password):
    """Performs login using provided username and password."""
    try:
        browser.click_element("id:user-login")
        time.sleep(1)
        enter_text_in_element("css:#fld-uname.fw", username)
        enter_text_in_element("css:#fld-upass.fw", password)
        browser.click_element("css:button[type=submit].lrg")
    except Exception as e:
        LOGGER.error(f"Error performing login: {e}")
        raise LoginError("Login attempt failed")
    
def attempt_login():
    """Attempts to login with retries if login fails."""
    retries = 0
    while retries < RETRIES_COUNT:
        # Get login credentials from user
        # username = args.get_in_arg("username")['value']
        # password = args.get_in_arg("password")['value']
        username = 'twigbang'
        password = 'truongproghe'
        if not username or not password:
            LOGGER.debug("Login cancelled due to missing credentials.")
            raise LoginError("Login cancelled by user")

        try:
            perform_login(username, password)
            if not browser.is_element_visible("css:p.err"):
                LOGGER.info("Login successful.")
                return
            else:
                LOGGER.warning(f"Login failed on attempt {retries + 1}")
        except LoginError:
            retries += 1
            time.sleep(1)

    LOGGER.error("Max retries reached. Login failed.")
    raise LoginError("Exceeded maximum login attempts")
################################################################
# GET LYRICS FROM INPUT
def get_lyrics():
    """Navigates to the Lyrics.com search page and retrieves lyrics for a specified song."""
    try:
        song_name = args.get_in_arg("song_name")['value']
        enter_text_in_element('css:input#search.ui-autocomplete-input', song_name)
        browser.click_element('css:button#page-word-search-button')
        browser.wait_until_element_is_visible('class:best-matches', timeout=10)

        song_list = get_song_list()
        if not song_list:
            LOGGER.warning("No songs found.")
            return

        song_selected = song_list[0]
        if song_selected:
            browser.go_to(song_selected['url'])

        lyrics = get_lyrics_from_song()
        if lyrics:
            translated_lyrics = translate_lyrics(lyrics)
            save_lyrics_to_file(translated_lyrics, song_selected.get('title', song_name))
        else:
            LOGGER.warning("Lyrics not found.")
    except Exception as e:
        LOGGER.error(f"Error retrieving lyrics: {e}")

def get_song_list():
    """Retrieves the list of songs from the search results."""
    try:
        song_list = []
        song_elements = browser.find_elements("css:.best-matches .bm-case")
        for song in song_elements:
            song_title_element = song.find_element("css selector", ".bm-label a")
            song_url = song_title_element.get_attribute("href")
            album_elements = song.find_elements("css selector", ".bm-label b a")
            artist_element = song.find_elements("css selector", ".bm-label a")[-1]
            song_list.append({
                "title": song_title_element.text.strip(),
                "url": song_url,
                "image_url": song.find_element("css selector", ".album-thumb img").get_attribute("src"),
                "album_title": album_elements[1].text if len(album_elements) > 1 else "No album",
                "artist_name": artist_element.text.strip(),
            })
        return song_list
    except Exception as e:
        LOGGER.error(f"Error retrieving song list: {e}")
        return []

def get_lyrics_from_song():
    """Retrieves lyrics from the specified song URL."""
    try:
        browser.wait_until_element_is_visible('id:lyric-body-text', timeout=10)
        return browser.find_element('id:lyric-body-text').text.strip()
    except Exception as e:
        LOGGER.error(f"Error retrieving lyrics: {e}")
        return None
    
def translate_lyrics(lyrics):
    """Translates lyrics to Vietnamese."""
    try:
        return GoogleTranslator(source='auto', target='vi').translate(lyrics)
    except Exception as e:
        LOGGER.error(f"Error translating lyrics: {e}")
        return lyrics

def save_lyrics_to_file(lyrics_text, song_title):
    """Saves lyrics to a file with the specified title."""
    file_path = os.path.join(os.getcwd(), f'{song_title}.txt')
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(lyrics_text)
        # args.set_out_arg('trans_song', file_path)
        LOGGER.info(f"Lyrics saved to {file_path}")
    except Exception as e:
        LOGGER.error(f"Error saving lyrics to file: {e}")

################################################################
# Helper functions
def enter_text_in_element(selector, text):
    """Click elements and enter input"""
    try:
        browser.click_element_when_visible(selector)
        time.sleep(0.5)
        windows.send_keys(text)
    except Exception as e:
        LOGGER.error(f"Error interacting with element {selector}: {e}")
        raise