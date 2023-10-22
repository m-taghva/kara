import datetime
import os
import subprocess
import argparse
import calendar
import sys
import json
import time
from alive_progress import alive_bar

# Specify address to address.json file
influxdb_conf_file_path = "./../conf/Software/InfluxdbConfig.json"

# Load the JSON data from the file and define adresses as a variable 
with open(influxdb_conf_file_path, 'r') as file:
    json_data = json.load(file)
Primary_influxdb_in_container_address = json_data['Main_influxdb_in_container_address']
Primary_influxdb_address_in_host = json_data['Main_influxdb_address_in_host']
Secondary_influxdb_address_in_host = json_data['Backup_influxdb_address_in_host']
Primary_influxdb_container_name = json_data['Main_influxdb_container_name']
Secondary_influxdb_container_name = json_data['Backup_influxdb_container_name']
Time_add_to_end_of_test = int(json_data['Time_add_to_end_of_test'])
Time_reduce_from_first_of_test = int(json_data['Time_reduce_from_first_of_test'])
Main_influxdb_DB_name = json_data['Main_influxdb_DB_name']

# Process given Test name as an arqument
argParser = argparse.ArgumentParser()
argParser.add_argument("-t", "--testname", help="Test Name (Directory in Result/)")
args = argParser.parse_args()
testDirectory = args.testname
global testDirectory2
testDirectory2 = args.testname
input_file = "./../result/"+testDirectory+"/time"
ring_dir_in_result_path = "./../result/"+testDirectory+"/Ring_cluster"
conf_dir_in_result_path = "./../result/"+testDirectory+"/Config_cluster"

#time defenition
def tehran_time_to_utc(tehran_time_str):
    # Create timezone objects for Tehran and UTC
    tehran_tz = pytz.timezone('Asia/Tehran')
    utc_tz = pytz.utc
    # Parse the input string as a datetime object with the Tehran timezone
    tehran_time = tehran_tz.localize(tehran_time_str)
    # Convert the Tehran time to UTC
    utc_time = tehran_time.astimezone(utc_tz)
    return utc_time

# Add 1-minute delay
#time.sleep(60)

def process_input_file(file_path_input):
    with alive_bar(16,title=f'\033[1mProcessing Test\033[0m:\033[92m{testDirectory}\033[0m') as bar:
        # check if config and ring dir exist
        if os.path.exists(ring_dir_in_result_path):
            bar()
        if os.path.exists(conf_dir_in_result_path):
            bar()
        with open(file_path_input, "r") as f:
            lines = f.readlines()
            for line in lines:
                
                # Split given time
                start_datetime_str, end_datetime_str = line.strip().split(",")
                bar()

                # Convert start and end datetime strings to datetime objects
                start_datetime = datetime.datetime.strptime(start_datetime_str, "%Y-%m-%d %H:%M:%S")
                end_datetime = datetime.datetime.strptime(end_datetime_str, "%Y-%m-%d %H:%M:%S")
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

                # creating backup time format
                backup_start_date , backup_start_time = start_datetime_utc_str.split(" ")
                start_time_backup = backup_start_date+"T"+backup_start_time+"Z"
                backup_end_date , backup_end_time = end_datetime_utc_str.split(" ")
                end_time_backup = backup_end_date+"T"+backup_end_time+"Z"
                bar()

                # dir name creation
                dir_start_date , dir_start_time = start_datetime_str.split(" ")
                dir_start_date = dir_start_date[2:].replace("-","")
                dir_start_time = dir_start_time.replace(":","")
                dir_end_date , dir_end_time = end_datetime_str.split(" ")
                dir_end_date = dir_end_date[2:].replace("-","")
                dir_end_time = dir_end_time.replace(":","")
                backup_dir_name = dir_start_date+"T"+dir_start_time+"_"+dir_end_date+"T"+dir_end_time
                bar()

                # Create backup_path2
                backup_path2 = Primary_influxdb_in_container_address +"/"+ backup_dir_name
                backup_path = f"{Primary_influxdb_in_container_address}/{backup_dir_name}" 
                os.makedirs(backup_path, exist_ok=True)
                bar()

                # Perform backup using influxd backup command
                #print("*-*-**-*-*-*-*-*-*-* Backup logs *-*-**-*-*-*-*-*-*-*") >> f"{backup_path}/backup.log"
                backup_command = f"docker exec -it {Primary_influxdb_container_name} influxd backup -portable -db {Main_influxdb_DB_name} -start {start_time_backup} -end {end_time_backup} {backup_path2}/backup > /dev/null 2>&1"
                backup_process = subprocess.run(backup_command, shell=True)
                exit_code = backup_process.returncode
                if exit_code == 0:
                    #print("\033[92mBackup successful.\033[0m")
                    bar()
                else:
                    print("\033[91mBackup failed.\033[0m")
                    sys.exit(1)
                print()

                # Tar backup files and delete extra files
                tar_command = f"tar -cf {Primary_influxdb_address_in_host}/{backup_dir_name}/backup.tar.gz -C {Primary_influxdb_address_in_host}/{backup_dir_name}/backup . "
                tar_process = subprocess.run(tar_command, shell=True)
                exit_code = tar_process.returncode
                if exit_code == 0:
                    #print("\033[92mTar successful.\033[0m")
                    #print()
                    bar()
                else:
                    print("\033[91mTar failed.\033[0m")
                    sys.exit(1)
                    print()

                # Delete backup directory files
                del_command = f"rm -rf {Primary_influxdb_address_in_host}/{backup_dir_name}/backup/*"
                del_process = subprocess.run(del_command , shell=True)
                bar()

                # Make info directory and move all into influxdb2 mount points
                os.makedirs(f"{Primary_influxdb_address_in_host}/{backup_dir_name}/info", exist_ok=True)
                cp_command = f"cp -r ./../result/{testDirectory}/* {Primary_influxdb_address_in_host}/{backup_dir_name}/info/"
                cp_process = subprocess.run(cp_command, shell=True)
                bar()

                #MV BACKUP.TAR.GZ TO influxdb2 and delete original file
                os.makedirs(Secondary_influxdb_address_in_host, exist_ok=True)
                mv_command = f"mv -f -u {Primary_influxdb_address_in_host}/{backup_dir_name}  {Secondary_influxdb_address_in_host}/" # specified to move to influxdb 
                mv_process = subprocess.run(mv_command, shell=True)
                exit_code = mv_process.returncode
                if exit_code == 0:
                    #print(f"\033[92mFiles moved to {Secondary_influxdb_container_name} location successfully.\033[0m")
                    bar()
                else:
                    print("\033[91mMoving files failed.\033[0m")
                    sys.exit(1)
                    print()

process_input_file(input_file)
#print(f"*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-* END OF BACKUP FOR\033[92m {testDirectory} \033[0m*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
