import argparse
import re
import os
import yaml
import logging
import csv
import subprocess
import sys
import pandas as pd
from bs4 import BeautifulSoup
from dataclasses import dataclass
import dominate
from dominate.tags import *
from dominate.util import raw
from dominate.document import document
pywiki_path = os.path.abspath("./../report_recorder/pywikibot/")
if pywiki_path not in sys.path:
    sys.path.append(pywiki_path)
import pywikibot
import analyzer
  
# variables
config_file = "/etc/kara/report_recorder.conf"
kateb_url = "https://kateb.burna.ir/wiki/"
log_path = "/var/log/kara/"

pageNameDelimiter = "; "
valueDelimiter = ","
timeColumn = "cosbench.run_time"

@dataclass
class subdf:
    subcsv: pd.core.frame.DataFrame
    csvinfo: dict
    bestColumnforDivider: str
    dividerNumber: int
    l: int
    value: str

@dataclass
class subPage:
    text: str
    columnName: str
    subcsv: dict
    summarycsv: pd.core.frame.DataFrame

def load_config(config_file):
    with open(config_file, "r") as stream:
        try:
            data_loaded = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(f"Error loading the configuration: {exc}")
            sys.exit(1)
    return data_loaded

#### make HTML template ####
def dict_html_software(data, confType):
    logging.info("report_recorder - Executing dict_html_software function")
    html = "<table border='1' class='wikitable'>\n"
    html += "<tr>\n"
    html += f"<td>servers</td>\n"
    if isinstance(data["servers"], list):
        for item in data["servers"]:
            html += f"<td>{item}</td>\n"
    else:
        str = data["servers"]
        html += f"<td>{str}</td>\n"
    html += "</tr>\n"
    for key , value in data.items():
        if key != "servers":
            html += "<tr>\n"
            html += f"<td>{key}</td>\n"
            if confType != "swift_status":
                str = "<br>".join(value)
                html += f"<td>{str}</td>\n"
            else:
                for i in range(len(value)):
                    html += f"<td>{value[i]}</td>\n"
            html += "</tr>\n"
    html += "</table>"
    return html

def dict_html_hardware(dict):
    logging.info("report_recorder - Executing dict_to_html function")
    html_dict = "<table border='1' class='wikitable'>\n"
    html_dict += "<tr><th> نام سرور </th><th> مشخصات </th></tr>\n"
    for key, value in dict.items():
        if isinstance(value, list):
            value_str = '<br>'.join(value)
        else:
            value_str = str(value)
        html_dict += f"<tr><td>{value_str}</td><td>{key}</td></tr>\n"
    html_dict += "</table>"
    return html_dict

def csv_to_html(csv_file):
    logging.info("report_recorder - Executing csv_to_html function")
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

