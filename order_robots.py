from robocorp.tasks import task
from RPA.HTTP import HTTP
from RPA.Excel.Files import Files
from RPA.Tables import Tables
from RPA.Browser.Selenium import Selenium
from RPA.PDF import PDF
from PIL import Image
from RPA.Assistant import Assistant
import time, os

# Initialize the Selenium browser object
browser = Selenium()

@task
def order_robots():
    """Automates the robot ordering process from a CSV file and exports images as a PDF."""
    browser.open_available_browser("https://robotsparebinindustries.com/#/robot-order", headless=False)
    process_orders_from_csv("orders.csv")
    browser.close_browser()

def process_orders_from_csv(file_path):
    """Reads the CSV file and processes each row to fill in the robot order form."""
    tables = Tables()
    csv_data = tables.read_table_from_csv(file_path, header=True)

    for i, row in enumerate(csv_data):
        click_modal()
        print(f"Processing row {i}: {row}")
        fill_order_form(row)
        browser.click_element("id:order-another")
        retry_on_error("id:order-another")
        time.sleep(1)

def fill_order_form(row):
    """Fills the robot order form with data from the CSV and submits the form."""
    fields = {
        'class:custom-select': 'Head',
        'class:radio_body': 'Body',
        'css:input[type="number"].form-control': 'Legs',
        'css:input[type="text"].form-control': 'Address'
    }
    
    order_id = row.get('Order number', '')

    for selector, field in fields.items():
        input_field_value(selector, row.get(field, ''))

    browser.click_element('id:order')
    retry_on_error('id:order')
    time.sleep(1)
    generate_order_details(order_id)

def input_field_value(selector, value):
    """Inputs or selects values for a specific form field."""
    if not value:
        return

    if selector == 'class:custom-select':
        browser.select_from_list_by_value(selector, str(value))
    elif selector == 'class:radio_body':
        try:
            browser.click_element(f"css:input[type='radio'][name='body'][value='{value}']")
        except Exception as e:
            print(f"Error selecting radio button with value '{value}': {e}")
    else:
        browser.input_text(selector, str(value))

def retry_on_error(retry_selector, max_retries=10):
    """Retries the action if there is an internal server error."""
    retry_count = 0
    while browser.is_element_visible('css:.alert.alert-danger') and retry_count < max_retries:
        print(f"Internal Server Error detected, retrying... Attempt {retry_count + 1}")
        browser.click_element(retry_selector)
        time.sleep(1)
        retry_count += 1

    if retry_count == max_retries:
        print("Max retries reached. Proceeding with caution.")

def generate_order_details(order_id):
    """Retrieves order details and generates a PDF report."""
    browser.wait_until_element_is_visible("id:receipt", timeout=10)
    order_details_html = browser.get_element_attribute('id:receipt', 'innerHTML')
    
    folder_path = 'order_images'
    robot_images = download_robot_images(folder_path)

    generate_order_pdf(order_id, order_details_html, robot_images, folder_path)

def download_robot_images(folder_path, div_id='robot-preview-image'):
    """Downloads robot images and saves them to the specified folder."""
    os.makedirs(folder_path, exist_ok=True)
    image_elements = browser.find_elements(f'css:#{div_id} img')

    http = HTTP()
    downloaded_images = []

    for i, img in enumerate(image_elements):
        src = browser.get_element_attribute(img, 'src')
        if src:
            image_path = os.path.join(folder_path, f"robot_part_{i}.png")
            http.download(src, image_path, overwrite=True)
            downloaded_images.append(image_path)

    return downloaded_images

def generate_order_pdf(order_id, order_details_html, image_files, folder_path):
    """Generates a PDF for the order, including the robot images and details."""
    merged_image_path = os.path.join(folder_path, f"merged_robot_image_{order_id}.png")
    merge_images(image_files, merged_image_path)

    html_content = f"""
    <html>
    <body>
        <h1>Order Details: {order_id}</h1>
        {order_details_html}
        <img src="{merged_image_path}" style="width:100%;">
    </body>
    </html>
    """

    pdf = PDF()
    pdf.html_to_pdf(html_content, f"order_details/{order_id}.pdf")

def merge_images(image_files, output_path, page_width=600):
    """Merges multiple images vertically and centers them on a white background."""
    images = [Image.open(img) for img in image_files]
    total_height = sum(img.height for img in images)

    merged_image = Image.new('RGB', (page_width, total_height), (255, 255, 255))

    y_offset = 0
    for img in images:
        x_offset = (page_width - img.width) // 2
        merged_image.paste(img, (x_offset, y_offset))
        y_offset += img.height

    merged_image.save(output_path)

def click_modal():
    """Clicks the modal button to proceed with the order form."""
    browser.click_element("css:.btn-dark")
    print("Clicked the modal button")
