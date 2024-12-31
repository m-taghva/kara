import argparse
import re
import os
import yaml
import logging
import csv
import subprocess
import shutil
import sys
import shutil
import pandas as pd
from bs4 import BeautifulSoup
from dataclasses import dataclass
import dominate
from dominate.tags import *
from dominate.util import raw
from dominate.document import document
import jdatetime
python_ver_dir = subprocess.run(f'find /usr/local/lib/ -maxdepth 1 -type d -name "python*" -exec basename {{}} \\; | sort -V | tail -n 1', shell=True, capture_output=True, text=True).stdout.strip()
pywiki_path = os.path.abspath(f"/usr/local/lib/{python_ver_dir}/dist-packages/report_recorder_bot/")
if pywiki_path not in sys.path:
    sys.path.append(pywiki_path)
import pywikibot
import analyzer

# variables
config_file = "/etc/kara/report_recorder.conf"
kateb_url = "https://kateb.burna.ir/wiki/"
log_path = "/var/log/kara/"

class testClassification:
    pageNameDelimiter = "_"
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

    class mainPage:
        category: str

    def __init__(self,infocsv,detailcsv,clusterName,scenarioName,imgsdict, conf) -> None:
        self.infocsv = infocsv
        self.detailcsv = detailcsv.drop(columns=[col for col in infocsv.columns.intersection(detailcsv.columns) if col != self.timeColumn])
        self.clusterName = clusterName
        self.scenarioName = scenarioName
        self.maxTestsPerPage = 8
        self.autoDivider = True
        self.subPagesHTML = []
        self.imgsdict = imgsdict
        self.mainPageHTML = dominate.document(title=f'{clusterName}--{scenarioName}')
        with self.mainPageHTML:
            p(raw(f"در این سند تست‌های مرتبط با سناریو {self.scenarioName} در کلاستر {self.clusterName} آورده شده‌اند. در ادامه ابتدا در بخش معماری کلاستر مشخصات سخت‌افزاری و نرم‌افزاری کلاستر {self.clusterName} و سپس در بخش نتایج تست‌های کارایی، دسته‌بندی تست‌های انجام شده آورده شده است."), dir="rtl")
            if 'classification' in conf:
                if 'comment' in conf['classification']:
                    p(raw(conf['classification']['comment']), dir="rtl")
            h2("معماری کلاستر", dir="rtl")
            p("برای مشاهده مشخصات سخت‌افزاری کلاستر به سند ",a(f'مشخصات سخت‌افزاری {clusterName}', href=f'./{clusterName}--HW.html', target='_blank')," مراجعه کنید.",dir="rtl")
            p("برای مشاهده تنظیمات و مشخصات نرم‌افزاری کلاستر به سند ",a(f'مشخصات نرم‌افزاری سناریو {scenarioName} در کلاستر {clusterName}', href=f'./{clusterName}--{scenarioName}--SW.html', target='_blank')," مراجعه کنید.",dir="rtl")
            h2("نتایج تست‌های کارایی", dir="rtl")
        # Convert each row to a tuple and count occurrences
        row_counts = infocsv.drop(columns=[self.timeColumn]).apply(tuple, axis=1).value_counts()
        most_duplicated_count = row_counts.max()   # Count of the most duplicated row
        if most_duplicated_count>self.maxTestsPerPage:
            self.maxTestsPerPage=most_duplicated_count
            print(f"Notice: The threshold has been automatically adjusted to {self.maxTestsPerPage} to avoid errors.")
        if 'classification' in conf:
            if 'autoDivider' in conf['classification']:
                if conf['classification']['autoDivider'] == False:
                    self.maxTestsPerPage = len(self.infocsv)
                    self.autoDivider = False
            else:
                print("Warning: there isn't the 'autoDivider' parameter in the classification section, then autoDivider=True !!!")
            if 'maxTestsPerPage' in conf["classification"] and self.autoDivider:
                self.maxTestsPerPage = conf["classification"]["maxTestsPerPage"]
            elif self.autoDivider:
                print(f"Warning: there isn't the 'maxTestsPerPage' parameter in the classification section, then maxTestsPerPage={self.maxTestsPerPage} (default)")
            if 'categories' in conf["classification"]:
                with self.mainPageHTML:
                    p(raw(f"در این سناریو مجموعا <b>{len(self.infocsv)}</b> تست وجود دارد که در <b>{len(conf['classification']['categories'])}</b> دسته {list(conf['classification']['categories'].keys())} طبقه‌بندی شده‌اند. در ادامه هر دسته تست در یک بخش جداگانه آورده شده است."), dir="rtl")
            else:
                print("Warning: there isn't the 'categories' section in the classification section. !!!")
            self.createPagesHTML(conf["classification"],self.infocsv)
            
        else:
            print("Warning: there isn't the 'classification' section in conf, then autoDivider=True !!!")
            exit()
        self.AllPagesHTML = self.subPagesHTML
        self.AllPagesHTML.append(self.mainPageHTML)

    def createcsvinfo(self, subdfinstance):
        for column_name in subdfinstance.subcsv.columns:
            unique_values = subdfinstance.subcsv[column_name].unique()
            subdfs = []
            maxl = 0
            for value in unique_values:
                subcsv = subdfinstance.subcsv[subdfinstance.subcsv[column_name] == value].drop(columns=[column_name])
                notMerged = 1
                for i in range(len(subdfs)):
                    if subdfs[i].l+len(subcsv) <= self.maxTestsPerPage:
                        concatcsv = pd.concat([subdfs[i].subcsv,subcsv])
                        new_subdf = self.subdf(subcsv = concatcsv, csvinfo={}, bestColumnforDivider = None, dividerNumber=len(concatcsv)+1, l=len(concatcsv), value=f"{subdfs[i].value}{self.valueDelimiter}{value}")
                        new_subdf.subcsv[column_name]= subdfinstance.subcsv[column_name]
                        subdfs[i] = new_subdf
                        notMerged = 0
                        break
                if notMerged:
                    new_subdf = self.subdf(subcsv=subcsv, csvinfo={}, bestColumnforDivider = None, dividerNumber=len(subcsv)+1, l=len(subcsv), value=value)
                    subdfs.append(new_subdf)
                if new_subdf.l>maxl:
                    maxl = new_subdf.l
            subdfinstance.csvinfo[column_name] = subdfs
            if maxl <= self.maxTestsPerPage and len(subdfs) < subdfinstance.dividerNumber:
                subdfinstance.dividerNumber = len(subdfs)
                subdfinstance.bestColumnforDivider = column_name

    def divider(self, maindata):
        if not maindata.bestColumnforDivider:
            for key, subdf_list in maindata.csvinfo.items():
                currentDividerNumber = 0
                for index, item in enumerate(subdf_list):
                    if item.l > self.maxTestsPerPage:
                        self.createcsvinfo(maindata.csvinfo[key][index])
                        currentDividerNumber += self.divider(maindata.csvinfo[key][index])
                    else:
                        currentDividerNumber += 1
                if currentDividerNumber < maindata.dividerNumber:
                    maindata.dividerNumber = currentDividerNumber
                    maindata.bestColumnforDivider = key
            return maindata.dividerNumber
        else:
            return maindata.dividerNumber

    def createMainPageData(self, maindata,prefixstr=""):
        doclist = {}
        for item in maindata.csvinfo[maindata.bestColumnforDivider]:
            currentstr = f'{maindata.bestColumnforDivider}:{item.value}'
            if(item.bestColumnforDivider):
                doclist.update(self.createMainPageData(item,prefixstr+currentstr+self.pageNameDelimiter))
            else:
                if len(maindata.csvinfo[maindata.bestColumnforDivider])==1:
                    prefixstr += "detail"
                    currentstr=""
                doclist[prefixstr+currentstr] = item.subcsv
        return doclist

    def createSubPageData(self, subPageData: subPage):
        if not subPageData.summarycsv.empty:
            most_duplicated_count = subPageData.summarycsv.apply(tuple, axis=1).value_counts().max() # Count of the most duplicated row 
            if len(subPageData.summarycsv)-most_duplicated_count:
                subPageData.columnName = subPageData.summarycsv.nunique().idxmax()
                uniqueList = subPageData.summarycsv[subPageData.columnName].unique()
                subPageData.text = f"در اینجا {len(uniqueList)} دسته تست شامل {subPageData.columnName} برابر با {uniqueList.tolist()} آورده شده است."
                for value in subPageData.summarycsv[subPageData.columnName].unique():
                    subcsv = subPageData.summarycsv[subPageData.summarycsv[subPageData.columnName] == value].drop(columns=[subPageData.columnName])
                    subPageData.subcsv[value] = self.subPage(text="", columnName=None, subcsv={}, summarycsv=subcsv)
                    self.createSubPageData(subPageData.subcsv[value])
            else:
                subPageData.text = f"در این تست {subPageData.summarycsv.iloc[0].to_dict()} است."
                subPageData.summarycsv = subPageData.summarycsv.drop(columns=subPageData.summarycsv.columns)
                if most_duplicated_count > 1:
                    subPageData.text += f"<br><b>توجه:</b> این تست {len(subPageData.summarycsv)} بار تکرار شده است."
        else:
            if len(subPageData.summarycsv) > 1:
                subPageData.text = f"<b>توجه:</b> این تست {len(subPageData.summarycsv)} بار تکرار شده است."
        subPageData.summarycsv[self.timeColumn]= self.infocsv[self.timeColumn]
        subPageData.summarycsv = pd.merge(subPageData.summarycsv, self.detailcsv, on=self.timeColumn)
        #subPageData.summarycsv.columns = subPageData.summarycsv.columns.str.replace('.', '. ', regex=False)

    def createSubPageHTML(self, subPageHTML: dominate.document, subPageData :subPage, heading_level=2):
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
                self.createSubPageHTML(subPageHTML, value, heading_level+1)
            with subPageHTML:
                if heading_level<7:
                    heading_tag = getattr(dominate.tags, f'h{heading_level}')
                    heading_tag(f'جمع‌بندی {subPageData.columnName}', dir="rtl")
                else:
                    starLevel = "*"*(heading_level-6)
                    p(raw(f"<b>{starLevel} جمع‌بندی {subPageData.columnName}</b><br>"), dir="rtl")
                with div():
                    raw(subPageData.summarycsv.dropna(axis=1, how='all').to_html(index=False, border=2))         
        else:
            with subPageHTML:
                with div():
                    subPageData.summarycsv = subPageData.summarycsv.round(2)
                    raw(subPageData.summarycsv.dropna(axis=1, how='all').to_html(index=False, border=2))
                if (subPageData.summarycsv[self.timeColumn].iloc[0] in self.imgsdict):
                    for group,hosts in self.imgsdict[subPageData.summarycsv[self.timeColumn].iloc[0]].items():
                        for host,dashboards in hosts.items():
                            for dashboard,imgList in dashboards.items():
                                p(raw(f"<b>{group}_{host}_{dashboard}</b><br>"), dir="rtl")
                                for image in imgList:
                                    img(src=f"./subpages/imgs/{image}", alt=f"{self.clusterName}--{self.scenarioName}")
    
    def pageDataToHTML(self,mainPageData, heading_level): #return list of dominate.document
        pagesHTML = []
        total_rows = sum(df.shape[0] for df in mainPageData.values())
        if(len(mainPageData)>1):
            with self.mainPageHTML:
                p(raw(f"در این بخش مجموعا <b>{total_rows}</b> تست وجود دارد که در <b>{len(mainPageData)}</b> دسته طبقه‌بندی شده‌اند. در ادامه هر دسته در یک بخش جداگانه آورده شده است."), dir="rtl")
        else:
            with self.mainPageHTML:
                p(raw(f"در این بخش مجموعا <b>{total_rows}</b> تست وجود دارد که در جدول زیر نشان داده شده‌ است:"), dir="rtl")
        for pageName, pageData in mainPageData.items():
            subPageData = self.subPage(text="", columnName=None, subcsv={}, summarycsv=pageData)
            self.createSubPageData(subPageData)
            subPageHTML = dominate.document(title=f'{self.clusterName}--{self.scenarioName}--{pageName}')
            self.createSubPageHTML(subPageHTML, subPageData)
            pagesHTML.append(subPageHTML)
            pageData[self.timeColumn]= self.infocsv[self.timeColumn]
            with self.mainPageHTML:
                if len(mainPageData)>1:
                    if heading_level<7:
                        heading_tag = getattr(dominate.tags, f'h{heading_level}')
                        heading_tag(f'{pageName}', dir="rtl")
                    else:
                        starLevel = "*"*(heading_level-6)
                        p(raw(f"<b>{starLevel} {pageName}</b><br>"), dir="rtl")
                    p(raw(f"در این دسته مجموعا <b>{len(pageData)}</b> تست وجود دارد که در جدول زیر نشان داده شده‌ است:"), dir="rtl")
                with div():
                    raw(pageData.dropna(axis=1, how='all').to_html(index=False, border=2))
                a('نمایش جزئیات', href=f'./subpages/{self.clusterName}--{self.scenarioName}--{pageName}.html', target='_blank')
        return pagesHTML
            
    def createPagesHTML(self, classification, subinfocsv, heading_level=3, prefixstr=""):
        if 'categories' in classification:
            for categoryName, categoryData in classification['categories'].items():
                with self.mainPageHTML:
                    if heading_level<7:
                        heading_tag = getattr(dominate.tags, f'h{heading_level}')
                        heading_tag(f'{categoryName}', dir="rtl")
                    else:
                        starLevel = "*"*(heading_level-6)
                        p(raw(f"<b>{starLevel} {categoryName}</b><br>"), dir="rtl")
                    if 'comment' in categoryData:
                        p(raw(categoryData['comment']), dir="rtl")
                if 'filter' in categoryData:
                    with self.mainPageHTML:
                        p(raw(f"در این بخش {categoryData['filter']} است."), dir="rtl")
                    tempcsv = subinfocsv
                    for filterParameter, values in categoryData['filter'].items():
                        if filterParameter in tempcsv.columns:
                            tempcsv = tempcsv[tempcsv[filterParameter].isin(values)]
                            if len(values) == 1:
                                tempcsv = tempcsv.drop(columns=[filterParameter])
                        else:
                            print(f"ERROR: the '{filterParameter}' filter in '{categoryName}' category is wrong. It seems that it doesn't exist in the info.csv file or the subcsv with this filter is empty !!!")
                            exit()
                        if tempcsv.empty:
                            print(f"ERROR: the subcsv with '{filterParameter}' filter in '{categoryName}' category is empty")
                            exit()
                    self.createPagesHTML(categoryData,tempcsv,heading_level+1,prefixstr+categoryName+self.pageNameDelimiter)
                else:
                    print(f"ERROR: there isn't 'filter' parameter in '{categoryName}' category")
                    exit()
        else:
            #classification['subinfocsv'] = subinfocsv
            maindata = self.subdf(subcsv=subinfocsv.drop(columns=[self.timeColumn]),csvinfo={}, bestColumnforDivider = None, dividerNumber=len(subinfocsv)+1, l=len(subinfocsv), value=None)
            self.createcsvinfo(maindata)
            self.divider(maindata)
            mainPageData = self.createMainPageData(maindata,prefixstr)
            self.subPagesHTML.extend(self.pageDataToHTML(mainPageData,heading_level=heading_level))

