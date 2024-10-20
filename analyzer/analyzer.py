import os
import re
import sys
import yaml
import subprocess
import logging
import argparse
import configparser
from glob import glob
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter

# variables
log_path = "/var/log/kara/"
config_file = "/etc/kara/analyzer.conf"

BOLD = "\033[1m"
RESET = "\033[0m"
YELLOW = "\033[1;33m"

def load_config(config_file):
    with open(config_file, "r") as stream:
        try:
            data_loaded = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(f"Error loading the configuration: {exc}")
            sys.exit(1)
    return data_loaded
    
def conf_dir(config_dir):
    global configs_dir
    configs_dir = config_dir
    return configs_dir

# read backup dir
listOfServers = []
def load(directory):
    with open(configs_dir + directory, 'r') as f:
        content = f.readlines()
    return content

#### HARDWARE info ####
# dmidecode -t 1
def generate_brand_model(serverName):
    manufacturer = ""
    productName = ""
    for line in load(f'/configs/{serverName}'+"/hardware/server-manufacturer/dmidecode.txt"):
        if "Manufacturer" in line:
            manufacturer = line.split(":")[1].replace("\n" , "")
        if "Product Name" in line:
            productName = line.split(":")[1].replace("\n" , "")
    return manufacturer + productName

# lscpu
def generate_cpu_model(serverName):
    coresPerSocket = ""
    socket = ""
    threads = ""
    model = ""
    for line in load(f'/configs/{serverName}'+"/hardware/cpu/lscpu.txt"):
        line = line.replace("\n","").split(":")
        if "Core(s) per socket" in line[0]:
            coresPerSocket=line[1].strip()
            #print ("("+  coresPerSocket+ ")")
        if "Socket(s)" in line[0]:
            socket=line[1].strip()
        if "Thread(s) per core" in line[0]:
            threads = line[1].strip()
        if "Model name" in line[0]:
            model = line[1].strip()
    return coresPerSocket + "xcores x " + socket + "xsockets x " + threads + "xthreads " + model

# lshw -short -C memory
def generate_memory_model(serverName):
    rams=[]
    for line in load(f'/configs/{serverName}'+"/hardware/memory/lshw-brief.txt"):
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
    Flag = False
    nets=[]
    capacities = []
    for line in load(f'/configs/{serverName}'+"/hardware/net/lshw-json.txt"):
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
    manufacturer = ""
    productName = ""
    for line in load(f'/configs/{serverName}'+"/hardware/motherboard/dmidecode.txt"):
        if "Manufacturer" in line:
            manufacturer = line.split(":")[1].replace("\n", "")
        if "Product Name" in line:
            productName = line.split(":")[1].replace("\n", "")
    return manufacturer + productName

# lshw -C disk
def generate_disk_model(serverName):
    disks= []
    with open(f'{configs_dir}/configs/{serverName}'+"/hardware/disk/lshw.txt",'r') as f:
        diskList = f.read().split("*-")
    for i in range (1,len(diskList)):
        if not("size:" in diskList[i]):
            continue 
        diskname=""
        for x in diskList[i].splitlines():
            if "description:" in x or "product:" in x:
                diskname+=x.split(":")[1].strip() + " "
            elif "size:" in x:
                diskname+=x.split("(")[1].split(")")[0] + " "
        disks.append(diskname)
    counts = Counter(disks)
    disksNames =""
    for item, count in counts.items():
        disksNames += str(count) + "x" + item + "\n"
    return disksNames

def generate_model(server, part, spec):
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
    
def compare(part, spec):
    listOfServers = get_list_of_servers()
    dict = {}
    for server in listOfServers:
        model= generate_model(server ,part ,spec)
        if model in dict:
            if dict[model] is None:
                dict[model] = []
        else: dict[model]= []
        dict[model].append(server)
    return dict

#### SOFTWARE info ####
def get_list_of_servers():
    cmd = ["ls", f'{configs_dir}/configs/']
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    global listOfServers
    listOfServers = result.stdout.split("\n")
    listOfServers.pop()
    return listOfServers

