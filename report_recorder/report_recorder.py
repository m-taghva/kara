import argparse
import re
import os
from bs4 import BeautifulSoup
import logging
import csv
from collections import Counter
import subprocess
import sys
import pandas as pd
pywiki_path = os.path.abspath("./../report_recorder/pywikibot")
if pywiki_path not in sys.path:
    sys.path.append(pywiki_path)
import pywikibot
classification_path = os.path.abspath("./../report_recorder/")
if classification_path not in sys.path:
    sys.path.append(classification_path)
import classification

# read backup dir
configs_dir = ""
def load(directory):
    with open(configs_dir + directory, 'r') as f:
        content = f.readlines()
    return content

# dmidecode -t 1
def generate_brand_model(serverName):
    result = load(f'/configs/{serverName}' + "/hardware/server-manufacturer/dmidecode.txt")
    manufacturer = ""
    productName = ""
    for line in result:
        if "Manufacturer" in line:
            manufacturer = line.split(":")[1].replace("\n" , "")
        if "Product Name" in line:
            productName = line.split(":")[1].replace("\n" , "")
    return manufacturer + productName

# lscpu
def generate_cpu_model(serverName):
    result= load(f'/configs/{serverName}' + "/hardware/cpu/lscpu.txt")
    coresPerSocket = ""
    socket = ""
    threads = ""
    model = ""
    for line in result:
        line = line.replace("  ", "").replace("\n","").split(":")
        if "Core(s) per socket" in line[0]:
            coresPerSocket=line[1]
            #print ("("+  coresPerSocket+ ")")
        if "Socket(s)" in line[0]:
            socket=line[1]
        if "Thread(s) per core" in line[0]:
            threads = line[1]
        if "Model name" in line[0]:
            model = line[1]
    return coresPerSocket + "xcores x " + socket + "xsockets x " + threads + "xthreads " + model

# lshw -short -C memory
def generate_memory_model(serverName):
    result = load(f'/configs/{serverName}' + "/hardware/memory/lshw-brief.txt")
    rams=[]
    for line in result:
        line = line.replace("  ", "")
        if "DIMM" in line:
            if "empty" not in line:
                model = line.split("memory ")[1]
                rams.append(model)
    counts = Counter(rams)
    ram = ""
    for item , count in counts.items():
        ram+= str(count) + "x" + item
    return ram

# lshw -json -C net
def generate_net_model(serverName):
    result = load(f'/configs/{serverName}' + "/hardware/net/lshw-json.txt")
    Flag = False
    nets=[]
    capacities = []
    for line in result:
        line = line.replace(",\n" , "")
        if "id" in line:
            Flag = True
        if Flag is True:
            if "product" in line:
                nets.append( line.split(":")[1].replace("" , ""))
            if "capacity" in line:
                capacities.append(line.split(":")[1].replace("000000000" , "")+"Gbit/s")
                Flag = False
    netModel=[]
    for i in range(len(nets)):
        if i < len(capacities):
            netModel.append(capacities[i] + " " + nets[i])
        else:
            netModel.append(nets[i])
    counts = Counter(netModel)
    net = ""
    for item, count in counts.items():
        net += str(count) + "x" + item + "\n"
    return net

# dmidecode -t 2
def generate_motherboard_model(serverName):
    result = load(f'/configs/{serverName}' + "/hardware/motherboard/dmidecode.txt")
    manufacturer = ""
    productName = ""
    for line in result:
        if "Manufacturer" in line:
            manufacturer = line.split(":")[1].replace("\n", "")
        if "Product Name" in line:
            productName = line.split(":")[1].replace("\n", "")
    return manufacturer + productName

# lshw -short -C disk
def generate_disk_model(serverName):
    result = load(f'/configs/{serverName}' + "/hardware/disk/lshw-brief.txt")
    disks= []
    for line in result:
        if "disk" in line:
            diskname = line.split("disk")[1].replace("  ", "").replace("\n", "")
            if diskname != "":
                disks.append(diskname)
    counts = Counter(disks)
    disksNames =""
    for item, count in counts.items():
        disksNames += str(count) + "x" + item + "\n"
    return disksNames

def generate_model(server ,part ,spec):
    if part == "hardware":
        if spec == "cpu":
            return generate_cpu_model(server)
        elif spec == "memory":
            return generate_memory_model(server)
        elif spec == "net":
            return generate_net_model(server)
        elif spec == "motherboard":
            return generate_motherboard_model(server)
        elif spec == "brand":
            return generate_brand_model(server)
        elif spec == "disk":
            return generate_disk_model(server)
    elif part == "software":
        return "software not configed"