def create_sw_hw_htmls(template_content, html_output, page_title, data_loaded): #HW_page_title = cluster_name #SW_page_title = cluster_name + scenario_name
    logging.info("report_recorder - Executing create_sw_hw_htmls function")
    htmls_dict={}
    hw_info_dict = {}
    html_data = template_content.replace("{title}",f"{page_title}") # for replace placeholder with title in page url
    for match in re.finditer(r'{input_config}:(.+)', template_content):
        # Iterate over the placeholders and replace them with content
        address_placeholder = match.group(0)
        file_path = match.group(1).strip()
        logging.info(f"report_recorder - path of input file inside input html:{file_path}")
        if '{backup_dir}' in file_path:
            file_path = file_path.replace('{backup_dir}', configs_dir)
        if '.csv' in os.path.basename(file_path):
            html_csv = csv_to_html(file_path) 
            html_data = html_data.replace(address_placeholder, html_csv)
        else:
            with open(file_path, 'r') as file:
                content_of_file = file.readlines()
            html_content = ""
            for content_line in content_of_file:
                html_content += f"<p>{content_line.replace(' ','&nbsp;')}</p>"
            html_data = html_data.replace(address_placeholder, html_content)
    for hconfig_info in re.finditer(r'{hw_config}:(.+)', template_content):
        hconfig_placeholder = hconfig_info.group(0)
        part,spec = hconfig_info.group(1).split(',')
        logging.info(f"report_recorder - name of hardware part inside input html:{part,spec}")
        dict = analyzer.compare(part.strip(), spec.strip())
        hw_info_dict.update({spec.strip():dict})
        html_of_dict = dict_html_hardware(dict)
        html_data = html_data.replace(hconfig_placeholder, html_of_dict)
    for sconfig_info in re.finditer(r'{sw_config}:(.+)', template_content):
        sconfig_placeholder = sconfig_info.group(0)
        sconfigs = sconfig_info.group(1).split(',')
        logging.info(f"report_recorder - name of software part inside input html:{sconfigs}")
        if sconfigs[0] == "swift_status":
            software_html = dict_html_software(analyzer.generate_all_swift_status(sconfigs[1]),sconfigs[0])
        else:
            software_html = dict_html_software(analyzer.generate_confs(sconfigs[0],None if len(sconfigs)== 1 else sconfigs[1]),sconfigs[0])
        html_data = html_data.replace(sconfig_placeholder, software_html)
    html_data += "<p> </p>"
    html_data += data_loaded['naming_tag'].get('tags')
    logging.info(f"report_recorder - wiki tag for all htmls:{data_loaded['naming_tag'].get('tags')}")
    htmls_dict.update({page_title:html_data})
    htmls_dict.update(sub_pages_maker(html_data,page_title,hw_info_dict,data_loaded))
    for html_key,html_value in htmls_dict.items():
        with open(os.path.join(html_output+"/"+html_key+".html"), 'w') as html_file:
            html_file.write(html_value)
            print(f"HTML template saved to: {html_output+'/'+html_key+'.html'}") 
            logging.info(f"report_recorder - HTML template saved to: {html_output+'/'+html_key+'.html'}")
    return htmls_dict

# Function to create subdf for each unique value in a column
def createcsvinfo(subdfinstance):
    for column_name in subdfinstance.subcsv.columns:
        unique_values = subdfinstance.subcsv[column_name].unique()
        subdfs = []
        maxl = 0
        for value in unique_values:
            subcsv = subdfinstance.subcsv[subdfinstance.subcsv[column_name] == value].drop(columns=[column_name])
            notMerged = 1
            for i in range(len(subdfs)):
                if subdfs[i].l+len(subcsv) <=testPerPageLimit:
                    concatcsv = pd.concat([subdfs[i].subcsv,subcsv])
                    new_subdf = subdf(subcsv = concatcsv, csvinfo={}, bestColumnforDivider = None, dividerNumber=len(concatcsv)+1, l=len(concatcsv), value=f"{subdfs[i].value}{valueDelimiter}{value}")
                    new_subdf.subcsv[column_name]= subdfinstance.subcsv[column_name]
                    subdfs[i] = new_subdf
                    notMerged = 0
                    break
            if notMerged:
                new_subdf = subdf(subcsv=subcsv, csvinfo={}, bestColumnforDivider = None, dividerNumber=len(subcsv)+1, l=len(subcsv), value=value)
                subdfs.append(new_subdf)
            if new_subdf.l>maxl:
                maxl = new_subdf.l
        subdfinstance.csvinfo[column_name] = subdfs
        if maxl <= testPerPageLimit and len(unique_values) < subdfinstance.dividerNumber:
            subdfinstance.dividerNumber = len(unique_values)
            subdfinstance.bestColumnforDivider = column_name

def divider(maindata):
    if not maindata.bestColumnforDivider:
        for key, subdf_list in maindata.csvinfo.items():
            currentDividerNumber = 0
            for index, item in enumerate(subdf_list):
                if item.l > testPerPageLimit:
                    createcsvinfo(maindata.csvinfo[key][index])
                    currentDividerNumber += divider(maindata.csvinfo[key][index])
                else:
                    currentDividerNumber += 1
            if currentDividerNumber < maindata.dividerNumber:
                maindata.dividerNumber = currentDividerNumber
                maindata.bestColumnforDivider = key
        return maindata.dividerNumber
    else:
        return maindata.dividerNumber

def createMainPageData(maindata,prefixstr=""):
    doclist = {}
    for item in maindata.csvinfo[maindata.bestColumnforDivider]:
        currentstr = f'{maindata.bestColumnforDivider}:{item.value}'
        if(item.bestColumnforDivider):
            doclist.update(createMainPageData(item,prefixstr+currentstr+pageNameDelimiter))
        else:
            doclist[prefixstr+currentstr] = item.subcsv
    return doclist