def move_images(imgsdict,imgdir):
    if imgsdict:
        for time,groups in imgsdict.items():
            for group,hosts in groups.items():
                for host,dashboards in hosts.items():
                    for dashboard,imgList in dashboards.items():
                        for i in range(len(imgList)):
                            imgName = f'{time}_{group}_{host}_{dashboard}_{i}.png'
                            shutil.copy(imgList[i],os.path.join(imgdir,imgName))
                            imgList[i] = imgName
    else:
        imgsdict = {}

def load_config(config_file):
    with open(config_file, "r") as stream:
        try:
            data_loaded = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(f"Error loading the configuration: {exc}")
            sys.exit(1)
    return data_loaded

def path_to_dict(img_path_or_dict):
    imgs_path_to_dict = {}
    for time_dir in os.listdir(img_path_or_dict):
        filter_tests_dir = {'_','-'}
        if all(char in time_dir for char in filter_tests_dir):
            time_path = os.path.join(img_path_or_dict, time_dir)
            if os.path.isdir(time_path):
                imgs_path_to_dict[time_dir] = {}
                for host_dir in os.listdir(time_path):
                    if "-images" in host_dir:
                        host_path = os.path.join(time_path, host_dir)
                        if os.path.isdir(host_path):
                            group_name = host_dir.split("_", 1)[0]
                            host_name = host_dir.split("_")[1].replace('-images','')
                            imgs_path_to_dict[time_dir].setdefault(group_name, {})
                            imgs_path_to_dict[time_dir][group_name][host_name] = {}
                            # Collect all images in the host directory
                            all_images = [os.path.join(host_path, img_file) for img_file in os.listdir(host_path) if img_file.endswith('.png')]
                            # Separate dashboard images from others
                            dashboards = [img for img in all_images if "dashboard" in os.path.basename(img).lower()]
                            if dashboards:
                                dashboard_name = os.path.splitext(os.path.basename(dashboards[0]))[0]
                                dashboard_name_clean = re.sub(r'__\d+$', '', dashboard_name)
                                # Add dashboards to the host dictionary
                                imgs_path_to_dict[time_dir][group_name][host_name][dashboard_name_clean] = dashboards
    return imgs_path_to_dict 

