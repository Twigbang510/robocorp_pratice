from robocorp.tasks import task
from robocorp import browser
from RPA.HTTP import HTTP
from RPA.Excel.Files import Files
from RPA.Tables import Tables
from RPA.Browser.Selenium import Selenium
from RPA.PDF import PDF
import time, os
@task
def order_robots():
    """Automates the ordering process of a robot using data from a CSV file and exports the images as a PDF."""
    browser.configure(
        # browser_engine='msedge',
        slowmo=100,
    )
    page = open_the_intranet_website("https://robotsparebinindustries.com/#/robot-order")
    open_csv(page, "orders.csv")

def open_the_intranet_website(url):
    """Opens the intranet website using the configured browser and returns the page object."""
    browser.goto(url)
    return browser.page()

def click_modal(page):
    page.click(".modal-body .alert-buttons .btn-dark")
    print("Clicked the modal button")

def open_csv(page, file_path):
    excel = Tables()
    csv_data = excel.read_table_from_csv(file_path, header=True)
    
    for i, row in enumerate(csv_data):
        click_modal(page)
        print(f"Processing row {i}: {row}")
        fill_order(page, row)
        page.click('#order-another')
        retry_on_error(page, "#order-another")

def fill_order(page, row):
    fields = {
        'custom-select': 'Head',
        'radio_body': 'Body', 
        'Enter the part number for the legs': 'Legs',
        'Shipping address': 'Address'
    }
    order_id = row.get('Order number', '')
    
    for selector, field in fields.items():
        handle_field(page, selector, row.get(field, ''))
    
    page.click('#order')
    retry_on_error(page, '#order')
    time.sleep(1)
    get_order_details(page, order_id)

def handle_field(page, selector, value):
    if not value:
        return
    match selector:
        case 'custom-select':
            page.locator(f".{selector}").select_option(str(value))
        case 'radio_body':
            try:
                page.click(f"input[type='radio'][name='body'][value='{value}']")
            except Exception as e:
                print(f"Error selecting radio button with value '{value}': {e}")
        case 'Enter the part number for the legs' | 'Shipping address':
            page.get_by_placeholder(selector).fill(str(value))
        case _:
            page.fill(selector, str(value))

def retry_on_error(page, retry_selector, max_retries=5):
    retry_count = 0
    while page.locator('.alert.alert-danger').is_visible() and retry_count < max_retries:
        print(f"Internal Server Error detected, retrying... Attempt {retry_count + 1}")
        page.click(retry_selector)
        time.sleep(1) 
        retry_count += 1

    if retry_count == max_retries:
        print("Max retries reached. Proceeding with caution.")

def get_order_details(page, order_id):
    order_details = page.locator('#receipt').inner_html()
    folder_path = 'order_images'
    robot_images = download_images_from_div(page, folder_path)
    pdf = PDF()
    pdf.html_to_pdf(order_details, f"order_details/{order_id}.pdf")
    pdf.add_files_to_pdf(robot_images, f"order_details/{order_id}.pdf", append=True)

def download_images_from_div(page, folder_path, div_id='robot-preview-image'):
    os.makedirs(folder_path, exist_ok=True)
    image_elements = page.locator(f'#{div_id} img').all()
    print(f"Downloading {len(image_elements)} images")
    http = HTTP()
    downloaded_images = []

    for i, img in enumerate(image_elements):
        src = img.get_attribute('src')
        if src:
            image_name = os.path.join(folder_path, f"robot_part_{i}.png")
            http.download(f'https://robotsparebinindustries.com{src}', image_name, overwrite=True) 
            downloaded_images.append(image_name)

    return downloaded_images