def createSubPageData(subPageData:subPage):
    # Convert each row to a tuple and count occurrences
    if not subPageData.summarycsv.empty:
        most_duplicated_count = subPageData.summarycsv.apply(tuple, axis=1).value_counts().max() # Count of the most duplicated row 
        if len(subPageData.summarycsv)-most_duplicated_count:
            subPageData.columnName = subPageData.summarycsv.nunique().idxmax()
            uniqueList = subPageData.summarycsv[subPageData.columnName].unique()
            subPageData.text = f"در این سند {len(uniqueList)} دسته تست شامل {subPageData.columnName} برابر با {uniqueList.tolist()} آورده شده است."
            for value in subPageData.summarycsv[subPageData.columnName].unique():
                subcsv = subPageData.summarycsv[subPageData.summarycsv[subPageData.columnName] == value].drop(columns=[subPageData.columnName])
                subPageData.subcsv[value] = subPage(text="", columnName=None, subcsv={}, summarycsv=subcsv)
                createSubPageData(subPageData.subcsv[value])
        else:
            subPageData.text = f"در این تست {subPageData.summarycsv.iloc[0].to_dict()} است."
            subPageData.summarycsv = subPageData.summarycsv.drop(columns=subPageData.summarycsv.columns)
            if most_duplicated_count > 1:
                subPageData.text += f"<br><b>توجه:</b> این تست {len(subPageData.summarycsv)} بار تکرار شده است."
    else:
        if len(subPageData.summarycsv) > 1:
            subPageData.text = f"<b>توجه:</b> این تست {len(subPageData.summarycsv)} بار تکرار شده است."
    subPageData.summarycsv[timeColumn]= infocsv[timeColumn]
    subPageData.summarycsv = pd.merge(subPageData.summarycsv, detailcsv, on=timeColumn)
    subPageData.summarycsv.columns = subPageData.summarycsv.columns.str.replace('.', '. ', regex=False)

def createSubPageHTML(subPageHTML:dominate.document, subPageData:subPage, heading_level=2):
    with subPageHTML:
        p(raw(subPageData.text), dir="rtl")
    if subPageData.columnName:
        for key,value in subPageData.subcsv.items():
            with subPageHTML:
                if heading_level<7:
                    heading_tag = getattr(dominate.tags, f'h{heading_level}')
                    heading_tag(f'{subPageData.columnName}:{key}', dir="rtl")
                else:
                    starLevel = "*"*(heading_level-6)
                    p(raw(f"<b>{starLevel} {subPageData.columnName}:{key}</b><br>"), dir="rtl")
            createSubPageHTML(subPageHTML, value, heading_level+1)
        with subPageHTML:
            if heading_level<7:
                heading_tag = getattr(dominate.tags, f'h{heading_level}')
                heading_tag(f'جمع‌بندی {subPageData.columnName}', dir="rtl")
            else:
                starLevel = "*"*(heading_level-6)
                p(raw(f"<b>{starLevel} جمع‌بندی {subPageData.columnName}</b><br>"), dir="rtl")
            with div():
                raw(subPageData.summarycsv.to_html(index=False, border=2))         
    else:
        with subPageHTML:
            with div():
                raw(subPageData.summarycsv.to_html(index=False, border=2))
    