#### make HTML template ####
def dict_html_software(data, confType):
    logging.info("report_recorder - Executing dict_html_software function")
    html_table = table(border="1", _class='wikitable')
    header_row = tr()
    header_row += td("servers")
    if isinstance(data["servers"], list):
        for item in data["servers"]:
            header_row += td(item)
    else:
        header_row += td(data["servers"])
    html_table += header_row
    for key, value in data.items():
        if key != "servers":
            row = tr()
            row += td(key)
            if confType != "swift_status":
                # Join list items with <br> in the same cell
                cell = td()
                for i, val in enumerate(value):
                    if i > 0:
                        cell += br()  # Add line break between values
                    cell += val
                row += cell
            else:
                # Add individual items as separate cells
                for item in value:
                    row += td(item)
            html_table += row
    return str(html_table)

def dict_html_hardware(dict):
    logging.info("report_recorder - Executing dict_to_html function")
    html_table = table(border="1", _class="wikitable")
    header_row = tr()
    header_row += th("نام سرور")
    header_row += th("مشخصات")
    html_table += header_row
    for key, value in dict.items():
        row = tr()
        if isinstance(value, list):
            # Create a cell with values joined by <br> elements
            cell = td()
            for i, val in enumerate(value):
                if i > 0:
                    cell += br()
                cell += val
        else:
            cell = td(str(value))
        row += cell  # Add the cell with the values
        # Add the key as the second cell
        row += td(key)
        html_table += row
    return str(html_table)

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
    if 'input_config' in template_content:
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
    if 'hw_config' in template_content:
        for hconfig_info in re.finditer(r'{hw_config}:(.+)', template_content):
            hconfig_placeholder = hconfig_info.group(0)
            part,spec = hconfig_info.group(1).split(',')
            logging.info(f"report_recorder - name of hardware part inside input html:{part,spec}")
            dict = analyzer.compare(part.strip(), spec.strip())
            hw_info_dict.update({spec.strip():dict})
            html_of_dict = dict_html_hardware(dict)
            html_data = html_data.replace(hconfig_placeholder, html_of_dict)
        html_data += "<p> </p>"
        html_data += convertTagList(data_loaded['hw_sw_info'].get('hardware_tags', []))
    if 'sw_config' in template_content:
        for sconfig_info in re.finditer(r'{sw_config}:(.+)', template_content):
            sconfig_placeholder = sconfig_info.group(0)
            sconfigs = sconfig_info.group(1).split(',')
            logging.info(f"report_recorder - name of software part inside input html:{sconfigs}")
            if sconfigs[0] == "swift_status":
                software_html = dict_html_software(analyzer.generate_all_swift_status(sconfigs[1]),sconfigs[0])
            else:
                # partitioning configs
                configs = analyzer.partitioning(analyzer.generate_confs(sconfigs[0], None if len(sconfigs) == 1 else sconfigs[1]), sconfigs[0] , f"{html_output}/unimportant_conf")  ### must set the correct directory
                software_html = dict_html_software(configs,sconfigs[0])
            html_data = html_data.replace(sconfig_placeholder, software_html)
            html_data += "<p> </p>"
            html_data += convertTagList(data_loaded['hw_sw_info'].get('software_tags', []))
    htmls_dict.update({page_title:html_data})
    if 'hw_config' in template_content:
        htmls_dict.update(sub_pages_maker(html_data, page_title, hw_info_dict, data_loaded))
    for html_key,html_value in htmls_dict.items():
        if "HW--" in html_key:
            with open(os.path.join(html_output+"/subpages/"+html_key+".html"), 'w') as html_file:
                html_file.write(html_value)
                print(f"HTML template saved to: {html_output+'/subpages/'+html_key+'.html'}") 
                logging.info(f"report_recorder - HTML template saved to: {html_output+'/subpages/'+html_key+'.html'}")
        else:
            with open(os.path.join(html_output+"/"+html_key+".html"), 'w') as html_file:
                html_file.write(html_value)
                print(f"HTML template saved to: {html_output+'/'+html_key+'.html'}") 
                logging.info(f"report_recorder - HTML template saved to: {html_output+'/'+html_key+'.html'}")
    return htmls_dict