def compare_confs (confsOfServers, confType):
    commonConf = confsOfServers[listOfServers[0]]
    allConfs = {}
    for server in listOfServers:
        commonConf = get_commonConf(commonConf , confsOfServers[server], confType)
    for server in listOfServers:
        uncommonconfs = get_uncommonConf(confsOfServers[server], commonConf, confType)
        if len(uncommonconfs) != 0:
            allConfs[server] = uncommonconfs
    if len(commonConf) != 0:
        allConfs["All(common confs)"] = commonConf
    if confType == "server_confs":
        allConfs = convert_dict_to_list(allConfs)
    return allConfs  #####  dict of list of strings

def convert_dict_to_list (allconfs):
    newdict = {}
    for server in allconfs:
        nlist = []
        for confs in allconfs[server]:
            nlist.append(confs)
            nlist = nlist + list(allconfs[server][confs])
        newdict[server] = nlist
    return newdict

def get_commonConf (conf1, conf2, confType):
    if confType != "server_confs":
        return set(conf1) & set(conf2)
    else:
        commonConf = {}
        for section in conf2:
            if section in conf1:
                common = set(conf1[section]) & set(conf2[section])
                if len(common)!= 0:
                    commonConf[section] = common
        return commonConf

def get_uncommonConf (conf1, conf2, confType):
    if confType != "server_confs":
        return set(conf1) - conf2
    else:
        uncommonConf = {}
        for section in conf1:
            if section in conf2:
                uncommon = set (conf1[section]) - conf2[section]
                if len(uncommon)!= 0:
                    uncommonConf[section] = uncommon
            else:
                uncommonConf[section] = conf1[section]
        return uncommonConf

def generate_swift_status(servername):
    listOfDowns = []
    for line in load(f"/configs/{servername}/software/swift/services/{servername}-swift-status.txt"):
        if "No" in line:
            listOfDowns.append(line.split("No ")[1].replace("\n", "").split(" running")[0])
    return listOfDowns

def generate_all_swift_status(services):
    listOfServices = []
    if services == "main":
        listOfServices= ["proxy-server" , "object-server" , "account-server" , "container-server"]
    if services == "object":
        listOfServices = ["object-auditor" , "object-reconstructor" , "object-replicator" , "object-updater" , "object-expirer"]
    if services == "account":
        listOfServices = ["account-replicator" , "account-auditor"  , "account-reaper"]
    if services == "container":
        listOfServices = ["container-updater" , "container-auditor" , "container-replicator" , "container-sharder" , "container-sync"]
    returndict={}
    returndict ["servers"] = listOfServices
    for server in listOfServers:
        returndict[server] = []
        listOfDownServices = generate_swift_status(server)
        for service in listOfServices:
            if service in listOfDownServices:
                returndict[server].append( "Down" ) #### returndict[server].append([service , "Down"])
            else:
                returndict[server].append( "UP" ) ####  returndict[server].append([service , "UP"])
    return returndict   ####### dict of list of stirng

def generate_ring (servername, serverType):
    with open (configs_dir + "/configs/" + servername + "/software/swift/rings/" + servername + "-" + serverType + "-ring.txt", "r") as file:
        x = file.read()
    ring_item_dic = {}
    ring_item = []
    ring_item_dic["Ring." + serverType + ".nodes"] = len(set([v.split()[3] for v in x.splitlines()[6:]]))
    ring_item_dic.update({"Ring." + serverType + "." + item.split(" ")[1]: item.split(" ")[0] for item in x.splitlines()[1].split(", ")[:5]})
    for key , value in ring_item_dic.items():
        ring_item.append(key + " = " + str(value))
    return ring_item