def pageDataToHTML(clusterName,scenarioName,mainPageData): #return list of dominate.document
    #section 1
    #section 2
    pagesHTML = []
    mainPageHTML = dominate.document(title=f'{clusterName}--{scenarioName}')
    total_rows = sum(df.shape[0] for df in mainPageData.values())
    with mainPageHTML:
        p("برای مشاهده مشخصات سخت‌افزاری کلاستر به سند ",a(f'مشخصات سخت‌افزاری {clusterName}', href=f'./{clusterName}--HW.html', target='_blank'),"مراجعه کنید.",dir="rtl")
        p("برای مشاهده تنظیمات و مشخصات نرم‌افزاری کلاستر به سند ",a(f'مشخصات نرم‌افزاری سناریو {scenarioName} در کلاستر {clusterName}', href=f'./{clusterName}--{scenarioName}--SW.html', target='_blank'),"مراجعه کنید.",dir="rtl")
        h2("نتایج تست های کارایی", dir="rtl")
        p(raw(f"در این سناریو مجموعا <b>{total_rows}</b> تست وجود دارد که در <b>{len(mainPageData)}</b> دسته طبقه‌بندی شده‌اند. در ادامه هر دسته در یک بخش جداگانه آورده شده است."), dir="rtl")
    for pageName, pageData in mainPageData.items():
        subPageData = subPage(text="", columnName=None, subcsv={}, summarycsv=pageData)
        createSubPageData(subPageData)
        subPageHTML = dominate.document(title=f'{clusterName}--{scenarioName}--{pageName}')
        createSubPageHTML(subPageHTML, subPageData)
        pagesHTML.append(subPageHTML)
        pageData[timeColumn]= infocsv[timeColumn]
        with mainPageHTML:
            h2(pageName)
            p(raw(f"در این دسته مجموعا <b>{len(pageData)}</b> تست وجود دارد که در جدول زیر نشان داده شده‌ است:"), dir="rtl")
            with div():
                raw(pageData.to_html(index=False, border=2))
            a('نمایش جزئیات', href=f'./subpages/{clusterName}--{scenarioName}--{pageName}.html', target='_blank')
    pagesHTML.append(mainPageHTML)
    return pagesHTML
        
def createPagesHTML(clusterName,scenarioName): #return list of dominate.document
    global detailcsv,testPerPageLimit
    maindata = subdf(subcsv=infocsv.drop(columns=[timeColumn]),csvinfo={}, bestColumnforDivider = None, dividerNumber=len(infocsv)+1, l=len(infocsv), value=None)
    detailcsv = detailcsv.drop(columns=[col for col in infocsv.columns if col != timeColumn])
    # Convert each row to a tuple and count occurrences
    row_counts = maindata.subcsv.apply(tuple, axis=1).value_counts()
    most_duplicated_count = row_counts.max()   # Count of the most duplicated row
    if most_duplicated_count>testPerPageLimit:
        testPerPageLimit=most_duplicated_count
        print(f"Notice: The threshold has been automatically adjusted to {testPerPageLimit} to avoid errors.")
    createcsvinfo(maindata)
    divider(maindata)
    mainPageData = createMainPageData(maindata)
    pagesHTML = pageDataToHTML(clusterName,scenarioName,mainPageData)  
    return pagesHTML

infocsv = None
detailcsv = None
testPerPageLimit = None
def create_test_htmls(template_content, html_output, cluster_name, scenario_name, merged_file, merged_info_file, all_test_dir, data_loaded): #page_title = cluster_name + scenario_name
    global infocsv, detailcsv, testPerPageLimit
    logging.info("report_recorder - Executing create_test_htmls function")
    infocsv = pd.read_csv(merged_info_file)
    detailcsv = pd.read_csv(merged_file)
    testPerPageLimit = 12
    pagesHTML = createPagesHTML(cluster_name,scenario_name)
    if not os.path.exists(os.path.join(html_output+"/subpages")):
        os.mkdir(os.path.join(html_output+"/subpages"))
    for page in pagesHTML:
        pathPrefix = "subpages/"
        if page.title == f"{cluster_name}--{scenario_name}":
            pathPrefix = ""
        with open(os.path.join(html_output+"/"+pathPrefix+page.title+".html"), 'w') as html_file:
            html_file.write(page.render())
            print(f"HTML template saved to: {html_output+'/'+page.title+'.html'}") 
            logging.info(f"report_recorder - HTML template saved to: {html_output+'/'+page.title+'.html'}") 
    return pagesHTML

def sub_pages_maker(template_content , page_title ,hw_info_dict,data_loaded):
    logging.info("report_recorder - Executing sub_pages_maker function")
    global configs_dir
    htmls_list={}
    c_dir = configs_dir
    sub_dir_path = os.path.join(c_dir,'configs/{serverName}/hardware/')
    if page_title + "--CPU" in template_content:
        htmls_list.update({page_title + "--CPU":one_sub_page_maker(sub_dir_path+'cpu/',hw_info_dict['cpu'],data_loaded)})
    if page_title + "--Memory" in template_content:
        htmls_list.update({page_title + "--Memory":one_sub_page_maker(sub_dir_path+'memory/',hw_info_dict['memory'],data_loaded)})
    if page_title + "--Network" in template_content:
        htmls_list.update({page_title + "--Network":one_sub_page_maker(sub_dir_path+'net/',hw_info_dict['net'],data_loaded)})
    if page_title + "--Disk" in template_content:
        htmls_list.update({page_title + "--Disk":one_sub_page_maker(sub_dir_path+'disk/',hw_info_dict['disk'],data_loaded)})
    if page_title + "--PCI" in template_content:
        #htmls_list.update({page_title + "--PCI":sub_page_maker(sub_dir_path+'pci/',hw_info_dict['pci'],data_loaded)})
        htmls_list.update({page_title + "--PCI":one_sub_page_maker(sub_dir_path+'pci/',hw_info_dict['cpu'],data_loaded)})
    return htmls_list