def create_test_htmls(html_output, cluster_name, scenario_name, merged_file, merged_info_file, imgsdict, yamlConf): #page_title = cluster_name + scenario_name
    logging.info("report_recorder - Executing create_test_htmls function")
    move_images(imgsdict,os.path.join(html_output,'subpages/imgs'))
    tc = testClassification(infocsv=pd.read_csv(merged_info_file), detailcsv=pd.read_csv(merged_file), imgsdict=imgsdict, clusterName=cluster_name, scenarioName=scenario_name, conf=yamlConf)
    for page in tc.AllPagesHTML:
        pathPrefix = "subpages/"
        if page.title == f"{cluster_name}--{scenario_name}":
            pathPrefix = ""
        with open(os.path.join(html_output+"/"+pathPrefix+page.title+".html"), 'w') as html_file:
            page += convertTagList(yamlConf['tests_info'].get('test_tags', []))
            html_file.write(page.render())
            print(f"HTML template saved to: {html_output+'/'+pathPrefix+page.title+'.html'}") 
            logging.info(f"report_recorder - HTML template saved to: {html_output+'/'+pathPrefix+page.title+'.html'}") 
    return tc.AllPagesHTML

def sub_pages_maker(template_content , page_title ,hw_info_dict, data_loaded):
    logging.info("report_recorder - Executing sub_pages_maker function")
    global configs_dir
    htmls_list={}
    c_dir = configs_dir
    sub_dir_path = os.path.join(c_dir,'configs/{serverName}/hardware/')
    if page_title + "--CPU" in template_content:
        htmls_list.update({page_title + "--CPU":one_sub_page_maker(sub_dir_path+'cpu/',hw_info_dict['cpu'], data_loaded)})
    if page_title + "--Memory" in template_content:
        htmls_list.update({page_title + "--Memory":one_sub_page_maker(sub_dir_path+'memory/',hw_info_dict['memory'], data_loaded)})
    if page_title + "--Network" in template_content:
        htmls_list.update({page_title + "--Network":one_sub_page_maker(sub_dir_path+'net/',hw_info_dict['net'], data_loaded)})
    if page_title + "--Disk" in template_content:
        htmls_list.update({page_title + "--Disk":one_sub_page_maker(sub_dir_path+'disk/',hw_info_dict['disk'], data_loaded)})
    if page_title + "--PCI" in template_content:
        #htmls_list.update({page_title + "--PCI":sub_page_maker(sub_dir_path+'pci/',hw_info_dict['pci'])})
        htmls_list.update({page_title + "--PCI":one_sub_page_maker(sub_dir_path+'pci/',hw_info_dict['cpu'], data_loaded)})
    return htmls_list

