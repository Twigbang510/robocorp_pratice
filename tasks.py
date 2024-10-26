from robocorp.tasks import task
from RPA.HTTP import HTTP
from RPA.Excel.Files import Files
from RPA.Tables import Tables
from RPA.Browser.Selenium import Selenium
from RPA.PDF import PDF
from PIL import Image
import time, os
from deep_translator import GoogleTranslator
import validators
from DOP.RPA.Asset import Asset

LYRICS_URL = 'https://www.lyrics.com/'
RETRIES_COUNT = 4
browser = Selenium()
assets = Asset()

@task
def get_browser():
    """Opens a new browser window."""
    try: 
        browser.open_available_browser(LYRICS_URL)
        if check_login():
            login()
        get_lyrics()
    except Exception as e:
        print(f"Error opening browser: {e}")
        return False

################################################################
# LOGIN
def check_login():
    """Checks if the user is already logged in."""
    return browser.is_element_visible("id:user-login")

def perform_login(username, password):
    """Performs login using provided username and password."""
    browser.click_element("id:user-login")
    time.sleep(1)
    browser.input_text_when_element_is_visible("css:#fld-uname.fw", username)
    browser.input_text_when_element_is_visible("css:#fld-upass.fw", password)
    browser.click_element("css:button[type=submit].lrg")

def login():
    retries = 0
    while retries < RETRIES_COUNT:
        # Get login credentials from user
        assets_data = assets.get_asset('lyrics_user').get('value')
        
        username, password = assets_data.get('username'), assets_data.get('password')
        
        if not username or not password:
            print("Login cancelled")
            return False
        
        # Perform login
        perform_login(username, password)

        # Check if there is an error message indicating failed login
        if not browser.is_element_visible("css:p.err"):
            return True  # Login successful

        print("Login failed. Retrying...")
        retries += 1

    print("Max retries reached. Login failed.")
    return False

################################################################
# GET LYRICS FROM INPUT
def get_lyrics():
    """Navigates to the Lyrics.com search page and retrieves lyrics for a specified song."""
    title = None 
    assets_data = assets.get_asset('lyrics_user').get('value')

    browser.input_text('css:input#search.ui-autocomplete-input', assets_data.get('song_name'))
    browser.click_element('css:button#page-word-search-button')
    browser.wait_until_element_is_visible('class:best-matches', timeout=10)

    song_list = get_song_list()
    song_selected = song_list[0]
    if song_selected:
        browser.go_to(song_selected['url'])
        title = song_selected.get('title', None)

    lyrics = get_lyrics_from_song()
    if lyrics:
        final_title = song_selected['title'] if song_selected else title
        translated_lyrics = translate_lyrics(lyrics)
        save_lyrics_to_file(translated_lyrics, final_title)
    else:
        print("Lyrics not found.")

def get_song_list():
    song_list = []
    song_elements = browser.find_elements("css:.best-matches .bm-case")
    for song in song_elements:
        song_title_element = song.find_element("css selector", ".bm-label a")
        song_title = song_title_element.text.strip()
        song_url = song_title_element.get_attribute("href")

        image_element = song.find_element("css selector", ".album-thumb img")
        image_url = image_element.get_attribute("src") if image_element else None

        album_elements = song.find_elements("css selector", ".bm-label b a")
        album_title = album_elements[1].text if len(album_elements) > 1 else "No album"

        artist_element = song.find_elements("css selector", ".bm-label a")[-1]
        artist_name = artist_element.text.strip()

        song_list.append({
            "title": song_title,
            "url": song_url,
            "image_url": image_url,
            "album_title": album_title,
            "artist_name": artist_name,
        })
    return song_list

def get_lyrics_from_song():
    """Retrieves lyrics from the specified song URL."""
    try:
        browser.wait_until_element_is_visible('id:lyric-body-text', timeout=10)
        lyrics_element = browser.find_element('id:lyric-body-text')
        lyrics = lyrics_element.text.strip()
        return lyrics
    except Exception as e:
        print(f"Error retrieving lyrics: {e}")
        return None
    
def translate_lyrics(lyrics):
    translated = GoogleTranslator(source='auto', target='vi').translate(lyrics)
    return translated

def save_lyrics_to_file(lyrics_text, song_title):
    """Saves lyrics to a file with the specified title."""
    file_name = f'{song_title}.txt'
    file_path = os.path.join(os.getcwd(), file_name)
    try:
        # Open the file in write mode and save the lyrics
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(lyrics_text)
        print(f"Lyrics saved to {file_path}")
    except Exception as e:
        print(f"Error saving lyrics to file: {e}")
