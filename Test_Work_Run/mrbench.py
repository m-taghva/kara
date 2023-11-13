import sys
import os
import subprocess
import re
import csv
import shutil
import time
from manager import perform_backup_and_report

# For font style
BOLD = "\033[1m"
RESET = "\033[0m"
YELLOW = "\033[1;33m"

if len(sys.argv) != 2:
    print("Usage: python script.py path_to_xml_file,output_path")
    sys.exit(1)

# Extracting input paths from the comma-separated input
paths = sys.argv[1].split(',')
if len(paths) != 2:
    print("Error: Please provide both path to XML file and output path separated by a comma.")
    sys.exit(1)
workload_config_path, output_path = paths

print("")
print(f"{YELLOW}========================================{RESET}")
print("")
print("Processing input file")

cosbenchBin = shutil.which("cosbench")
if not(cosbenchBin):
    print("Command 'cosbench' not found, but can be add with:\n\n\t ln -s {cosbench-dir}/cli.sh /usr/bin/cosbench\n")
    exit()

# TODO: error handling ('hardlink' or 'not found link')
archive_path = os.readlink(cosbenchBin).split("cli.sh")[0]+"archive/"

def submit(workload_file_path):
    # Start workload
    Cos_bench_command = subprocess.run(["cosbench", "submit", workload_file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if Cos_bench_command.returncode == 1:
        print("\033[91mStarting workload failed.\033[0m")
        # TODO: error handling  
        return -1

    # Extract ID of workload
    output_lines = Cos_bench_command.stdout.splitlines()
    match = re.search('(?<=ID:\s)(w\d+)', output_lines[0])
    if match:
        workload_id = match.group()
    else:
        print("\033[91mStarting workload failed.\033[0m")
        # TODO: error handling
        return -1
    
    # Check every second if the workload has ended or not
    # TODO: check state of workload with "cli.sh info" command
    archive_file_path = f"{archive_path}{workload_id}-swift-sample"
    while True:
        if os.path.exists(archive_file_path):
            break
        time.sleep(10)  # changed to 3 seconds

    return workload_id

def create_test_dir(result_path,workload):
    result_file_path = os.path.join(result_path, workload)
    if os.path.exists(result_file_path):
        result_file_tail = '_' + '1' + '_'
        result_file_path += result_file_tail
        while os.path.exists(result_file_path):
            splitted_result_file = result_file_path.split('_')
            repeat_number = int(splitted_result_file[-2]) + 1
            splitted_result_file[-2] = str(repeat_number)
            result_file_path = '_'.join(splitted_result_file)
        
    os.mkdir(result_file_path)
    final_workload_name = result_file_path.split('/')[-1]
    return final_workload_name

def save_time(file):
    #print(file)
    try:
        # Find start of first main and end of last main
        with open(file, 'r') as csv_file:
            reader = csv.reader(csv_file)

            first_main_launching_time = None
            last_main_completed_time = None

            for row in reader:
                if row and row[0].endswith('main'):
                    if first_main_launching_time is None:
                        first_main_launching_time = row[21]
                        last_main_completed_time = row[24]

        if first_main_launching_time and last_main_completed_time:
            start_time = first_main_launching_time.split('@')[1].strip()
            end_time = last_main_completed_time.split('@')[1].strip()
            return start_time,end_time     
           
    except Exception as e:
        print(f"\033[91mAn error occurred: {str(e)}\033[0m")
        return -1
    
def copy_file(archive_file_path,result_file_path,max):
    #archive_file_path = archive_path + workload_id + "-swift-sample" 
    is_copy_successful = 0
    for retry in range(max):
        try:
            shutil.copy2(archive_file_path, result_file_path)
            return 1  # Exit the loop if copying is successful

        except Exception as e:
            print(f"\033[91mAn error occurred: {e}\033[0m")

            # Sleep for a short duration before retrying
        time.sleep(1)
    print(f"\033[91mMaximum retries reached ({max}). File {archive_file_path} copy failed.\033[0m")
    return 0
    
#submit workload
# TODO: check active workloads  
print("Sending workload")
print("Please wait until the test is finished ... (you can check Cosbench web console)")
workload_id = submit(workload_config_path) 
# TODO: if workload_id exists 
archive_workload_dir_name = f"{workload_id}-swift-sample"   #for example: w123-swift-sample 
#create directory for  workload results
workload_dir_name = workload_config_path.split('/')[-1].replace('.xml','')
workload_dir_name = create_test_dir(output_path,workload_dir_name)
print(f"\033[1mWorkload Info:\033[0m ID: {workload_id} Name: {workload_dir_name}")
result_path = f"{output_path}/{workload_dir_name}"

# save time
# TODO: save time using "cli.sh info" command
print("Saving test time ranges ...")
file_path_for_saveTime = f"{archive_path}{archive_workload_dir_name}/{archive_workload_dir_name}.csv"
start_time,end_time = save_time(file_path_for_saveTime)
time_file_path = f"{result_path}/time"
time_file = open(time_file_path, "w")
start_end_time = f"{start_time},{end_time}"
time_file.write(start_end_time)
time_file.close()

# copy files
time.sleep(5)
print("Copying Cosbench source files ...")
copy_file(archive_path + archive_workload_dir_name + '/workload.log', result_path + '/workload.log', 3)
copy_file(archive_path + archive_workload_dir_name + '/workload-config.xml', result_path + '/workload-config.xml', 3)
copy_file(archive_path + archive_workload_dir_name + '/' + archive_workload_dir_name + '.csv', result_path + '/' + archive_workload_dir_name + '.csv', 3)

#perform_backup_and_report(start_time, end_time, time_file_path, result_path)
