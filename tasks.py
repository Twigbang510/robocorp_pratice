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
        browser_engine='msedge',
        headless = False,
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
    pass
    

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
 
