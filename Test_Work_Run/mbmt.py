#!/usr/bin/env python3

import sys
import getopt
import os
import subprocess
import shutil

# Defining paths
metric_sum_file = "./../conf/Status-reporter/sum_metric_list.txt"
metric_mean_file = "./../conf/Status-reporter/mean_metric_list.txt"
metric_max_file = "./../conf/Status-reporter/max_metric_list.txt"
metric_min_file = "./../conf/Status-reporter/min_metric_list.txt"

def usage():
    print("""
    send_load.py [OPTIONS]
Options:
  -s, --script-file <file>    : Path to the script file. (Default: ./pre_test_script.sh)

Description:
  This script sends load to a cluster based on the provided benchmark and default files.
  Script-file is executed before every test.
  
Example usage:
  send_load.py -s /path/to/script.sh    (uses default benchmark and default files)
""")

def main(argv):
    # Default input and default files
    script_file = "./pre_test_script.sh"

    # Parse command line arguments
    try:
        opts, args = getopt.getopt(argv, "hs:", ["script-file="])
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt in ("-s", "--script-file"):
            script_file = arg
 
    # Call the main program 
    work = f"python3 ./workloadgen.py  {script_file}"
    work_process = subprocess.run(work,shell=True)

    # Check if the subprocess has finished
    if work_process.returncode == 0:
        # Run another Python script after workloadgen.py has finished
        merge = ["python3", "./../Status/csv_merger.py", "./../result,all_hosts_output.csv"]
        subprocess.run(merge, check=True)

def perform_backup_and_report(start_time, end_time, time_file_path, result_file_path):
 
     # Construct the status-reporter command with the variables
     status = f"python3 ./../Status/status_reporter.py {metric_sum_file},{time_file_path},{result_file_path}"
     subprocess.call(status, shell=True) 
    
     # Construct the backup command with the variables
     backup = f"python3 ./../Backup/backup_script.py -t '{start_time},{end_time}'"
     subprocess.call(backup, shell=True)

if __name__ == "__main__":
    main(sys.argv[1:])