def one_sub_page_maker(path_to_files, spec_dict, data_loaded):
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
                html_content += f"<br><syntaxhighlight lang='bash'>{''.join(file_contents)}</syntaxhighlight>"
            else:
                html_content += "<p> فایل مربوطه یافت نشد </p>"
    html_content += "<p> </p>"
    html_content += convertTagList(data_loaded['hw_sw_info'].get('hardware_tags',[]))
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
            href = href.replace('./subpages/', ' ', 1)
        elif href.startswith('./'):
            href = href.replace('./', ' ', 1)
        a_tag.replace_with(f"[[{href} |{a_tag.text}]]")
    # Convert <img> tags to wiki images
    for img_tag in soup.find_all('img'):
        if 'src' in img_tag.attrs:
            img_tag.replace_with(f"[[File:{os.path.basename(img_tag['src'])}|border|center|800px|{os.path.basename(img_tag['src'])}]]")
    # Remove <body>, <thead>, and <tbody> tags
    for tag_name in ['body', 'thead', 'tbody']:
        for tag in soup.find_all(tag_name):
            tag.unwrap()  # Remove the tag but keep its content
    return str(soup)

def check_data(site, title_content_dict, kateb_list, cluster_name, scenario_name):
    logging.info("report_recorder - Executing check_data function")
    delete_all = False
    skip_all = False
    titles_to_skip = []
    for title in list(title_content_dict.keys()):
        page = pywikibot.Page(site, title)
        if skip_all:
            # Skip existing pages if 'no all' is chosen
            if page.exists():
                logging.info(f"Skipping page '{title}' because 'no all' was chosen.")
                titles_to_skip.append(title)
                continue
            # Allow uploading new pages
            else:
                logging.info(f"New page '{title}' will be uploaded.")
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
    upload_data(site, title_content_dict, kateb_list, cluster_name, scenario_name)

