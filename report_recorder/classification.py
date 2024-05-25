import yaml
import itertools
import os
import csv
import pandas as pd

################# CSV to sorted yaml descending-based ###########################################################################
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

    # Write the unique values to a YAML file without quotes
    unique_file = 'unique_values.yaml'
    with open(unique_file, 'w') as f:
        yaml.dump(unique_values, f, default_flow_style=False, sort_keys=False)

    print(f"Unique values written to {unique_file}")

    with open('unique_values.yaml', 'r') as f:
        yaml_data = yaml.safe_load(f)

    # Convert the dictionary into a list of tuples (key, value) where the value is the length of the associated list
    sorted_data = dict(sorted(yaml_data.items(), key=lambda x: len(x[1]), reverse=True))
    # print (sorted_data)
    # Write the sorted dictionary back to a YAML file

    sorted_file = "sorted_output.yaml"
    with open(sorted_file, 'w') as f:
        yaml.dump(sorted_data,f,sort_keys=False)

    print(f"YAML file sorted based on number of values in descending order in {sorted_file}")
    return sorted_file

#######################################################################################################

def generate_combinations(yaml_data):
    # Get the values from each key in the YAML data
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
'''
# Specify the file path
file_path = "final.txt"

# Check if the file exists before attempting to delete it
if os.path.exists(file_path):
    # Delete the file
    os.remove(file_path)
    print(f"File '{file_path}' deleted successfully.")
else:
    print(f"File '{file_path}' does not exist.")
    



# Read the YAML file
with open('sorted_output.yaml', 'r') as yaml_file:
    yaml_data = yaml.safe_load(yaml_file)

# Initialize the multiplication result

# Iterate over the keys in reverse order
result=1
for key in yaml_data.keys():
    # Extract the values associated with the current key
    values = yaml_data[key]
    result *= len(values)
 

# Print the final result
print("Total Number of Tests is: ", result)
'''
def group_generator (yaml_data,threshold):

    keys_list = list(yaml_data.keys())
    result=1
    j=0

    for i in range(len(keys_list)):
        #print ("i is: ", i)
        key = keys_list[i]
        result*=len(yaml_data[keys_list[i]])

    #print (yaml_data[keys_list[2]])
        if result > threshold:
            if j!=0:
                j = i
                break
            else:
                j=1
        

    print ("j is the index of group breaker: ", j)

    keys_list1 = list(yaml_data.keys())

    # Define the range from 0 to i (inclusive)
    start_index = j 
    end_index = len(yaml_data.keys())

    # Get the sublist of keys
    sublist = keys_list1[start_index:end_index]
    #print (sublist)
    #print (keys_list1[end_index])


    new_yaml_data = {key: yaml_data[key] for key in sublist}
    #print (new_yaml_data)
    # Dump the new dictionary to a YAML file
    with open('from_threshold_to_end.yaml', 'w') as f:
        yaml.dump(new_yaml_data, f, default_flow_style=False,sort_keys=False)


    with open('from_threshold_to_end.yaml', 'r') as yaml_file:
        yaml_data1 = yaml.safe_load(yaml_file)

    # Generate combinations
    combinations1_number_of_group = generate_combinations(yaml_data1)

    #########################################################################################################
    '''
    keys_list2 = list(yaml_data.keys())

    # Define the range from 0 to i (inclusive)
    start_index = 0
    end_index = j

    # Get the sublist of keys
    sublist = keys_list2[start_index:end_index]

    new_yaml_data = {key: yaml_data[key] for key in sublist}

    # Dump the new dictionary to a YAML file
    with open('from_start_to_threshold.yaml', 'w') as f:
        yaml.dump(new_yaml_data, f, default_flow_style=False,sort_keys=False)


    with open('from_start_to_threshold.yaml', 'r') as yaml_file:
        yaml_data2 = yaml.safe_load(yaml_file)

    # Generate combinations
    combinations2_number_of_tests_within_each_group = generate_combinations(yaml_data2)


    n=len(combinations1_number_of_group)
    lists = [[] for _ in range(n)]

'''
    ###################################################################################
    number_of_groups = 0
    array_of_groups=[]
    for combination1 in combinations1_number_of_group:
        result_dict1=dict(zip(yaml_data1.keys(), combination1))
        array_of_groups.append(result_dict1)
        number_of_groups+=1 
    
    return number_of_groups,array_of_groups

 
'''
    #with open("final.txt", "a") as file:
        #print (result_dict1)
        #
        #file.write("\n\n")  
        #file.write('New group of tests')
        #file.write("\n\n")
    for combination2 in combinations2_number_of_tests_within_each_group:
        result_dict2=dict(zip(yaml_data2.keys(), combination2))
        with open("final.txt", "a") as file:   
            result_dict={}
            result_dict.update(result_dict2)
            result_dict.update(result_dict1)
            lists[i].append(result_dict)
            #print (result_dict)
            file.write(str(result_dict))
            file.write("\n")  
   
    print (array_of_groups)
    with open("final_final.txt", "w") as file:
        for i, lst in enumerate(lists):
    # Write the index and the list to the file
            file.write(f"{lst}\n")

'''



def group_classification(array_of_groups):
    mergedInfo_path = './merged_info.csv'
    info_path = './info.csv'
    mergedInfo = pd.read_csv(mergedInfo_path)
    #sharedInfoList = [{"swift_config.object_worker":"7","workload_config.concurrency":"8","swift_config.proxy_worker":"15"},{"swift_config.object_worker":"7","workload_config.concurrency":"16","workload_config.objSize":"128"}]

    for sharedInfo in array_of_groups:
        mergedInfo2 = mergedInfo
        testGroup = ' , '.join(f'{key} = {value}' for key, value in sharedInfo.items())
        print(testGroup)
        for key, value in sharedInfo.items():
            mergedInfo2 = mergedInfo2[mergedInfo2[key] == int(value) ]
        print(mergedInfo2)
    print (len(mergedInfo2))