def compare(part ,spec):
    cmd = ["ls" , f'{configs_dir}/configs']
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    listOfServers = result.stdout.split("\n")
    listOfServers.pop()
    dict = {}
    for server in listOfServers:
        model= generate_model(server ,part ,spec)
        if model in dict:
            if dict[model] is None:
                dict[model] = []
        else: dict[model]= []
        dict[model].append(server)
    return dict

def test_page_maker(merged_file, merged_info_file, all_test_dir, page_title):
    htmls_dict={}
    mergedInfo = pd.read_csv(merged_info_file)
    merged = pd.read_csv(merged_file)
    original_columns_merged_info = mergedInfo.columns.tolist()
    mergedInfo = mergedInfo.loc[:, mergedInfo.nunique() != 1]
    removed_columns_mergedInfo = [col for col in original_columns_merged_info if col not in mergedInfo.columns]
    merged = merged.drop(columns=removed_columns_mergedInfo, errors='ignore')
    num_lines = mergedInfo.shape[0]

    number_of_groups = 0
    sorted_unique = classification.csv_to_sorted_yaml(mergedInfo)
    array_of_groups = classification.group_generator(sorted_unique,threshold=8)
    

    html_result = "<h2> نتایج تست های کارایی </h2>"
    html_result += f"<p> بر روی این کلاستر {num_lines} تعداد تست انجام شده که در **var** دسته تست طبقه بندی شده است. </p>"
    for sharedInfo in array_of_groups:
        mergedInfo2 = mergedInfo
        merged2 = merged
        testGroup = ' , '.join(f'{key} = {value}' for key, value in sharedInfo.items())
        for key, value in sharedInfo.items():
            mergedInfo2 = mergedInfo2[mergedInfo2[key] == int(value)]
            merged2 = merged2[merged2[key] == int(value)]
            mergedInfo2 = mergedInfo2.drop(key,axis=1)
            merged2 = merged2.drop(key,axis=1)
        if merged2.empty:
            continue    
        else:
            number_of_groups+=1
            html_result+= f"<h3> نتایج تست های گروه: {testGroup} </h3>"
        html_result+= "<table border='1' class='wikitable'>\n"
        for i, row in enumerate(merged2.to_csv().split("\n")):
            html_result += "<tr>\n"
            tag = "th" if i == 0 else "td"
            for j , column in enumerate(row.split(",")):
                if j:
                    html_result += f"<{tag}>{column}</{tag}>\n"
            html_result += "</tr>\n"
        html_result += "</table>"
        format_tg = testGroup.strip().replace(' ','').replace('=','-').replace(',','-')
        html_result += f"<a href=https://kateb.burna.ir/wiki/{page_title}--{format_tg}> نمایش جزئیات </a>"
        ###### create subgroups within each original group  ######
        sorted_unique_file_1 = classification.csv_to_sorted_yaml(mergedInfo2)
        array_of_groups_1 = classification.group_generator(sorted_unique_file_1,threshold=4)
        sub_html_result = classification.create_tests_details(mergedInfo2,merged2,testGroup,array_of_groups_1,all_test_dir)
        htmls_dict.update({f"{page_title}--{format_tg}":sub_html_result+"[[رده:تست]]\n[[رده:کارایی]]\n[[رده:هیولا]]"})
    htmls_dict.update({page_title:html_result.replace("**var**",str(number_of_groups))+"[[رده:تست]]\n[[رده:کارایی]]\n[[رده:هیولا]]"})
    return htmls_dict

#### make HTML template ####
def dict_to_html(dict):
    html_dict = "<table border='1' class='wikitable'>\n"
    html_dict += "<tr><th> نام سرور </th><th> مشخصات </th></tr>\n"
    for key, value in dict.items():
        if isinstance(value, list):
            value_str = ','.join(value)
        else:
            value_str = str(value)
        html_dict += f"<tr><td>{value_str}</td><td>{key}</td></tr>\n"
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

