from robocorp.tasks import task
from robocorp import browser
from RPA.HTTP import HTTP
from RPA.Excel.Files import Files
from RPA.Tables import Tables
from RPA.Browser.Selenium import Selenium
from RPA.PDF import PDF
import time, os
@task
def insert_data_to_form():
    """Automates data insertion into a web form using data from an Excel file, captures screenshots, and exports the images as a PDF."""
    
    # Configure the browser to use 'msedge' with a slow-motion effect to simulate human-like interaction.
    browser.configure(
        # browser_engine='msedge',
        slowmo=100,
    )
    
    #Open the target intranet website.
    page = open_the_intranet_website("https://www.rpachallenge.com/")
    
    # Ensure 'images' directory exists
    os.makedirs('images', exist_ok=True)
    
    # Read data from the Excel file and fill the web form with each row of data.
    fill_form_with_excel_data(page)
    
    # Export captured screenshots as a single PDF document.
    export_pdf()
    

def open_the_intranet_website(url):
    """Opens the intranet website using the configured browser and returns the page object."""
    browser.goto(url)
    return browser.page()

def download_excel_file(url, filename):
    """Downloads an Excel file from a specified URL."""
    http = HTTP()
    http.download(url, filename)

def fill_form_with_excel_data(page):
    """Reads data from an Excel file and fills the web form for each row."""
    excel = Files()
    try:
        # Open the Excel workbook once
        excel.open_workbook("challenge.xlsx")
        worksheet = excel.read_worksheet_as_table("data", header=True)
        
        # Iterate through each row in the worksheet and fill the form
        for i, row in enumerate(worksheet):
            print(f"Processing row {i}: {row}")
            fill_form(page, row)
    finally:
        # Always close the workbook
        excel.close_workbook()

def fill_form(page, row):
    """Fills the web form with data from a single row of the Excel worksheet and takes a screenshot."""
    # Define form field names that correspond to both Excel keys and the form element names
    fields = {
        'labelAddress': 'Address',
        'labelFirstName': 'First Name',
        'labelEmail': 'Email',
        'labelPhone': 'Phone Number',
        'labelRole': 'Role in Company',
        'labelCompanyName': 'Company Name',
        'labelLastName': 'Last Name'
    }
    
    try:
        # Fill each form field using the data from the row
        for field_name, key in fields.items():
            selector = f"[ng-reflect-name='{field_name}']"
            page.fill(selector, str(row.get(key, '')))
        
        # Take a screenshot of the form filled with the current row's data
        screenshot_path = f"images/{row.get('First Name', 'unknown')}.png"
        page.screenshot(path=screenshot_path)
        
        # Attempt to click the submit button
        page.click(".btn.uiColorButton")
        time.sleep(1)  # Wait for a second to allow the form to process
    except Exception as e:
        print(f"Error during form filling: {e}")

def export_pdf():
    """Combines all screenshots in the 'images' directory into a single PDF document."""
    pdf = PDF()
    
    # Get a list of all image files in the 'images' directory with specified extensions
    image_files = [os.path.join('images', file) for file in os.listdir('images') if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))]
    
    # Add the image files to a new PDF document and save it with the specified name
    if image_files:  # Ensure there are images to add
        pdf.add_files_to_pdf(image_files, 'output_pdf.pdf')
    else:
        print("No images found to add to the PDF.")
 
@task
def order_robots():
    """Automates the ordering process of a robot using data from a CSV file and exports the images as a PDF."""
    browser.configure(
        browser_engine='msedge',
        slowmo=100,
    )
    page = open_the_intranet_website("https://robotsparebinindustries.com/#/robot-order")
    open_csv(page, "orders.csv")

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