def upload_data(site, title_content_dict, kateb_list, cluster_name, scenario_name):
    logging.info("report_recorder - Executing upload_data function")
    try:
        for title, content in title_content_dict.items():
            page = pywikibot.Page(site, title)
            page.text = content + '\n powered by KARA'
            page.save(summary="Uploaded by KARA", force=True, quiet=False, botflag=True)
            #page.save(" برچسب: [[مدیاویکی:Visualeditor-descriptionpagelink|ویرایش‌گر دیداری]]")
            logging.info(f"Page '{title}' uploaded successfully.")
    except pywikibot.exceptions.Error as e:
        logging.error(f"report_recorder - Error uploading page '{title}': {e}")
    if kateb_list:
        list_page_title = kateb_list 
        list_page = pywikibot.Page(site, list_page_title)
        # Check if the page exists
        if list_page.exists():
            # Get the current content of the page
            current_content = list_page.text
            # Define the new page name to append
            if scenario_name:
                text_to_append = f"\n* [[{cluster_name}--{scenario_name}|{cluster_name}--{scenario_name}]]"
            else:
                text_to_append = f"\n* [[{cluster_name}|{cluster_name}]]"
            if text_to_append not in current_content:
                new_content = current_content + text_to_append
                list_page.text = new_content
                list_page.save(summary="kara append new page title to this page", force=True, quiet=False, botflag=True)
                print(f"Successfully updated the page '{list_page_title}'")
        else:
            # Define the new page name to append
            if scenario_name:
                text_to_append = f"\n* [[{cluster_name}--{scenario_name}|{cluster_name}--{scenario_name}]]"
            else:
                text_to_append = f"\n* [[{cluster_name}|{cluster_name}]]"
            if text_to_append:
                list_page.text = text_to_append + '\n[[رده:فهرست]]\n'
                list_page.save(summary="Uploaded by KARA", force=True, quiet=False, botflag=True)
                print(f"Successfully updated the page '{list_page_title}'")
                
