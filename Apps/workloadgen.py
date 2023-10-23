import sys
import subprocess
import generate_xml
import os
import time
import shutil
import csv
from start_backup_report import perform_backup_and_report

# Getting arguments from send-load.py
# Arguments are: input file, default file and script file
script_file_path = sys.argv[1]
sleep_time_between_workloads = 0 #time in Seconds

# Defining paths
cosbench_command = './../../cli.sh'
archive_path = './../../archive/'
result_path = './../result/'
pre_test_script_path = script_file_path
workloads_dir_path = "./workloads"
config_gen_path = "config_gen.py"
input_txt_path = "./input.txt"
submit = 'submit'
max_pre_test_script_failure = 3

# New code starts here
def process_on_workloads(workloads_dir_path):

    # make dir for workloads and check if it is empty or not
    try :
        if workloads_dir_path:
            delete_command = f"rm -rf {workloads_dir_path}/*"
            delete_process = subprocess.run(delete_command, shell=True)
            delete_exit_code = delete_process.returncode
            if delete_exit_code == 1:
                print("\033[91mFailure in deleting directory!\033[0m")
        else:
            os.mkdir(workloads_dir_path)
    except:
        print("\033[91mFailure in processing with directory!\033[0m")

    # Trrigger generator xml
    trrigger_command = f"python3 {config_gen_path} {input_txt_path}"
    trrigger_process = subprocess.run(trrigger_command, shell=True)
    trrigger_exit_code = trrigger_process.returncode
    if trrigger_exit_code == 1:
        print("\033[91mFailure in triggering generator xml!\033[0m")
        exit()

    all_workloads = os.listdir(workloads_dir_path)
    all_workloads = sorted(all_workloads)
    for workload in all_workloads:
        # Execute the script before running the test
        print("\033[1m\nExecuting pre-test script...\033[0m")
        time.sleep(1)
        pre_test_script_failure_num = 0

        for talash in range(max_pre_test_script_failure):
            pre_test_script = subprocess.run([pre_test_script_path], shell=True)

            if pre_test_script.returncode == 0:
                print("\033[92mPre-test script executed successfully!\033[0m")
                break
            else:
                print("\033[91mPre-test script executed with failure! Retrying {} more time(s)\033[0m".format(max_pre_test_script_failure - talash - 1))
                pre_test_script_failure_num += 1
                time.sleep(1)

        if pre_test_script_failure_num == max_pre_test_script_failure:
            print("\033[91mMaximum pre-test script failures reached. Skipping this workload.\033[0m")
            continue

        # Sleep time for a short duration
        if sleep_time_between_workloads > 0:
            print("Wait for: ",sleep_time_between_workloads,"s")
            time.sleep(sleep_time_between_workloads)

        # Start workload
        workload_file_path = os.path.join(workloads_dir_path, workload)
        Cos_bench_command = subprocess.run(["bash", cosbench_command, submit, workload_file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if Cos_bench_command.returncode == 1:
            print("\033[91mStarting workload failed. Skipping this workload.\033[0m")
            continue

        # Extract ID of workload
        output_lines = Cos_bench_command.stdout.splitlines()
        workload_id = ""
        for line in output_lines:
            if "ID" in line:
                parts = line.split()
                if len(parts) > 1:
                    workload_id = parts[-1]
                    break
        
        # Generate archive file name of workload
        archive_file_name = workload_id + "-swift-sample"
        print(f"\033[1mWorkload Info:\033[0m ID: {workload_id} Name: {workload}")
        if workload_id == "":
            print("\033[91mWorkload ID is empty. Skipping this workload.\033[0m")
            continue
        
        # Check every second if the workload has ended or not
        while True:
            archive_file_path = os.path.join(archive_path, archive_file_name)
            if os.path.exists(archive_file_path):
                break
            time.sleep(3)  # changed to 3 seconds
        
        # Create result directory for workloads
        workload_for_dir_name = workload.replace('.xml', '')
        result_file_path = os.path.join(result_path, workload_for_dir_name)
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
        
        # Create and copy workload.log & Add try for copying file up to 2 times
        archive_log_file = os.path.join(archive_file_path, 'workload.log')
        result_log_file = os.path.join(result_file_path, 'workload.log')
        max_retries = 2  # Number of retry attempts

        for retry in range(max_retries + 1):
            try:
                shutil.copy2(archive_log_file, result_log_file)
                break  # Exit the loop if copying is successful

            except Exception as e:
                print(f"\033[91mAn error occurred: {e}\033[0m")

            if retry < max_retries:
                # Sleep for a short duration before retrying
                time.sleep(1)
            else:
                print(f"\033[91mMaximum retries reached ({max_retries}). File {archive_log_file} copy failed.\033[0m")
            
        # Create and copy workload-config.xml
        archive_config_file = os.path.join(archive_file_path, 'workload-config.xml')
        result_config_file = os.path.join(result_file_path, 'workload-config.xml')
        max_retries = 2

        for retry in range(max_retries + 1):
            try:
                shutil.copy2(archive_config_file, result_config_file)
                break
            except Exception as e:
                print(f"\033[91mAn error occurred: {e}\033[0m")

            if retry < max_retries:
                time.sleep(3)
            else:
                print(f"\033[91mMaximum retries reached ({max_retries}). File {archive_config_file} copy failed.\033[0m")
        # Create archive csv file
        archive_csv_path = os.path.join(archive_file_path, archive_file_name)
        archive_csv_path += ".csv"

        # Create result csv file
        result_csv_path = os.path.join(result_file_path, workload)
        result_csv_path += ".csv"

        # Copy csv file from archive to result directory
        max_retries = 2

        for retry in range(max_retries + 1):
            try:
                shutil.copy2(archive_csv_path, result_csv_path)
                break
            except Exception as e:
                print(f"\033[91mAn error occurred: {e}\033[0m")

            if retry < max_retries:
                time.sleep(3)
            else:
                print(f"\033[91mMaximum retries reached ({max_retries}). File {archive_csv_path} copy failed.\033[0m")

        # Remove config.xml file
        def remove_file_with_retry(file_path, max_retries=2):
            for retry in range(max_retries + 1):
                if os.path.exists(file_path):
                    try:
                        result = subprocess.run(['rm', '-rf', file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
                    except Exception as e:
                        print(f"\033[91mAn error occurred when removing '{file_path}': {e}\033[0m")

                    if retry < max_retries:
                        # Sleep for a short duration before retrying
                        time.sleep(1)
                    else:
                        print(f"\033[91mMaximum retries reached ({max_retries}). File removal failed for '{file_path}'\033[0m")
                else:
                    print("\033[91mFile Not Found.\033[0m")
                    break
        try:
            # Find start of first main and end of last main
            with open(result_csv_path, 'r') as csv_file:
                reader = csv.reader(csv_file)

                first_main_launching_time = None
                last_main_completed_time = None

                for row in reader:
                    if row and row[0].endswith('main'):
                        if first_main_launching_time is None:
                            first_main_launching_time = row[21]
                            last_main_completed_time = row[24]

            if first_main_launching_time and last_main_completed_time:
                
                # Write time of workload in time file
                time_file_path = f"{result_file_path}/time"
                time_file = open(time_file_path, "w")
                start_time = first_main_launching_time.split('@')[1].strip()
                end_time = last_main_completed_time.split('@')[1].strip()
                start_end_time = f"{start_time},{end_time}"
                time_file.write(start_end_time)
                time_file.close()

                perform_backup_and_report(start_time, end_time, time_file_path, result_file_path)

        except Exception as e:
            print(f"\033[91mAn error occurred for workload {workload}: {str(e)}\033[0m")
            continue

process_on_workloads(workloads_dir_path)
