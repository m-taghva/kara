import argparse
import re
import os
import pywikibot
from bs4 import BeautifulSoup
import logging
import subprocess
import csv

#### make HTML template ####
def dict_to_html(dict):
    html_dict = "<table border='1' class='wikitable'>\n"
    html_dict += "<tr><th>product_name</th><th>servers</th></tr>\n"
    for key, value in dict.items():
        html_dict += f"<tr><td>{key}</td><td>{value}</td></tr>\n"
    html_dict += "</table>"
    return html_dict

def csv_to_html(csv_file):
    html_csv = "<table border='1' class='wikitable'>\n"
    with open(csv_file, 'r') as file:
        for i, row in enumerate(csv.reader(file)):
            html_csv += "<tr>\n"
            tag = "th" if i == 0 else "td"
            for column in row:
                html_csv += f"<{tag}>{column}</{tag}>\n"
            html_csv += "</tr>\n"
    html_csv += "</table>"
    return html_csv

def create_html_template(template_content, html_output):
    logging.info("Executing report_recorder create_html_template function")
    html_data = template_content # for replace placeholder with content of files
    # Find all occurrences of {input_config} placeholders in the template
    for match in re.finditer(r'{input_config}:(.+)', template_content):
        # Iterate over the placeholders and replace them with content
        placeholder = match.group(0)
        file_path = match.group(1).strip()
        if '.csv' in os.path.basename(file_path):
            html_csv = csv_to_html(file_path) 
            html_data = html_data.replace(placeholder, html_csv)
        else:
            with open(file_path, 'r') as file:
                content_of_file = file.readlines()
            html_content = ""
            for content_line in content_of_file:
                html_content += f"<p>{content_line.replace(' ','&nbsp;')}</p>"
            html_data = html_data.replace(placeholder, html_content)
    with open(html_output, 'w') as html_file:
        html_file.write(html_data)
        print(f"HTML template saved to: {html_output}")  
    return html_data

#### upload data and make wiki page ####
def upload_data(site, title, content):
    logging.info("Executing report_recorder upload_data function")
    try:
        page = pywikibot.Page(site, title)
        page.text = content
        page.save("Uploaded data using Pywikibot")
        logging.info(f"Page '{title}' uploaded successfully.")
    except pywikibot.exceptions.Error as e:
        logging.error(f"Error uploading page '{title}': {e}")

def convert_html_to_wiki(html_content):
    logging.info("Executing report_recorder convert_html_to_wiki function")
    soup = BeautifulSoup(html_content, 'html.parser')
    # Convert <a> tags to wiki links
    for a_tag in soup.find_all('a'):
        if 'href' in a_tag.attrs:
            a_tag.replace_with(f"[{a_tag['href']}|{a_tag.text}]")
    # Convert <img> tags to wiki images
    for img_tag in soup.find_all('img'):
        if 'src' in img_tag.attrs:
            img_tag.replace_with(f"[[File:{img_tag['src']}]]")
    return str(soup)

def upload_images(site, html_file_path):
    logging.info("Executing report_recorder upload_images function")
    with open(html_file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')
    # Find image filenames in <img> tags
    image_filenames = [img['src'] for img in soup.find_all('img') if 'src' in img.attrs]
    # Upload each image to the wiki
    for image_filename in image_filenames:
        image_path = os.path.join(os.path.dirname(html_file_path), image_filename)
        page = pywikibot.FilePage(site, f'File:{image_filename}')
        if not page.exists():
            # Create a FilePage object
            file_page = pywikibot.FilePage(site, page.title())
            # Check if the file already exists
            if file_page.exists():
                raise ValueError("File already exists!")
            # Upload the file
            success = file_page.upload(image_path, comment=f"Uploaded image '{image_filename}' using Pywikibot")
            if success:
                print(f"File uploaded successfully! File page: {file_page.full_url()}")
            else:
                print("Upload failed.")
            logging.info(f"Image '{image_filename}' uploaded successfully.")
        else:
            logging.warning(f"Image '{image_filename}' already exists on the wiki.")

def main(input_template, html_output, page_title, html_page, upload_operation, create_html):
    log_dir = f"sudo mkdir /var/log/kara/ > /dev/null 2>&1 && sudo chmod -R 777 /var/log/kara/"
    log_dir_run = subprocess.run(log_dir, shell=True)
    logging.basicConfig(filename= '/var/log/kara/all.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("\033[92m****** report_recorder main function start ******\033[0m")
    if create_html:
        with open(input_template, 'r') as template_content:
            # Create HTML template
            create_html_template(template_content.read(), html_output)
    if upload_operation:
        # Set up the wiki site
        site = pywikibot.Site()
        site.login()
        with open(html_page, 'r', encoding='utf-8') as file:
            html_content = file.read()
        wiki_content = convert_html_to_wiki(html_content)
        # Upload converted data to the wiki
        upload_data(site, page_title, wiki_content)
        # Upload images to the wiki
        upload_images(site, html_page)
    logging.info("\033[92m****** report_recorder main function end ******\033[0m")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate report for kateb")
    parser.add_argument("-i", "--input_template", help="Template HTML file path.")
    parser.add_argument("-o", "--html_output", help="Output HTML file name")
    parser.add_argument("-p", "--html_page", help="HTML template for upload")
    parser.add_argument("-t", "--page_title", help="Kateb page title.")
    parser.add_argument("-U", "--upload_operation", action='store_true', help="upload page to kateb")
    parser.add_argument("-H", "--create_html", action='store_true', help="create HTML page template")
    args = parser.parse_args()
    if args.upload_operation and (args.html_page is None or args.page_title is None):
        print("Error: Both -p (--html_page) and -t (--page_title) switches are required for upload operation -U")
        exit(1)
    if args.create_html and (args.input_template is None or args.html_output is None):
        print("Error: Both -i (--input_template) and -o (--html_output) switches are required for generate HTML operation -H")
        exit(1)
    input_template = args.input_template 
    html_output = args.html_output
    page_title = args.page_title 
    html_page = args.html_page
    upload_operation = args.upload_operation
    create_html = args.create_html
    main(input_template, html_output, page_title, html_page, upload_operation, create_html)