def extract_ini_file (server, serverType):
    # Read the file into a variable
    file_path = configs_dir + "/configs/" + server + "/software/swift/server-confs/" + server + "-" + serverType + "-server.conf"
    with open(file_path, 'r') as file:
        file_content = file.read()
    # Replace [DEFAULT] with [default] for fix repeating 
    modified_content = file_content.replace("[DEFAULT]", "[default]")
    config = configparser.ConfigParser()
    config.read_string(modified_content)
    confs = {}
    for section in config.sections():
        confs["["+section+"]"] = []
        for key , value in config.items(section):
            confs["["+section+"]"].append(key + " = " + value)
        if confs["["+section+"]"] == []:
            confs["["+section+"]"] = ["empty"]
    return confs

def get_conf (server, confType, serverType = None):
    conf = []
    if confType == "server_confs":
        conf = extract_ini_file (server , serverType)
    if confType == "software_version":
        conf= [i.replace("\n", "") for i in load("/configs/" + server + "/software/system/images-version.txt") if i != "\n"]
    if confType == "sysctl":
        conf = [i.replace("\n" , "") for i in load ("/configs/" + server + "/software/system/sysctl.txt") if i != "\n"]
        pattern_replacements = [(r'br-.*?\.', 'br-.'),(r'veth.*?\.', 'veth.'),(r'enp.*?\.', 'enp.'),(r'tap.*?\.', 'tap.')]
        for i in range(len(conf)):
            for pattern, replacement in pattern_replacements:
                conf[i] = re.sub(pattern, replacement, conf[i])
    if confType == "systemctl":
        conf = [" ".join(i.replace("  " , "").split(" ")[:3]) for i in load ("/configs/" + server + "/software/system/systemctl.txt") if i != "\n"]
    if confType == "lsof":
        conf = [i.replace("\n" , "") for i in load ("/configs/" + server + "/software/system/lsof.txt") if i != "\n"]
    if confType == "lsmod":
        conf = [i.replace("  ", " ").replace("\n", "") for i in load("/configs/" + server + "/software/system/lsmod.txt") if i != "\n"]
        for i in range(len(conf)):
            last_space_index = conf[i].rfind(' ')
            if not conf[i][last_space_index+1:].isdigit():
                conf[i] = conf[i][:last_space_index] + " (" + conf[i][last_space_index+1:] + ")"
    if confType == "rings":
        conf = generate_ring(server, serverType)
    return conf

def generate_confs (confType, serverType = None):
    confOfServers = {}
    for server in listOfServers:
        confOfServers[server] =  get_conf(server, confType , serverType)
    compared_dict = compare_confs(confOfServers , confType)
    compared_dict ["servers"] = confType + "  " + (serverType if serverType != None else "")
    return compared_dict

def partitioning (confOfServers , confType , unimportantconfDir):
    if os.path.exists(unimportantconfDir+"/"+confType+"-Unimportant_conf.txt"):
        with open( unimportantconfDir+"/"+confType+"-Unimportant_conf.txt", 'r') as f:
            unimportantConfs = f.readlines() # reads list of important configs here
        unimportantConfs = [unimportantConf.strip() for unimportantConf in unimportantConfs]  # to remove /n at the end of lines
        for server in listOfServers:
            if server in confOfServers:
                unImportantList = []
                importantList = list (confOfServers[server])

                for conf in confOfServers[server]:  # searches to find important configs in all configs of server
                    for unimportantConf in unimportantConfs:
                        if unimportantConf in conf:
                            unImportantList.append(conf)
                            importantList.remove(conf)
                finalList = []
                if len(importantList) !=0:
                    finalList = ["************* Important Confs *************" ]
                    finalList = finalList + importantList
                if len(unImportantList) != 0:
                    finalList.append("************* Other Confs *************")
                    finalList.extend(unImportantList)
                confOfServers[server] = finalList
    return confOfServers

