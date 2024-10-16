from robocorp.tasks import task
from RPA.HTTP import HTTP
from RPA.Excel.Files import Files
from RPA.Tables import Tables
from RPA.Browser.Selenium import Selenium
from RPA.PDF import PDF
from PIL import Image
from RPA.Assistant import Assistant
import time, os
from deep_translator import GoogleTranslator
import validators

LYRICS_URL = 'https://www.lyrics.com/'
RETRIES_COUNT = 4
browser = Selenium()
assistant = Assistant()
@task
def get_browser():
    """Opens a new browser window."""
    try: 
        browser.open_available_browser(LYRICS_URL)
        login_choice = show_guest_or_login()
        if login_choice == 'Login':
            login()
        else:
            print("Continuing as Guest")
            
        get_lyrics()
    except Exception as e:
        print(f"Error opening browser: {e}")
        return False

################################################################
# LOGIN
def show_guest_or_login():
    assistant.add_heading("Choose mode")
    assistant.add_radio_buttons(
        name = "Mode",
        options = ["Guest", "Login"],
        default="Guest",
        label= "Mode"
    )
    assistant.add_submit_buttons('Submit')
    choice = assistant.run_dialog()
    print(choice)
    return choice.get('Mode')    

def login_form():
    """Requests user input."""
    assistant.add_heading('Login')
    assistant.add_text_input('username', 'username', 'Enter username')
    assistant.add_password_input(
        name='password', 
        label='password', 
        placeholder='Enter password'
    )
    assistant.add_submit_buttons('Login')
    return assistant.run_dialog()

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
        form_data = login_form()
        username, password = form_data.get('username'), form_data.get('password')
        
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
    song_name_or_url = search_form().get('song_name_or_url')
    title = None 
    song_selected = None 

    if not validators.url(song_name_or_url):
        browser.input_text('css:input#search.ui-autocomplete-input', song_name_or_url)
        browser.click_element('css:button#page-word-search-button')
        browser.wait_until_element_is_visible('class:best-matches', timeout=10)

        song_list = get_song_list()
        song_selected = display_song_list(song_list)

        if song_selected:
            browser.go_to(song_selected['url'])
            title = song_selected.get('title', None)
    else:
        browser.go_to(song_name_or_url)
        browser.wait_until_element_is_visible('css:h1#lyric-title-text.lyric-title', timeout=10)
        title_element = browser.find_element('css:h1#lyric-title-text.lyric-title')
        title = title_element.text
    lyrics = get_lyrics_from_song()
    if lyrics:
        final_title = song_selected['title'] if song_selected else title
        translated_lyrics = translate_lyrics(lyrics)
        save_lyrics_to_file(translated_lyrics, final_title)
    else:
        print("Lyrics not found.")

def search_form():
    assistant.add_heading("Search for names...")
    assistant.add_text_input("song_name_or_url", "URL/Song name", "Enter song name or URL to search")
    assistant.add_submit_buttons("Search")
    song_name_or_url = assistant.run_dialog()
    return song_name_or_url

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

def display_song_list(song_list):
    assistant.add_heading("Choose a song from the list")
    song_options = []
    for song in song_list:
        option_label = f"{song['title']} by {song['artist_name']}"
        song_options.append(option_label)
        assistant.add_text(f"Album: {song['album_title']}")
        assistant.add_text(f"Artist: {song['artist_name']}")
        if song.get('image_url'):
            assistant.add_image(url_or_path=song['image_url'], width=100, height=100)

    assistant.add_radio_buttons(
        name='selected_song',
        options=song_options,
        label="Select a song to retrieve lyrics"
    )
    assistant.add_submit_buttons("Submit")
    selected_song_label = assistant.run_dialog().get('selected_song')

    for song in song_list:
        if f"{song['title']} by {song['artist_name']}" == selected_song_label:
            return song
    return None

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