def create_hw_htmls(template_content, html_output, page_title): #page_title = cluster_name
    logging.info("Executing report_recorder create_html_template function")
    htmls_dict={}
    hw_info_dict = {}
    html_data = template_content.replace("{title}",f"{page_title}") # for replace placeholder with content of files
    # Find all occurrences of {input_config} placeholders in the template
    for match in re.finditer(r'{input_config}:(.+)', template_content):
        # Iterate over the placeholders and replace them with content
        address_placeholder = match.group(0)
        file_path = match.group(1).strip()
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
    for config_info in re.finditer(r'{server_config}:(.+)', template_content):
        config_placeholder = config_info.group(0)
        part,spec = config_info.group(1).split(',')
        dict = compare(part.strip(), spec.strip())
        hw_info_dict.update({spec.strip():dict})
        html_of_dict = dict_to_html(dict)
        html_data = html_data.replace(config_placeholder, html_of_dict)
    htmls_dict.update({page_title:html_data})
    htmls_dict.update(sub_pages_maker(html_data,page_title,hw_info_dict))
    for html_key,html_value in htmls_dict.items():
        with open(os.path.join(html_output+"/"+html_key+".html"), 'w') as html_file:
            html_file.write(html_value)
            print(f"HTML template saved to: {html_output+'/'+html_key+'.html'}") 
    return htmls_dict

def create_test_htmls(template_content, html_output, page_title, merged_file, merged_info_file, all_test_dir): #page_title = cluster_name + scenario_name
    htmls_dict = test_page_maker(merged_file, merged_info_file, all_test_dir, page_title)
    for html_key,html_value in htmls_dict.items():
        with open(os.path.join(html_output+"/"+html_key+".html"), 'w') as html_file:
            html_file.write(html_value)
            print(f"HTML template saved to: {html_output+'/'+html_key+'.html'}") 
    return htmls_dict

#### upload data and make wiki page ####
def convert_html_to_wiki(html_content):
    logging.info("Executing report_recorder convert_html_to_wiki function")
    soup = BeautifulSoup(html_content, 'html.parser')
    # Convert <a> tags to wiki links
    for a_tag in soup.find_all('a'):
        a_tag.replace_with(f"[{a_tag['href']} |{a_tag.text}]")
    # Convert <img> tags to wiki images
    for img_tag in soup.find_all('img'):
        if 'src' in img_tag.attrs:
            img_tag.replace_with(f"[[File:{os.path.basename(img_tag['src'])}|800px|thumb|center|{os.path.basename(img_tag['src']).split('_2024')[0]}]]") #replace(_2024) hazf shavaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaad
    return str(soup)

def sub_pages_maker(template_content , page_title ,hw_info_dict):
    global configs_dir
    htmls_list={}
    s1 = configs_dir
    sub_dir_path = os.path.join(s1,'configs/{serverName}/hardware/')
    if page_title + "--CPU" in template_content:
        htmls_list.update({page_title + "--CPU":one_sub_page_maker(sub_dir_path+'cpu/',hw_info_dict['cpu'])})
    if page_title + "--Memory" in template_content:
        htmls_list.update({page_title + "--Memory":one_sub_page_maker(sub_dir_path+'memory/',hw_info_dict['memory'])})
    if page_title + "--Network" in template_content:
        htmls_list.update({page_title + "--Network":one_sub_page_maker(sub_dir_path+'net/',hw_info_dict['net'])})
    if page_title + "--Disk" in template_content:
        htmls_list.update({page_title + "--Disk":one_sub_page_maker(sub_dir_path+'disk/',hw_info_dict['disk'])})
    if page_title + "--PCI" in template_content:
        #htmls_list.update({page_title + "--PCI":sub_page_maker(sub_dir_path+'pci/',hw_info_dict['pci'])})
        htmls_list.update({page_title + "--PCI":one_sub_page_maker(sub_dir_path+'pci/',hw_info_dict['cpu'])})
    return htmls_list

def one_sub_page_maker(path_to_files,spec_dict):
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
    html_content += "[[رده:تست]]\n[[رده:کارایی]]\n[[رده:هیولا]]"
    return html_content

def upload_data(site, page_title, wiki_content):
    logging.info("Executing report_recorder upload_data function")
    try:
        page = pywikibot.Page(site, page_title)
        if not page.exists():
            page.text = wiki_content + '\n powered by KARA'
            page.save(summary="Uploaded by KARA", force=True, quiet=False, botflag=False)
            #page.save(" برچسب: [[مدیاویکی:Visualeditor-descriptionpagelink|ویرایش‌گر دیداری]]")
            logging.info(f"Page '{page_title}' uploaded successfully.")
        else:
            print(f"Page '\033[91m{page_title}\033[0m' already exists on the wiki.")
            logging.warning(f"Page '{page_title}' already exists on the wiki.")
    except pywikibot.exceptions.Error as e:
        logging.error(f"Error uploading page '{page_title}': {e}")