####### MERGER #######
def merge_csv(csv_file, output_directory, mergedinfo_dict, merged_dict):
    logging.info("status_analyzer - Executing merge_csv function")
    try:
        csv_data = pd.read_csv(csv_file)
        if mergedinfo_dict:  
            if os.path.exists(f'{output_directory}/merged_info.csv'):
                merged_info = pd.concat([pd.read_csv(f'{output_directory}/merged_info.csv'), pd.DataFrame(mergedinfo_dict, index=[0])], ignore_index=True).drop_duplicates()
            else:
                merged_info = pd.DataFrame(mergedinfo_dict, index=[0])
            merged_info.to_csv(f'{output_directory}/merged_info.csv', index=False, mode='w')
            print(f"Data from test appended successfully to {YELLOW}'{output_directory}/merged_info.csv'{RESET}")
        if merged_dict:
            for key, value in merged_dict.items():
                csv_data.insert(0, key, value) 
        if os.path.exists(f'{output_directory}/merged.csv'):
            merged = pd.concat([pd.read_csv(f'{output_directory}/merged.csv'), csv_data], ignore_index=True).drop_duplicates()
        else:
            merged = csv_data
        merged.to_csv(f'{output_directory}/merged.csv', index=False, mode='w')
        print(f"Data from '{csv_file}' appended successfully to {YELLOW}'{output_directory}/merged.csv'{RESET}") 
        print("")
        logging.info(f"status_analyzer - Data from '{csv_file}' appended successfully to '{output_directory}/merged.csv'") 
    except FileNotFoundError:
        logging.info(f"status_analyzer - File '{csv_file}' not found. Skipping")
        print(f"File '{csv_file}' not found. Skipping...")
    return f'{output_directory}/merged.csv'

def merge_process(output_directory, selected_CSVs):
    logging.info("status_analyzer - Executing merge_process function")
    if '*' in selected_CSVs:    
        selected_CSVs = glob(selected_CSVs)
        for file in selected_CSVs:
            merged_file = merge_csv(file, output_directory, mergedinfo_dict=None, merged_dict=None)
    else:
        for file in selected_CSVs:
            if os.path.exists(file):
                merged_file = merge_csv(file, output_directory, mergedinfo_dict=None, merged_dict=None)
            else:
                print(f"\033[91mThis CSV file doesn't exist:\033[0m{file}")
                logging.info(f"status_analyzer - This CSV file doesn't exist:{file}")
                exit(1)
    return merged_file
                
####### ANALYZER #######
def make_all_row(source_csv, row_operations, all_row_data):
    for operation in row_operations:
        row_data = {}
        for column in source_csv.columns:
            if column != "Host_name" and column != "cosbench.run_time":
                if operation == 'sum':
                    row_data[column] = source_csv[column].sum()
                elif operation == 'avg':
                    row_data[column] = source_csv[column].mean()
        row_data['Host_name'] = operation.upper()
        all_row_data[operation] = row_data
    return all_row_data

def process_csv_file(source_csv, operation, new_column_name, selected_columns):
    logging.info("Executing status_analyzer process_csv_file function")
    if operation == 'sum':
        new_column_name = f"sum.{new_column_name}"
        source_csv[new_column_name] = source_csv[selected_columns].sum(axis=1)
    elif operation == 'avg':
        new_column_name = f"avg.{new_column_name}"
        source_csv[new_column_name] = source_csv[selected_columns].mean(axis=1)
    elif operation == 'mul':
        new_column_name = f"mul.{new_column_name}"
        result = 1
        for selected_col in selected_columns:
            if isinstance(selected_col, (int, float)):
                result *= selected_col  # Multiply by the constant
            elif selected_col in source_csv.columns:
                result *= source_csv[selected_col]  # Multiply by the column values
            else:
                print(f"\033[91mColumn\033[0m '{selected_col}' \033[91mdoes not exist in the CSV file or it's type is not number!\033[0m")
                exit()
        source_csv[new_column_name] = result
    elif operation == 'div':
        new_column_name = f"div.{new_column_name}"
        if len(selected_columns) == 2:
            source_csv[new_column_name] = source_csv[selected_columns[0]] / source_csv[selected_columns[1]]
        else:
            print("\033[91mDivision requires exactly two selected columns\033[0m")
    return source_csv