def one_sub_page_maker(path_to_files,spec_dict,data_loaded):
    logging.info("report_recorder - Executing one_sub_page_maker function")
    html_content = ""
    for i in os.listdir(path_to_files.replace("{serverName}",next(iter(spec_dict.values()))[0])):
        html_content += f"<h2> {str(i).replace('.txt','')} </h2>"
        for key,value in spec_dict.items():
            html_content += f"<h3> {value} </h3>"
            p = path_to_files.replace("{serverName}",value[0])+i
            if os.path.exists(p):
                with open(p, 'r') as file:
                    file_contents = file.readlines()
                for file_content in file_contents:
                    html_content += f"<p>{file_content.replace(' ','&nbsp;')}</p>"
            else:
                html_content += "<p> فایل مربوطه یافت نشد </p>"
    html_content += "<p> </p>"
    html_content += data_loaded['naming_tag'].get('tags')
    return html_content

#### upload data and make wiki page ####
def convert_html_to_wiki(html_content):
    logging.info("report_recorder - Executing convert_html_to_wiki function")
    # Convert dominate document to a string if needed
    if isinstance(html_content, document):
        html_content = html_content.render()
    elif not isinstance(html_content, str):
        html_content = str(html_content)
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
    except Exception as e:
        logging.error(f"Error parsing HTML content: {e}")
        raise
    # Convert <a> tags to wiki links
    for a_tag in soup.find_all('a'):
        href = a_tag.get('href', '').replace(' ', '_').replace(".html", '', 1)
        if href.startswith('./subpages/'):
            href = href.replace('./subpages/', kateb_url, 1)
        elif href.startswith('./'):
            href = href.replace('./', kateb_url, 1)
        a_tag.replace_with(f"[{href} |{a_tag.text}]")
    # Convert <img> tags to wiki images
    for img_tag in soup.find_all('img'):
        if 'src' in img_tag.attrs:
            img_tag.replace_with(f"[[File:{os.path.basename(img_tag['src'])}|border|center|800px|{os.path.basename(img_tag['src'])}]]")
    # Remove <body>, <thead>, and <tbody> tags
    for tag_name in ['body', 'thead', 'tbody']:
        for tag in soup.find_all(tag_name):
            tag.unwrap()  # Remove the tag but keep its content
    return str(soup)

def check_data(site, title_content_dict):
    logging.info("report_recorder - Executing check_data function")
    delete_all = False
    skip_all = False
    titles_to_skip = []
    for title in list(title_content_dict.keys()):
        page = pywikibot.Page(site, title)
        if skip_all:
            logging.info(f"Skipping page '{title}' due to 'no all' choice.")
            titles_to_skip.append(title)
            continue
        if page.exists() and not delete_all:
            valid_input_received = False
            while not valid_input_received:
                user_choice = input(f"\033[1;33mPage '{title}' already exists. Delete it? (yes/yes all/no/no all):\033[0m").strip().lower()
                if user_choice == "yes":
                    page.delete(reason="Removing old page before re-upload", prompt=False)
                    logging.info(f"Page '{title}' existed and was deleted.")
                    valid_input_received = True
                elif user_choice == "yes all":
                    delete_all = True
                    logging.info(f"Deleting all existing pages due to 'yes all' choice.")
                    valid_input_received = True
                elif user_choice == "no":
                    logging.info(f"Page '{title}' exists and was not deleted.")
                    titles_to_skip.append(title)
                    valid_input_received = True
                elif user_choice == "no all":
                    skip_all = True
                    logging.info(f"Skipping all remaining pages due to 'no all' choice.")
                    titles_to_skip.append(title)
                    valid_input_received = True
                else:
                    print(f"\033[91mInvalid input '{user_choice}' received.")
                    logging.error(f"Invalid input '{user_choice}' received.")
    # Remove skipped titles from the dictionary
    for title in titles_to_skip:
        title_content_dict.pop(title, None)
    # If "yes all" was chosen, delete remaining pages
    if delete_all:
        for title in list(title_content_dict.keys()):
            page = pywikibot.Page(site, title)
            if page.exists():
                page.delete(reason="Removing old page before re-upload", prompt=False)
                logging.info(f"Page '{title}' existed and was deleted due to 'yes all' choice.")
    upload_data(site, title_content_dict)