def upload_images(site, html_content, output_htmls_path):
    logging.info("report_recorder - Executing upload_images function")
    # Convert dominate document to string if needed
    if isinstance(html_content, document):
        html_content = html_content.render()
    elif not isinstance(html_content, str):
        html_content = str(html_content)
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
    except Exception as e:
        logging.error(f"Error parsing HTML content: {e}")
        raise

    # Extract image paths
    image_paths = [img['src'] for img in soup.find_all('img') if 'src' in img.attrs]
    # Upload each image
    for image_path in image_paths:
        if "./" in image_path:
            image_path = image_path.replace("./", f"{str(output_htmls_path)}/")
        image_filename = os.path.basename(image_path)
        page = pywikibot.FilePage(site, f'File:{image_filename}')
        # Check if the file already exists
        if page.exists():
            print(f"Image \033[91m'{image_filename}'\033[0m already exists on the wiki.")
            logging.info(f"report_recorder - Image '{image_filename}' already exists on the wiki. Skipping upload.")
            continue

        # Attempt to upload the image
        try:
            success = page.upload(image_path, comment=f"Uploaded image '{image_filename}' by KARA", ignore_warnings=True)
            if success:
                print(f"File \033[1;33m'{image_filename}'\033[0m uploaded successfully!")
                logging.info(f"report_recorder - Image '{image_filename}' uploaded successfully.")
            else:
                print(f"\033[91mFailed to upload image '{image_filename}'\033[0m")
                logging.warning(f"report_recorder - Failed to upload image '{image_filename}'.")
        except Exception as upload_error:
            logging.error(f"Error uploading image '{image_filename}': {upload_error}")
            print(f"\033[91mError uploading image '{image_filename}'\033[0m")

def convertTagList(tagList):
    tagstr = ""
    for tag in tagList:
        tagstr +=f"[[رده:{tag}]]\n"
    return tagstr

def main(software_template, hardware_template, output_htmls_path, cluster_name, scenario_name, configs_directory, upload_operation, create_html_operation, merged_file, merged_info_file, create_test_page, kateb_list, img_path_or_dict):
    global configs_dir
    htmls_dict = {}
    imgsdict = {}
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
        cluster_name = data_loaded.get('cluster_name')
    if scenario_name is None:
        scenario_name = data_loaded.get('scenario_name')
    if output_htmls_path is None:
        output_htmls_path = data_loaded['output_path']
    if merged_file is None:
        merged_file = data_loaded['tests_info']['merged']
    if merged_info_file is None:
        merged_info_file = data_loaded['tests_info']['merged_info']
    if output_htmls_path is None:
        output_htmls_path = data_loaded['output_path']

    if not os.path.exists(os.path.join(output_htmls_path+"/subpages/imgs/")):
        subprocess.run(f"mkdir -p {output_htmls_path}/subpages/imgs/", shell=True)

    if configs_directory is None:
        configs_directory = data_loaded['hw_sw_info']['configs_dir']
    if software_template is None:
        if 'software_template' in data_loaded['hw_sw_info']:
            software_template = data_loaded['hw_sw_info']['software_template']
        else:
            software_template = None

    if hardware_template is None:
        if 'hardware_template' in data_loaded['hw_sw_info']:
            hardware_template = data_loaded['hw_sw_info']['hardware_template']
        else:
            hardware_template = None

    if kateb_list is None:
        if 'kateb_list_page' in data_loaded:
            kateb_list = data_loaded['kateb_list_page']
        else:
            kateb_list = None
    
    if img_path_or_dict is None:
        if 'images_path'in data_loaded['tests_info']:
            img_path_or_dict = data_loaded['tests_info']['images_path']
        else:
            print('for make tests htmls with images you need "images_path" if config file or a dictionary from status_reporter')
            exit()

    if isinstance(img_path_or_dict, str) and os.path.isdir(img_path_or_dict):
        imgsdict = path_to_dict(img_path_or_dict)
    elif isinstance(img_path_or_dict, dict):
        imgsdict = img_path_or_dict
        
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
            scenario_pages = create_test_htmls(output_htmls_path, cluster_name, scenario_name, merged_file, merged_info_file, imgsdict, data_loaded)
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
            upload_images(site, content, output_htmls_path)
        if create_test_page:
            for page in scenario_pages:
                wiki_content = convert_html_to_wiki(page.body)
                title_content_dict[page.title] = wiki_content
                # Upload images to the wiki
                upload_images(site, page.body, output_htmls_path)
        # Upload converted data to the wiki
        check_data(site, title_content_dict, kateb_list, cluster_name, scenario_name)
    logging.info("\033[92m****** report_recorder main function end ******\033[0m")