def analyze_and_save_csv(csv_original, keep_column, output_directory, data_loaded):
    logging.info("status_analyzer - Executing analyze_and_save_csv function")
    source_csv = pd.read_csv(csv_original, usecols=lambda column: column.strip() != "")
    selected_column_names = set()
    all_row_data = {}
    for section_name, content in data_loaded['transformation'].items():
        if 'csv' in section_name:
            final_output_csv_name = f"{os.path.splitext(os.path.basename(csv_original))[0]}_analyzed.csv"
            final_output_csv_path = os.path.join(output_directory, final_output_csv_name)
            if 'columns' in content:
                for new_column_name, column_content in content.get('columns', {}).items():
                    operation = column_content['operation']
                    selected_columns = [line for line in column_content.get('selected_columns', [])]
                    if not operation or not selected_columns:
                        print(f"\033[91moperation or selected columns missing for transformation in file {final_output_csv_name} \033[0m")
                        exit()
                    # Ensure that all selected columns exist before creating the new column
                    missing_columns = [col for col in selected_columns if col not in source_csv.columns]
                    if missing_columns:
                        for miss_col in missing_columns:
                            if not isinstance(miss_col, (int, float)):
                                print(f"\033[91mSelected columns missing:\033[0m {missing_columns} \033[91mfor new column\033[0m '{new_column_name}'")
                    source_csv = process_csv_file(source_csv, operation, new_column_name, selected_columns)
                    selected_column_names.update(selected_columns)
            # Process 'rows' section for operations on all columns
            row_operations = content.get('rows', [])
            if row_operations:
                all_row_data = make_all_row(source_csv, row_operations, all_row_data)
                for operation, row_data in all_row_data.items():
                    all_row = pd.DataFrame([row_data])
                    source_csv = pd.concat([source_csv, all_row], ignore_index=True)
            if keep_column:
                csv_final = source_csv
            else:
                keep_columns = [col for col in source_csv.columns if col not in selected_column_names]
                csv_final = source_csv[keep_columns]
    csv_final.to_csv(final_output_csv_path, index=False)
    print(f"\n{BOLD}Analyzed CSV file:{RESET}{YELLOW} '{final_output_csv_path}' {RESET}{BOLD}has been created with the extracted values.{RESET}\n")
    return final_output_csv_path

###### Make graph and image ######
def plot_and_save_graph(csv_original, output_directory, data_loaded):
    logging.info("status_analyzer - Executing plot_and_save_graph function")
    csv_data = pd.read_csv(csv_original, usecols=lambda column: column.strip() != "")
    image_dict = {}
    for group_name, group_data in data_loaded['transformation']['graph'].items():
        filter_data = group_data.get('filter', {})
        selected_columns = group_data.get('selected_columns', [])
        temp_csv = csv_data
        for filter_column, filter_values in filter_data.items():
            if filter_column in temp_csv.columns:
                temp_csv = temp_csv[temp_csv[filter_column].isin(filter_values)]
        for column_pair in selected_columns:
            for x_column, y_column in column_pair.items():
                if x_column in temp_csv.columns and y_column in temp_csv.columns:
                    # Extract x and y values from DataFrame
                    x_values = temp_csv[x_column]
                    y_values = temp_csv[y_column]
                    # Plot the data
                    plt.plot(x_values, y_values, marker='o')
                    # Set plot labels and title
                    plt.xlabel(x_column)
                    plt.ylabel(y_column)
                    title = f"name of csv: {os.path.basename(csv_original).replace('.csv', ' ')}"
                    plt.title(title)
                    plt.grid(True)
                    plt.tight_layout()
                    image_name = os.path.basename(csv_original).replace('.csv', f'_{group_name}_{x_column}_{y_column}.png')
                    image_file_path = os.path.join(output_directory, image_name)
                    plt.savefig(image_file_path)
                    print(f"{YELLOW}image of analyzed graph save:{RESET} {BOLD}'{image_file_path}'{RESET}")
                    image_dict[image_name] = image_file_path
                    plt.clf()
                else:
                    print(f"\033[91mcheck config file, mybe these seleceted columns are not existed on csv file:\033[0m '{x_column}' \033[91mand\033[0m '{y_column}'  \033[91mso graph of them can't create!\033[0m")
    return image_dict