def upload_data(site, title_content_dict):
    logging.info("report_recorder - Executing upload_data function")
    try:
        for title, content in title_content_dict.items():
            page = pywikibot.Page(site, title)
            page.text = content + '\n powered by KARA'
            page.save(summary="Uploaded by KARA", force=True, quiet=False, botflag=False)
            #page.save(" برچسب: [[مدیاویکی:Visualeditor-descriptionpagelink|ویرایش‌گر دیداری]]")
            logging.info(f"Page '{title}' uploaded successfully.")
    except pywikibot.exceptions.Error as e:
        logging.error(f"report_recorder - Error uploading page '{title}': {e}")

def upload_images(site, html_content):
    logging.info("report_recorder - Executing upload_images function")
    # Convert dominate document to a string if needed
    if isinstance(html_content, document):
        html_content = html_content.render()
    elif not isinstance(html_content, str):
        html_content = str(html_content)
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
    except Exception as e:
        logging.error(f"Error parsing HTML content: {e}")
        raise
    image_paths = [img['src'] for img in soup.find_all('img') if 'src' in img.attrs]
    # Upload each image to the wiki
    for image_path in image_paths:
        image_filename = os.path.basename(image_path)
        page = pywikibot.FilePage(site, f'File:{image_filename}')
        if not page.exists():
            file_page = pywikibot.FilePage(site, page.title())
            if file_page.exists():
                raise ValueError("File already exists!")
            success = file_page.upload(image_path, comment=f"Uploaded image '{image_filename}' by KARA")
            if success:
                print(f"File uploaded successfully! File page: {file_page.full_url()}")
                logging.info(f"report_recorder - Image '{image_filename}' uploaded successfully.")
            else:
                print(f"Upload this image '{image_filename}' failed.")
                logging.warning(f"report_recorder - Upload this image '{image_filename}' failed.")
        else:
            print(f"Image'\033[91m{image_filename}\033[0m'already exists on the wiki.")
            logging.warning(f"report_recorder - Image '{image_filename}' already exists on the wiki.")