################# temp code of daily report ##################################
def convert_to_shamsi(miladi_date):
    shamsi = {}
    shamsi['y'] = int(miladi_date.split('-')[0])
    shamsi['m'] = int(miladi_date.split('-')[1])
    shamsi['d'] = int(miladi_date.split('-')[2])
    shamsi_date = jdatetime.date.fromgregorian(day=shamsi['d'],month=shamsi['m'],year=shamsi['y'])
    shamsi_date_str = shamsi_date.strftime("%Y-%m-%d")
    return shamsi_date_str

def create_daily_html(dfdict,imgsdict,output_dir,timeVariable,cluster_name,report_time,start_date,end_date,start_time,end_time):
    pageHTML = dominate.document(title=f'title')
    with pageHTML:
        p(raw(f"در این سند گزارش روزانه کلاستر {cluster_name} در بازه زمانی از تاریخ <span dir='rtl'>{start_date}</span>  ساعت <span dir='rtl'>{report_time.split('__')[0].split('_')[1]}</span> تا تاریخ <span dir='rtl'>{end_date}</span> ساعت <span dir='rtl'>{report_time.split('__')[1].split('_')[1]}</span> آورده شده است.<br>"))#, dir="rtl"
        h2(f"نتایج گزارش روزانه در یک نگاه", dir="rtl")
        for group,csv in dfdict.items():
            h3(f"{group}", dir="rtl")
            with div():
                csv.columns = csv.columns.str.replace(r'_.*?\.', '.', 1,regex=True)
                csv.columns = csv.columns.str.replace('.', ' .', regex=False)
                csv = csv.round(2)
                raw(csv.dropna(axis=1, how='all').to_html(index=False, border=2))
        if (imgsdict[report_time][list(imgsdict[report_time].keys())[0]]):
            h2(f"داشبوردهای گرافانا با تایم فریم {timeVariable}", dir="rtl")
            for group,hosts in imgsdict[report_time].items():
                h3(f"{group}", dir="rtl")
                for host,dashboards in hosts.items():
                    h4(f"{host}", dir="rtl")
                    for dashboard,imgList in dashboards.items():
                        h5(dashboard, dir="rtl")
                        for image in imgList:
                            img(src=f"./imgs/{image}", alt=f"Daily-{cluster_name}-{image}")
    return pageHTML

def main2(output_dir, cluster_name, kateb_list, kateb_tags, csv_address, imgsdict, timeVariable):

    report_time = str(list(imgsdict.keys())[0])
    start_date = convert_to_shamsi(report_time.split('__')[0].split('_')[0])
    end_date = convert_to_shamsi(report_time.split('__')[1].split('_')[0])
    start_time = report_time.split('__')[0].split('_')[1]
    end_time = report_time.split('__')[1].split('_')[1]
    
    title = f"{cluster_name}:گزارش وضعیت کلاستر from {start_date}_{start_time} to {end_date}_{end_time}"
    if not os.path.exists(os.path.join(output_dir+"/imgs/")):
        subprocess.run(f"mkdir -p {output_dir}/imgs/", shell=True)
    move_images(imgsdict,os.path.join(output_dir,'imgs'))
    dfdict = {}
    for group,csv_path in csv_address.items():
        dfdict[group] = pd.read_csv(csv_path)
    content = create_daily_html(dfdict,imgsdict,output_dir,timeVariable,cluster_name,report_time,start_date,end_date,start_time,end_time)
    with open(os.path.join(output_dir,f"{title}.html"),'w') as f:
        f.write(content.render())
    site = pywikibot.Site()
    site.login()
    title_content_dict = {}
    wiki_content = convert_html_to_wiki(str(content.body)+convertTagList(kateb_tags))
    title_content_dict[title] = wiki_content
    upload_images(site, content, output_dir)
    check_data(site, title_content_dict, kateb_list, title, scenario_name=None)

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
    parser.add_argument("-kl", "--kateb_list", help="title of kateb page include list of pages")
    parser.add_argument("-img", "--img_path_or_dict", help="title of kateb page include list of pages")
    args = parser.parse_args()
    software_template = args.software_template 
    hardware_template = args.hardware_template 
    output_htmls_path = args.output_htmls_path if args.output_htmls_path else None
    cluster_name = args.cluster_name if args.cluster_name else None
    scenario_name = args.scenario_name if args.scenario_name else None
    merged_file = args.merged_file if args.merged_file else None
    merged_info_file = args.merged_info_file if args.merged_info_file else None
    configs_directory = args.configs_directory if args.configs_directory else None
    upload_operation = args.upload_operation
    create_html_operation = args.create_html_operation
    create_test_page = args.create_test_page
    kateb_list = args.kateb_list
    img_path_or_dict = args.img_path_or_dict
    main(software_template, hardware_template, output_htmls_path, cluster_name, scenario_name, configs_directory, upload_operation, create_html_operation, merged_file, merged_info_file, create_test_page, kateb_list, img_path_or_dict)
