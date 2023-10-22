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

def perform_backup_and_report(final_workload_name, time_file_path, result_file_path):
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

    subprocess.call(['python3', backup_script_path, '-t', final_workload_name])

    # Construct the status-reporter command with the variables
    other_script_command = f"python3 status_reporter.py {metric_sum_file},{time_file_path},{result_file_path}"
    subprocess.call(other_script_command, shell=True)
    merge_csv = ["python3", "csv_merger.py", "./../result,all_hosts_output.csv"]
    subprocess.run(merge_csv, check=True)    
