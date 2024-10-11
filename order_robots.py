from robocorp.tasks import task
from robocorp import browser
from RPA.HTTP import HTTP
from RPA.Excel.Files import Files
from RPA.Tables import Tables
from RPA.Browser.Selenium import Selenium
from RPA.PDF import PDF
from PIL import Image
from RPA.Assistant import Assistant
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
        'input[type="number"].form-control': 'Legs',
        'input[type="text"].form-control': 'Address'
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
        case 'input[type="number"].form-control' | 'input[type="text"].form-control':
            page.fill(selector,str(value))        
        case _:
            page.fill(selector, str(value))

def retry_on_error(page, retry_selector, max_retries=10):
    retry_count = 0
    while page.locator('.alert.alert-danger').is_visible() and retry_count < max_retries:
        print(f"Internal Server Error detected, retrying... Attempt {retry_count + 1}")
        page.click(retry_selector)
        time.sleep(1) 
        retry_count += 1

    if retry_count == max_retries:
        print("Max retries reached. Proceeding with caution.")

def merge_images_and_center(image_files, output_path, page_width=600):
    """Merge images from multiple images"""
    images = [Image.open(image) for image in image_files]

    heights = [img.height for img in images]
    total_height = sum(heights)
    
    merged_image = Image.new(
        'RGB', 
        (page_width, total_height), 
        (255, 255, 255) #white background
    ) 

    y_offset = 0
    for img in images:
        x_offset = (page_width - img.width) // 2
        
        merged_image.paste(img, (x_offset, y_offset))
        y_offset += img.height

    # Save the merged image
    merged_image.save(output_path)

def generate_pdf(order_id, order_details_html, image_files, folder_path):
    """Generates PDF for a given order details page and image files"""
    merged_image_path = f"{folder_path}/merged_robot_image_{order_id}.png"
    merge_images_and_center(image_files, merged_image_path)

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

def get_order_details(page, order_id):
    # Get the order details in HTML format
    order_details = page.locator('#receipt').inner_html()

    folder_path = 'order_images'
    robot_images = download_images_from_div(page, folder_path)

    generate_pdf(order_id, order_details, robot_images, folder_path)
    
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