def main(software_template, hardware_template, output_htmls_path, cluster_name, scenario_name, configs_directory, upload_operation, create_html_operation, merged_file, merged_info_file, all_test_dir, create_test_page):
    global configs_dir
    htmls_dict = {}
    data_loaded = load_config(config_file)
    log_level = data_loaded['log'].get('level')
    if log_level is not None:
        log_level_upper = log_level.upper()
        valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if log_level_upper in valid_log_levels:
            log_dir_run = subprocess.run(f"sudo mkdir {log_path} > /dev/null 2>&1 && sudo chmod -R 777 {log_path}", shell=True)
            logging.basicConfig(filename= f'{log_path}all.log', level=log_level_upper, format='%(asctime)s - %(levelname)s - %(message)s')
        else:
            print(f"\033[91mInvalid log level:{log_level}\033[0m")  
    else:
        print(f"\033[91mPlease enter log_level in the configuration file.\033[0m")

    logging.info("\033[92m****** report_recorder main function start ******\033[0m")
    if software_template is None and hardware_template is None and create_test_page is None:
        print(f"\033[91m report_recorder need hardware_template(-ht),software_template(-st) and test_page(-tp) operation to work please select one of them ! \033[0m")
        exit()
    if cluster_name is None:
        cluster_name = data_loaded['naming_tag'].get('cluster_name')
    if scenario_name is None:
        scenario_name = data_loaded['naming_tag'].get('scenario_name')
    if merged_file is None:
        merged_file = data_loaded['tests_info'].get('merged')
    if merged_info_file is None:
        merged_info_file = data_loaded['tests_info'].get('merged_info')
    if all_test_dir is None:
        all_test_dir = data_loaded['tests_info'].get('tests_dir')
    if output_htmls_path is None:
        output_htmls_path = data_loaded['output_path']
    if configs_directory is None:
        configs_directory = data_loaded['configs_dir']
    if software_template is None and data_loaded['software_template']:
            software_template = data_loaded['software_template']
    if hardware_template is None and data_loaded['hardware_template']:
        hardware_template = data_loaded['hardware_template']
    if create_html_operation:
        if configs_directory is not None:
            if os.path.exists(configs_directory):
                configs_dir = configs_directory
                analyzer.conf_dir(configs_dir)
                analyzer.get_list_of_servers()
            elif software_template or hardware_template:
                print(f"\033[91minput backup File not found for make hardware or software pages\033[0m")
                logging.warning(f"report_recorder - input backup File not found for make hardware or software pages")
                exit(1)
            if hardware_template:
                with open(hardware_template, 'r') as template_content:
                    htmls_dict = create_sw_hw_htmls(template_content.read(), output_htmls_path, cluster_name+'--HW', data_loaded) 
            if software_template:
                with open(software_template, 'r') as template_content:
                    htmls_dict.update(create_sw_hw_htmls(template_content.read(), output_htmls_path, cluster_name+'--'+scenario_name+'--SW', data_loaded))
        if create_test_page:
            scenario_pages = create_test_htmls("",output_htmls_path, cluster_name, scenario_name, merged_file, merged_info_file, all_test_dir, data_loaded)
    elif upload_operation:
        for html_file in os.listdir(output_htmls_path):
            with open(os.path.join(output_htmls_path,html_file), 'r', encoding='utf-8') as file:
                htmls_dict = [{cluster_name+html_file:file.read()}]
    if upload_operation:
        # Set up the wiki site
        site = pywikibot.Site()
        site.login()
        title_content_dict = {}
        for title,content in htmls_dict.items():
            wiki_content = convert_html_to_wiki(content)
            title_content_dict[title] = wiki_content
            # Upload images to the wiki
            upload_images(site, content)
        if create_test_page:
            for page in scenario_pages:
                wiki_content = convert_html_to_wiki(page.body)
                title_content_dict[page.title] = wiki_content
                # Upload images to the wiki
                upload_images(site, page.body)
        # Upload converted data to the wiki
        check_data(site, title_content_dict)
    logging.info("\033[92m****** report_recorder main function end ******\033[0m")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate report for kateb")
    parser.add_argument("-st", "--software_template", help="input template HTML file path")
    parser.add_argument("-ht", "--hardware_template", help="input template HTML file path")
    parser.add_argument("-o", "--output_htmls_path", help="output HTML files path")
    parser.add_argument("-cn", "--cluster_name", help="cluster_name set for title of Kateb HW page.")
    parser.add_argument("-sn", "--scenario_name", help="set for title of Kateb test page.")
    parser.add_argument("-U", "--upload_operation", action='store_true', help="upload page to kateb")
    parser.add_argument("-H", "--create_html_operation", action='store_true', help="create HTML page template")
    parser.add_argument("-tp", "--create_test_page", action='store_true', help="create monster test HTML page")
    parser.add_argument("-cd", "--configs_directory", help="directory of backup include test configs")
    parser.add_argument("-m", "--merged_file", help="path to merged.csv file")
    parser.add_argument("-mi", "--merged_info_file", help="path to merged_info.csv file")
    parser.add_argument("-td", "--all_test_dir", help="directory of all tests")
    args = parser.parse_args()
    software_template = args.software_template 
    hardware_template = args.hardware_template 
    output_htmls_path = args.output_htmls_path if args.output_htmls_path else None
    cluster_name = args.cluster_name if args.cluster_name else None
    scenario_name = args.scenario_name if args.scenario_name else None
    merged_file = args.merged_file if args.merged_file else None
    merged_info_file = args.merged_info_file if args.merged_info_file else None
    all_test_dir = args.all_test_dir if args.all_test_dir else None
    configs_directory = args.configs_directory if args.configs_directory else None
    upload_operation = args.upload_operation
    create_html_operation = args.create_html_operation
    create_test_page = args.create_test_page
    main(software_template, hardware_template, output_htmls_path, cluster_name, scenario_name, configs_directory, upload_operation, create_html_operation, merged_file, merged_info_file, all_test_dir, create_test_page)
