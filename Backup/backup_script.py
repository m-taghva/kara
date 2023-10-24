import datetime
import os
import subprocess
import argparse
import calendar
import sys
import json
import time
import pytz
from alive_progress import alive_bar

# Specify address to InfluxDBConfig.json file
influxdb_conf_file_path = "./../conf/Backup/BackupConfig.json"

# Load the JSON data from the file and define addresses as variables
with open(influxdb_conf_file_path, 'r') as file:
    json_data = json.load(file)
Port = int(json_data['Ssh_port_influx_host'])
User = json_data['User_influxdb_host']
Influxdb_container_port = int(json_data['Influxdb_container_port'])
Influxdb_host_ip = json_data['Influxdb_host_ip']
Second_host_ip = json_data['Second_host_ip']
Backup_dir_in_container = json_data['Backup_dir_in_container']
Backup_dir_in_host = json_data['Backup_dir_in_host']
Backup_dir_in_second_host = json_data['Backup_dir_in_second_host']
Influxdb_container_name = json_data['Influxdb_container_name']
Time_add_to_end_of_test = int(json_data['Time_add_to_end_of_test'])
Time_reduce_from_first_of_test = int(json_data['Time_reduce_from_first_of_test'])
Influxdb_DB_name = json_data['Influxdb_DB_name']

# Command-line argument parsing
argParser = argparse.ArgumentParser()
argParser.add_argument("-t","--time", help="Start and end times for backup (format: 'start_time,end_time')")
args = argParser.parse_args()
time_range = args.time

# Split the time_range into start_time and end_time
start_time_str, end_time_str = time_range.split(',')

# Function to convert Tehran time to UTC
def tehran_time_to_utc(tehran_time_str):
    tehran_tz = pytz.timezone('Asia/Tehran')
    utc_tz = pytz.utc
    tehran_time = tehran_tz.localize(tehran_time_str)
    utc_time = tehran_time.astimezone(utc_tz)
    return utc_time

# Function to process the input file
def process_input_file(start_time_str, end_time_str):
    with alive_bar(12, title=f'\033[1mProcessing Test\033[0m:\033[92m{start_time_str}-{end_time_str}\033[0m') as bar:
        # Convert start and end datetime strings to datetime objects
        start_datetime = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
        end_datetime = datetime.datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
        bar()

        # Convert Tehran time to UTC
        start_datetime_utc = tehran_time_to_utc(start_datetime)
        end_datetime_utc = tehran_time_to_utc(end_datetime)
        bar()

        dir_start_datetime_utc = tehran_time_to_utc(start_datetime)
        dir_end_datetime_utc = tehran_time_to_utc(end_datetime)
        bar()

        # Add the specified number of seconds to both datetime objects
        start_datetime_utc -= datetime.timedelta(seconds=Time_reduce_from_first_of_test)
        end_datetime_utc += datetime.timedelta(seconds=Time_add_to_end_of_test)
        bar()

        # Convert the UTC datetime objects back to strings
        start_datetime_utc_str = start_datetime_utc.strftime("%Y-%m-%d %H:%M:%S")
        end_datetime_utc_str = end_datetime_utc.strftime("%Y-%m-%d %H:%M:%S")
        bar()

        # Creating backup time format
        backup_start_date, backup_start_time = start_datetime_utc_str.split(" ")
        start_time_backup = backup_start_date + "T" + backup_start_time + "Z"
        backup_end_date, backup_end_time = end_datetime_utc_str.split(" ")
        end_time_backup = backup_end_date + "T" + backup_end_time + "Z"
        bar()

        # Directory name creation
        dir_start_date, dir_start_time = start_datetime_utc_str.split(" ")
        dir_start_date = dir_start_date[2:].replace("-", "")
        dir_start_time = dir_start_time.replace(":", "")
        dir_end_date, dir_end_time = end_datetime_utc_str.split(" ")
        dir_end_date = dir_end_date[2:].replace("-", "")
        dir_end_time = dir_end_time.replace(":", "")
        backup_dir_name = dir_start_date + "T" + dir_start_time + "_" + dir_end_date + "T" + dir_end_time
        bar()

        # Create backup_path
        backup_path = f"{Backup_dir_in_container}/{backup_dir_name}"
        os.makedirs(backup_path, exist_ok=True)
        bar()

        # Perform backup using influxd backup command
        backup_command = f"ssh -p {Port} {User}@{Influxdb_host_ip} 'docker exec -i -u root {Influxdb_container_name} influxd backup -portable -db {Influxdb_DB_name} -start {start_time_backup} -end {end_time_backup} {backup_path}/backup > /dev/null 2>&1'"
        backup_process = subprocess.run(backup_command, shell=True)
        exit_code = backup_process.returncode
        if exit_code == 0:
            bar()
        else:
            print("\033[91mBackup failed.\033[0m")
            sys.exit(1)

        # Tar backup files and delete extra files
        tar_command = f"ssh -p {Port} {User}@{Influxdb_host_ip} 'sudo tar -cf {Backup_dir_in_host}/{backup_dir_name}/backup.tar.gz -C {Backup_dir_in_host}/{backup_dir_name}/backup .' "
        tar_process = subprocess.run(tar_command, shell=True)
        exit_code = tar_process.returncode
        if exit_code == 0:
            bar()
        else:
            print("\033[91mTar failed.\033[0m")
            sys.exit(1)

        # Delete backup directory files
        del_command = f"ssh -p {Port} {User}@{Influxdb_host_ip} 'sudo rm -rf {Backup_dir_in_host}/{backup_dir_name}/backup'"
        del_process = subprocess.run(del_command, shell=True)
        bar()

        # Move backup.tar.gz to secondary host and delete original file
        os.makedirs(Backup_dir_in_second_host, exist_ok=True)
        mv_command = f"scp -3 -r scp://{User}@{Influxdb_host_ip}:{Port}/{Backup_dir_in_host}/{backup_dir_name}  scp://{User}@{Second_host_ip}:{Port}/{Backup_dir_in_second_host}"
        mv_process = subprocess.run(mv_command, shell=True)
        exit_code = mv_process.returncode
        if exit_code == 0:
            bar()
        else:
            print("\033[91mMoving files failed.\033[0m")
            sys.exit(1)

process_input_file(start_time_str, end_time_str)
