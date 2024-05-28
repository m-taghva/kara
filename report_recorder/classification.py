import yaml
import itertools
import csv
import pandas as pd
import os

################# CSV to sorted yaml descending-based ###########################################################################

def create_tests_details(mergedTestsInfo,mergedTests,test_group,array_of_parameters,tests_dir):
    img_metrics = ['netdata_disk_sdb_writes_mean','netdata_statsd_timer_swift_object_server_put_timing_events_mean']
    html_result =  f"<p> در این سند جزئیات مربوط به تست های گروه {test_group} آمده است</p>"
    serverList = unique_values = mergedTests['Host_alias'].unique().tolist()
    for testInfo in array_of_parameters:
        testGroup = ' , '.join(f'{key} = {value}' for key, value in testInfo.items())
        for serverName in serverList:
            mergedTestsInfo2 = mergedTestsInfo
            mergedTests2 = mergedTests 
            mergedTests2 = mergedTests2[mergedTests2['Host_alias'] == serverName ]
            for key, value in testInfo.items():
                mergedTestsInfo2 = mergedTestsInfo2[mergedTestsInfo2[key] == int(value) ]
                mergedTestsInfo2 = mergedTestsInfo2.drop(columns=key)
                mergedTests2 = mergedTests2[mergedTests2[key] == int(value) ]
                mergedTests2 = mergedTests2.drop(columns=key)
            if mergedTestsInfo2.empty:
                break
            else:
                html_result+= f"<h2> نتایج تست های گروه: {testGroup} </h2>"
                html_result+= f"<h3> نتایج سرور: {serverName} </h3>"
            mergedTestsInfo2.reset_index()
            test_rows = [pd.DataFrame([row], columns=mergedTestsInfo2.columns) for _, row in mergedTestsInfo2.iterrows()]
            for test in test_rows:
                trow = test.iloc[0]
                row_dict = trow.to_dict()
                selected_merged = mergedTests2.loc[mergedTests2['Time'] == row_dict['Time']]
                html_result+= f"<h4> نتایج تست : {row_dict} </h4>"
                html_result+= "<table border='1' class='wikitable'>\n"
                for i, row in enumerate(selected_merged.to_csv().split("\n")):
                    html_result += "<tr>\n"
                    tag = "th" if i == 0 else "td"
                    for j , column in enumerate(row.split(",")):
                        if j:
                            html_result += f"<{tag}>{column}</{tag}>\n"
                    html_result += "</tr>\n"
                html_result += "</table>"
                html_result += "<h4>تصاویر \n</h4> <p> </p>"
                directory_path = os.path.join(tests_dir,f"{row_dict['Time']}/query_results/{serverName}-images")
                for img in img_metrics:
                    if os.path.exists(directory_path):
                        for filename in os.listdir(directory_path):
                            if img in filename:
                                img_addr = os.path.join(directory_path,filename)
                                html_result += f"<img src={img_addr}>"   
                    else:
                        print(f"Directory {directory_path} does not exist for inserting images into kateb.")
            html_result +=  f"<h3> خلاصه و جمع بندی</h3>" 
            html_result+= "<table border='1' class='wikitable'>\n"
            for i, row in enumerate(mergedTests2.to_csv().split("\n")):
                html_result += "<tr>\n"
                tag = "th" if i == 0 else "td"
                for j , column in enumerate(row.split(",")):
                    if j:
                        html_result += f"<{tag}>{column}</{tag}>\n"
                html_result += "</tr>\n"
            html_result += "</table>"    
    return html_result

##########################################################################################################
def csv_to_sorted_yaml(merged_info_file):
    unique_values = {}
    with open(merged_info_file, 'r') as f:
        reader = csv.reader(f)
        headers = next(reader)  # Skip the header row   
        # Initialize sets for each column except the first
        for header in headers[1:]:
            unique_values[header] = set()    
        for row in reader:
            for i, value in enumerate(row[1:], start=1):  # Skip the first column
                unique_values[headers[i]].add(int(value) if value.isdigit() else value)
    # Convert sets to lists for YAML serialization
    for key in unique_values:
        unique_values[key] = list(unique_values[key]) 
    unique_file = f'unique_yaml_{os.path.basename(merged_info_file)}.yaml'
    with open(unique_file, 'w') as f:
        yaml.dump(unique_values, f, default_flow_style=False, sort_keys=False)
    #print(f"Unique values written to {unique_file}")
    with open(unique_file, 'r') as f:
        yaml_data = yaml.safe_load(f)
    # Convert the dictionary into a list of tuples (key, value) where the value is the length of the associated list
    sorted_data = dict(sorted(yaml_data.items(), key=lambda x: len(x[1]), reverse=True))
    sorted_file = f'sorted_yaml_{os.path.basename(merged_info_file)}.yaml'
    with open(sorted_file, 'w') as f:
        yaml.dump(sorted_data,f,sort_keys=False)
    #print(f"YAML file sorted based on number of values in descending order in {sorted_file}")
    return sorted_file

#######################################################################################################

def generate_combinations(yaml_data):
    values_lists = list(yaml_data.values())
    # Generate all possible combinations of values from the lists
    combinations = list(itertools.product(*values_lists))
    return combinations

########################################################################################################
# yaml reader
def yaml_reader(input):
    with open(input, 'r') as yaml_file:
        yaml_data = yaml.safe_load(yaml_file)
    return yaml_data
########################################################################################################

def group_generator (yaml_data,threshold):
    keys_list = list(yaml_data.keys())
    result=1
    j=1
    if (len(keys_list)==1):
        j=0
    else:
        for i in range(len(keys_list)):
            key = keys_list[i]
            result*=len(yaml_data[key])
            j = i
            if result > threshold:
                #print ("j first is: ", j)
                break       
    #print (f"j is the index of group breaker: {j}, result is {result} ")
    keys_list1 = list(yaml_data.keys())
    # Define the range from 0 to i (inclusive)
    start_index = j 
    end_index = len(yaml_data.keys())
    # Get the sublist of keys
    sublist = keys_list1[start_index:end_index]
    new_yaml_data = {key: yaml_data[key] for key in sublist}
    with open('from_threshold_to_end.yaml', 'w') as f:
        yaml.dump(new_yaml_data, f, default_flow_style=False,sort_keys=False)
    with open('from_threshold_to_end.yaml', 'r') as yaml_file:
        yaml_data1 = yaml.safe_load(yaml_file)
    # Generate combinations
    combinations1_number_of_group = generate_combinations(yaml_data1)
    #print (f"combinations1_number_of_group is {combinations1_number_of_group}")

    ###################################################################################

    array_of_groups=[]
    for combination1 in combinations1_number_of_group:
        result_dict1=dict(zip(yaml_data1.keys(), combination1))
        array_of_groups.append(result_dict1)
    return array_of_groups
def group_classification(array_of_groups):
    mergedInfo_path = './merged_info.csv'
    info_path = './info.csv'
    mergedInfo = pd.read_csv(mergedInfo_path)
    for sharedInfo in array_of_groups:
        mergedInfo2 = mergedInfo
        testGroup = ' , '.join(f'{key} = {value}' for key, value in sharedInfo.items())
        #print(testGroup)
        for key, value in sharedInfo.items():
            mergedInfo2 = mergedInfo2[mergedInfo2[key] == int(value) ]
        #print(mergedInfo2)
    #print (len(mergedInfo2))
