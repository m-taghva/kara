import os
import sys
import subprocess
import shutil

# Defining paths
metric_sum_file = "./../conf/Status-reporter/sum_metric_list.txt"
metric_mean_file = "./../conf/Status-reporter/mean_metric_list.txt"
metric_max_file = "./../conf/Status-reporter/max_metric_list.txt"
metric_min_file = "./../conf/Status-reporter/min_metric_list.txt"

def perform_backup_and_report(start_time, end_time, time_file_path, result_file_path):
 
    # Construct the status-reporter command with the variables
    status = f"python3 ./../status/status_reporter.py {metric_sum_file},{time_file_path},{result_file_path}"
    subprocess.call(status, shell=True) 
    
    # Construct the backup command with the variables
    backup = f"python3 ./../Backup/backup_script.py -t '{start_time},{end_time}'"
    subprocess.call(backup, shell=True)