def upload_images(site, html_content):
    logging.info("Executing report_recorder upload_images function")
    soup = BeautifulSoup(html_content, 'html.parser')
    image_paths = [img['src'] for img in soup.find_all('img') if 'src' in img.attrs]
    # Upload each image to the wiki
    for image_path in image_paths:
        image_filename = os.path.basename(image_path)
        page = pywikibot.FilePage(site, f'File:{image_filename}')
        if not page.exists():
            file_page = pywikibot.FilePage(site, page.title())
            if file_page.exists():
                raise ValueError("File already exists!")
            success = file_page.upload(image_path, comment=f"Uploaded image '{image_filename}' using KARA")
            if success:
                print(f"File uploaded successfully! File page: {file_page.full_url()}")
            else:
                print("Upload failed.")
            logging.info(f"Image '{image_filename}' uploaded successfully.")
        else:
            logging.warning(f"Image '{image_filename}' already exists on the wiki.")

def main(input_template, html_output_path, cluster_name, scenario_name, main_html_page, configs_directory, upload_operation, create_html_operation, merged_file, merged_info_file, all_test_dir):
    global configs_dir
    htmls_dict = {}
    log_maker = subprocess.run(f"sudo mkdir /var/log/kara/ > /dev/null 2>&1 && sudo chmod -R 777 /var/log/kara/", shell=True)
    logging.basicConfig(filename= '/var/log/kara/all.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("\033[92m****** report_recorder main function start ******\033[0m")
    if create_html_operation:
        if configs_directory is not None:
            if os.path.exists(configs_directory):
                configs_dir = configs_directory
            else:
                print(f"\033[91minput backup File not found\033[0m")
        if input_template:
            with open(input_template, 'r') as template_content:
                htmls_dict = create_hw_htmls(template_content.read(), html_output_path, cluster_name+'--HW')  
        if merged_file and merged_info_file and  all_test_dir:
            htmls_dict.update(create_test_htmls("",html_output_path,cluster_name+"--"+scenario_name, merged_file, merged_info_file, all_test_dir)) 
    elif upload_operation:
        with open(main_html_page, 'r', encoding='utf-8') as file:
            htmls_dict = [{cluster_name:file.read()}]
    if upload_operation:
        # Set up the wiki site
        site = pywikibot.Site()
        site.login()
        for title,content in htmls_dict.items():
            wiki_content = convert_html_to_wiki(content)
            # Upload converted data to the wiki
            upload_data(site, title, wiki_content)
            # Upload images to the wiki
            upload_images(site, content)
    logging.info("\033[92m****** report_recorder main function end ******\033[0m")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate report for kateb")
    parser.add_argument("-i", "--input_template", help="Template HTML file path")
    parser.add_argument("-o", "--html_output_path", help="Output HTML file name")
    parser.add_argument("-p", "--main_html_page", help="HTML template for upload")
    parser.add_argument("-cn", "--cluster_name", help="cluster_name set for title of Kateb HW page.")
    parser.add_argument("-sn", "--scenario_name", help="set for title of Kateb test page.")
    parser.add_argument("-U", "--upload_operation", action='store_true', help="upload page to kateb")
    parser.add_argument("-H", "--create_html_operation", action='store_true', help="create HTML page template")
    parser.add_argument("-cd", "--configs_directory", help="directory of backup include test configs")
    parser.add_argument("-m", "--merged_file", help="path to merged.csv file")
    parser.add_argument("-mi", "--merged_info_file", help="path to merged_info.csv file")
    parser.add_argument("-td", "--all_test_dir", help="directory of all tests")
    args = parser.parse_args()
    input_template = args.input_template 
    html_output_path = args.html_output_path
    cluster_name = args.cluster_name
    scenario_name = args.scenario_name 
    main_html_page = args.main_html_page
    merged_file = args.merged_file
    merged_info_file = args.merged_info_file
    all_test_dir = args.all_test_dir
    if args.configs_directory:
       configs_directory = args.configs_directory 
    else:
        configs_directory = None
    upload_operation = args.upload_operation
    create_html_operation = args.create_html_operation
    main(input_template, html_output_path, cluster_name, scenario_name, main_html_page, configs_directory, upload_operation, create_html_operation, merged_file, merged_info_file, all_test_dir)