def main(merge, analyze, graph, csv_original, output_directory, selected_CSVs, keep_column):
    data_loaded = load_config(config_file)
    log_level = data_loaded['log'].get('level')
    if log_level is not None:
        log_level_upper = log_level.upper()
        valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if log_level_upper in valid_log_levels:
            log_maker = subprocess.run(f"sudo mkdir {log_path} > /dev/null 2>&1 && sudo chmod -R 777 {log_path}", shell=True)
            logging.basicConfig(filename= f'{log_path}all.log', level=log_level_upper, format='%(asctime)s - %(levelname)s - %(message)s')
        else:
            print(f"\033[91mInvalid log level:{log_level}\033[0m")  
    else:
        print(f"\033[91mPlease enter log_level in the configuration file.\033[0m")
    logging.info("\033[92m****** status_analyzer main function start ******\033[0m")
    if output_directory is None:
        output_directory = data_loaded['output_path']
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    if analyze:
        final_output_csv_path = analyze_and_save_csv(csv_original, keep_column, output_directory, data_loaded)
    if merge:
        merged_file = merge_process(output_directory, selected_CSVs)
    if graph: 
        plot_and_save_graph(csv_original, output_directory, data_loaded)
    logging.info("\033[92m****** status_analyzer main function end ******\033[0m")
    return final_output_csv_path
           
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Perform CSV operations and merge files.')
    parser.add_argument('-M', '--merge', action='store_true', help='Merge CSV files')
    parser.add_argument('-o', '--output_directory', help='Path to the directory containing CSV files or output for merged csv file (required for -M)')
    parser.add_argument('-sc', '--selected_CSVs', help='Name of the selected CSV files or "*.csv" (required for -M)')
    parser.add_argument('-A', '--analyze', action='store_true', help='Analyze CSV files')
    parser.add_argument('-c', '--csv_org', help='Custom CSV file for analysis (required for -A)')
    parser.add_argument('-k', '--keep_column', action='store_true', help='keep column of orginal_CSV file')
    parser.add_argument('-G', '--graph', action='store_true', help='make graph of CSV file')
    args = parser.parse_args()
    # Check required arguments based on operation
    if args.merge and (args.output_directory is None or args.selected_CSVs is None):
        print("Error: Both -o (--input_directory) and -sc (--selected_CSVs) switches are required for merge operation -M")
        exit(1)
    if args.analyze and (args.csv_org is None):
        print("Error: -c (--csv_org) switche is required for analyze operation -A")
        exit(1)
    if args.graph and (args.csv_org is None and args.output_directory is None):
        print("Error: these switchs sc (--csv_org) and -o (--output_directory) are required for make graph operation -G")
        exit(1)
    # Set values to None if not provided
    merge = args.merge ; analyze = args.analyze ; keep_column = args.keep_column ; graph = args.graph
    csv_original = args.csv_org.strip() if args.csv_org else None
    output_directory = args.output_directory.strip() if args.output_directory else None
    selected_CSVs = args.selected_CSVs if args.selected_CSVs else None
    if merge:
        if selected_CSVs:
            if '*' in selected_CSVs:
                selected_CSVs = args.selected_CSVs.strip()
            else:
                selected_CSVs = args.selected_CSVs.split(',')         
        else:
            selected_CSVs = None
            print(f'\033[91mplease select correct csv file your file is wrong: {args.selected_csv}\033[0m')
            exit(1)
    main(merge, analyze, graph, csv_original, output_directory, selected_CSVs, keep_column)