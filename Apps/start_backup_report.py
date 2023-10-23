import os
import sys
import subprocess
import shutil

# Defining paths
result_path = './../result/'
backup_script_path = './../Backup/backup_script.py'
hosts_file_path = "./../conf/Deployments/Host-names/hosts.txt"
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
  
    # Start backup phase and its process & get-ring and get-conf to result dir
    Ring_address = os.path.join(result_path, final_workload_name, 'Ring_cluster')
    os.makedirs(Ring_address, exist_ok=True)

    conf_address = os.path.join(result_path, final_workload_name, 'Config_cluster')
    os.makedirs(conf_address, exist_ok=True)

    get_conf_command = f"python3 ./../Codes/get_conf.py -f {hosts_file_path}"
    get_conf_process = subprocess.run(get_conf_command, shell=True)

    get_ring_command = f"python3 ./../Codes/get_ring.py -f {hosts_file_path}"
    get_ring_process = subprocess.run(get_ring_command, shell=True)

    # Move all *.conf from . to result
    ring_mv_command = f"mv *.conf {conf_address}"
    ring_mv_process = subprocess.run(ring_mv_command, shell=True)

    conf_mv_command = f"mv *.txt {Ring_address}"
    conf_mv_process = subprocess.run(conf_mv_command, shell=True)
