from robocorp.tasks import task
from RPA.Excel.Files import Files
import time, os, sys
from deep_translator import GoogleTranslator
import validators
from DOP.RPA.Asset import Asset
from DOP.RPA.ProcessArgument import ProcessArgument
import logging
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyautogui as autogui

# Constants
LYRICS_URL = 'https://www.lyrics.com/'
RETRIES_COUNT = 4

# Initialize components
assets = Asset()
args = ProcessArgument()
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

# Browser setup
browser = None

@task
def main():
    global browser
    try:
        browser = get_browser()
        if check_login():
            attempt_login()
        get_lyrics()
    except Exception as e:
        LOGGER.error(f"Error when running task: {e}")
    finally:
        if browser:
            browser.quit()
    
def get_browser():
    """Opens a new browser window using Selenium WebDriver."""
    try:
        driver = webdriver.Chrome()  
        driver.get(LYRICS_URL)
        return driver
    except Exception as e:
        LOGGER.error(f"Error opening browser: {e}")
        raise SystemError(f"Error opening browser: {e}")

################################################################
# Helper functions
def wait_for_element(by, selector, timeout=10):
    """Waits until the element is visible or throws TimeoutException."""
    try:
        element = WebDriverWait(browser, timeout).until(
            EC.visibility_of_element_located((by, selector))
        )
        return element
    except Exception as e:
        LOGGER.error(f"Error waiting for element {selector}: {e}")
        return None

def enter_text_in_element(by, selector, text):
    """Click elements and enter input using pyautogui"""
    try:
        element = wait_for_element(by, selector)
        if element:
            element.click()
            time.sleep(0.5)
            autogui.typewrite(text,interval=0.1)
    except Exception as e:
        LOGGER.error(f"Error interacting with element {selector}: {e}")
        raise

################################################################
# LOGIN
def check_login():
    """Checks if the user is already logged in."""
    try:
        element = wait_for_element(By.ID, "user-login")
        return bool(element)
    except:
        return False

def perform_login(username, password):
    """Performs login using provided username and password."""
    try:
        login_button = wait_for_element(By.ID, "user-login")
        if login_button:
            login_button.click()
            time.sleep(1)
            enter_text_in_element(By.CSS_SELECTOR, "#fld-uname.fw", username)
            enter_text_in_element(By.CSS_SELECTOR, "#fld-upass.fw", password)
            submit_button = wait_for_element(By.CSS_SELECTOR, "button[type=submit].lrg")
            if submit_button:
                submit_button.click()
    except Exception as e:
        LOGGER.error(f"Error performing login: {e}")
        raise LoginError("Login attempt failed")
    
def attempt_login():
    """Attempts to login with retries if login fails."""
    retries = 0
    while retries < RETRIES_COUNT:
        username = assets.get_asset("username")['value']
        password = assets.get_asset("password")['value']
        if not username or not password:
            LOGGER.debug("Login cancelled due to missing credentials.")
            raise LoginError("Login cancelled by user")

        try:
            perform_login(username, password)
            if not wait_for_element(By.CSS_SELECTOR, "p.err"):
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
        song_name = assets.get_asset("song_name")['value']
        enter_text_in_element(By.CSS_SELECTOR, 'input#search.ui-autocomplete-input', song_name)
        search_button = wait_for_element(By.CSS_SELECTOR, 'button#page-word-search-button')
        if search_button:
            search_button.click()
        time.sleep(2)

        song_list = get_song_list()
        if not song_list:
            LOGGER.warning("No songs found.")
            return

        song_selected = song_list[0]
        if song_selected:
            browser.get(song_selected['url'])

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
        song_elements = wait_for_element(By.CSS_SELECTOR, ".best-matches .bm-case")
        if song_elements:
            song_elements = browser.find_elements(By.CSS_SELECTOR, ".best-matches .bm-case")
            for song in song_elements:
                song_title_element = song.find_element(By.CSS_SELECTOR, ".bm-label a")
                song_url = song_title_element.get_attribute("href")
                album_elements = song.find_elements(By.CSS_SELECTOR, ".bm-label b a")
                artist_element = song.find_elements(By.CSS_SELECTOR, ".bm-label a")[-1]
                song_list.append({
                    "title": song_title_element.text.strip(),
                    "url": song_url,
                    "image_url": song.find_element(By.CSS_SELECTOR, ".album-thumb img").get_attribute("src"),
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
        lyrics_element = wait_for_element(By.ID, "lyric-body-text")
        if lyrics_element:
            return lyrics_element.text.strip()
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
        LOGGER.info(f"Lyrics saved to {file_path}")
    except Exception as e:
        LOGGER.error(f"Error saving lyrics to file: {e}")
