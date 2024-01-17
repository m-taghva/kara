import os
import subprocess
import re
import csv
import shutil
import time
import argparse

# For font style
BOLD = "\033[1m"
RESET = "\033[0m"
YELLOW = "\033[1;33m"

print("")
print(f"{YELLOW}========================================{RESET}")
print("")

def submit(workload_file_path, output_path):
    cosbenchBin = shutil.which("cosbench")
    if not(cosbenchBin):
        print("Command 'cosbench' not found, but can be add with:\n\n\t ln -s {cosbench-dir}/cli.sh /usr/bin/cosbench\n")
        return None, None, -1
    archive_path = os.readlink(cosbenchBin).split("cli.sh")[0]+"archive/"
    print("Sending workload ...")
    # Start workload
    Cos_bench_command = subprocess.run(["cosbench", "submit", workload_file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if Cos_bench_command.returncode == 1:
        print("\033[91mStarting workload failed.\033[0m")
        return None, None, -1
    # Extract ID of workload
    output_lines = Cos_bench_command.stdout.splitlines()
    workload_id_regex = re.search('(?<=ID:\s)(w\d+)', output_lines[0])
    workload_name = workload_file_path.split('/')[-1].replace('.xml','')
    if workload_id_regex:
        workload_id = workload_id_regex.group()
        print(f"\033[1mWorkload Info:\033[0m ID: {workload_id} Name: {workload_name}")
    else:
        print("\033[91mStarting workload failed.\033[0m")
        return None, None, -1
    # Check every second if the workload has ended or not
    archive_file_path = f"{archive_path}{workload_id}-swift-sample"
    while True:
        if os.path.exists(archive_file_path):
            time.sleep(5) 
            break
        time.sleep(5)
    result_path = create_test_dir(output_path, workload_name)
    archive_workload_dir_name = f"{workload_id}-swift-sample"
    print(f"Result Path: {result_path}")
    # run other functions 
    start_time, end_time = save_time(f"{archive_path}{archive_workload_dir_name}/{archive_workload_dir_name}.csv", result_path)
    copy_bench_files(archive_path, archive_workload_dir_name, result_path)
    return  start_time, end_time, result_path

def create_test_dir(result_path, workload_name):
    result_file_path = os.path.join(result_path, workload_name)
    if os.path.exists(result_file_path):
        i = 1
        while os.path.exists(result_file_path + f"_{i}"):
            i += 1
        result_file_path += f"_{i}"
    os.mkdir(result_file_path)
    return result_file_path

def save_time(file, result_path):
    start_time = None
    end_time = None
    # save time
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
            time_file = open(f"{result_path}/time", "w")
            start_end_time = f"{start_time},{end_time}"
            time_file.write(start_end_time)
            time_file.close()
            #return start_time,end_time
            print(f"Start Time: {start_time}")
            print(f"End Time: {end_time}")     
        return start_time, end_time        
    except Exception as e:
        print(f"\033[91mAn error occurred: {str(e)}\033[0m")
        return -1

def copy_bench_files(archive_path, archive_workload_dir_name, result_path):
    # copy files
    time.sleep(5)
    copylistfiles = ["/workload.log","/workload-config.xml",'/'+ archive_workload_dir_name + '.csv']
    print("Copying Cosbench source files ...")
    for fileName in copylistfiles:
        archive_file_path = archive_path + archive_workload_dir_name +fileName
        retry=3
        while retry>0:
            try:
                shutil.copy2(archive_file_path, result_path +fileName)
                break # Exit the loop if copying is successful
            except Exception as e:
                print(f"\033[91mAn error occurred: {e}\033[0m")
                # Sleep for a short duration before retrying
            time.sleep(1)
            retry-=1
        if retry == 0 :
            print(f"\033[91mMaximum retries reached ({retry}). File {archive_file_path} copy failed.\033[0m")
  
def main(workload_config_path, output_path):
    if not os.path.exists(output_path):
       os.makedirs(output_path)
    start_time, end_time, result_file_path = submit(workload_config_path, output_path)
    return start_time, end_time, result_file_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Monster Benchmark')
    parser.add_argument('-i', '--input', help='Input file path', required=True)
    parser.add_argument('-o', '--output', help='Output directory', required=True)
    args = parser.parse_args()
    workload_config_path = args.input
    output_path = args.output
    main(workload_config_path, output_path)
