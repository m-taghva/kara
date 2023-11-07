import datetime
import os
import subprocess
import argparse
import sys
import pytz
import yaml
from alive_progress import alive_bar

# Specify address to BackupConfig.json file
config_file = "./../conf/Backup/monstaver.yml"

def load_config(config_file):
    with open(config_file, "r") as stream:
        try:
            data_loaded = yaml.safe_load(stream)
            return data_loaded  # Add this line to return the loaded data
        except yaml.YAMLError as exc:
            print(f"Error loading the configuration: {exc}")
            sys.exit(1)

# Command-line argument parsing
argParser = argparse.ArgumentParser()
argParser.add_argument("-t", "--time", help="Start and end times for backup (format: 'start_time,end_time')")
args = argParser.parse_args()

# Load the configuration from the YAML file
data_loaded = load_config(config_file)

# Check if the user provided the -t option
if args.time:
    time_range = args.time
else:
    # Use the default time from the config file
    time_range = data_loaded['default_section']['time']
  
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

# Access the configuration values from the 'influxdb' section
    default_config = data_loaded['default_section']
    time_add, time_reduce = map(int, default_config['time_margin'].split(','))
    Backup_dir_in_your_server = default_config.get("backup_output")   

    with alive_bar(21, title=f'\033[1mProcessing Test\033[0m:\033[92m{start_time_str}-{end_time_str}\033[0m') as bar:
        # Convert start and end datetime strings to datetime objects
        start_datetime = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
        end_datetime = datetime.datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
        bar()

        # Convert Tehran time to UTC
        start_datetime_utc = tehran_time_to_utc(start_datetime)
        end_datetime_utc = tehran_time_to_utc(end_datetime)
        bar()


        # Add the specified number of seconds to both datetime objects
        start_datetime_utc -= datetime.timedelta(seconds=time_add)
        end_datetime_utc += datetime.timedelta(seconds=time_reduce)
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
        dir_start_date, dir_start_time = start_time_str.split(" ")
        dir_start_date = dir_start_date[2:].replace("-", "")
        dir_start_time = dir_start_time.replace(":", "")
        dir_end_date, dir_end_time = end_time_str.split(" ")
        dir_end_date = dir_end_date[2:].replace("-", "")
        dir_end_time = dir_end_time.replace(":", "")
        backup_dir_name = dir_start_date + "T" + dir_start_time + "_" + dir_end_date + "T" + dir_end_time
        bar()

    for key,value in data_loaded['influxdb_section'].items(): 
        Influxdb_container_name = key
        Port = value['ssh_port']
        User = value['user_influxdb_server']
        Influxdb_host_ip = value['influxdb_server_ip']
        Backup_dir_in_container = value['backup_dir_container']
        Backup_dir_in_host = value['backup_dir_host']
        New_location_backup_in_host = value['temporary_location_backup_host']
        for Influxdb_DB_name in value['influxdb_DB_name']:        
            # Perform backup using influxd backup command
            backup_command = f"ssh -p {Port} {User}@{Influxdb_host_ip} 'sudo docker exec -i -u root {Influxdb_container_name} influxd backup -portable -db {Influxdb_DB_name} -start {start_time_backup} -end {end_time_backup} {Backup_dir_in_container}/{backup_dir_name}/backup/{Influxdb_DB_name} > /dev/null 2>&1'"
            backup_process = subprocess.run(backup_command, shell=True)
            exit_code = backup_process.returncode
            if exit_code == 0:
               bar()
            else:
               print("\033[91mBackup failed.\033[0m")
               sys.exit(1)

        # Tar backup files and delete extra files
        tar_command = f"ssh -p {Port} {User}@{Influxdb_host_ip} 'sudo tar -cf {Backup_dir_in_host}/{backup_dir_name}/backup.tar.gz -C {Backup_dir_in_host}/{backup_dir_name}/backup/ . '"
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
        if exit_code == 0:
            bar()
        else:
            print("\033[91mDelete backup dir failed.\033[0m")
            sys.exit(1)
         
        # Check if the directory exists on the host server
        check_command = f"ssh -p {Port} {User}@{Influxdb_host_ip} 'if [ -d {New_location_backup_in_host} ]; then echo \"Directory exists\"; else echo \"Directory does not exist\"; fi'"
        check_process = subprocess.run(check_command, shell=True, capture_output=True, text=True)
        if "Directory exists" in check_process.stdout:
            print()
        else:
             # Create temporary backup directory on the host server with elevated privileges
             mkdir_command = f"ssh -p {Port} {User}@{Influxdb_host_ip} 'sudo mkdir {New_location_backup_in_host} && sudo mv {Backup_dir_in_host}/{backup_dir_name}/  {New_location_backup_in_host} && sudo chmod -R 777 {New_location_backup_in_host}'"
             mkdir_process = subprocess.run(mkdir_command, shell=True)
             exit_code = mkdir_process.returncode
        if exit_code == 0:
            bar()
        else:
            print("\033[91mDirectory creation and permission setting failed.\033[0m")
            sys.exit(1)        

        # Move backup.tar.gz to secondary host and delete original file
        os.makedirs(Backup_dir_in_your_server, exist_ok=True)
        subprocess.run(f"sudo mkdir -p {Backup_dir_in_your_server} && sudo chmod -R 777 {Backup_dir_in_your_server}", shell=True)
        mv_command = f"scp -r -P {Port} {User}@{Influxdb_host_ip}:{New_location_backup_in_host}/*  {Backup_dir_in_your_server}/ > /dev/null 2>&1"
        mv_process = subprocess.run(mv_command, shell=True)
        exit_code = mv_process.returncode
        if exit_code == 0:
            bar()
        else:
            print("\033[91mMoving files failed.\033[0m")
            sys.exit(1)

        # remove temporary location of backup in host
        del_command_tmp_loc = f"ssh -p {Port} {User}@{Influxdb_host_ip} 'sudo rm -rf {New_location_backup_in_host}'"
        del_process = subprocess.run(del_command_tmp_loc, shell=True)
        if exit_code == 0:
            bar()
        else:
            print("\033[91mRemove temp dir failed.\033[0m")
            sys.exit(1)
 
        # copy selected directory to output directory 
        input_paths = data_loaded['default_section']['input_paths']
        for path in input_paths:
            other_dir = f"sudo cp -rp {path}/ {Backup_dir_in_your_server}"
            other_dir_process = subprocess.run(other_dir, shell=True)
            if exit_code == 0:
                bar()
            else:
                print("\033[91mCopy paths failed.\033[0m")
                sys.exit(1)   

        # copy ring and config to output
        for key,value in data_loaded['swift'].items():
          container_name = key
          user = value['user']
          ip = value['ip']
          port = value['port']
          print(user + "," + ip + "," + str(port))
   
          get_conf_command =  f"ssh -p {str(port)} {user}@{ip} docker exec {container_name} cat /etc/swift/object-server.conf > Backup_dir_in_your_server/{container_name}-object-server.conf"
          get_conf_process = subprocess.run(get_conf_command, shell=True)
          bar()
          if get_conf_process.returncode == 1:
             print("\033[91mFailure in getting object-server.conf\033[0m")
             
          get_conf_command =  f"ssh -p {str(port)} {user}@{ip} docker exec {container_name} cat /etc/swift/container-server.conf > Backup_dir_in_your_server/{container_name}-container-server.conf"
          get_conf_process = subprocess.run(get_conf_command, shell=True)
          bar()
          if get_conf_process.returncode == 1:
             print("\033[91mFailure in getting container-server.conf\033[0m")
          
          get_conf_command =  f"ssh -p {str(port)} {user}@{ip} docker exec {container_name} cat /etc/swift/account-server.conf > Backup_dir_in_your_server/{container_name}-account-server.conf"
          get_conf_process = subprocess.run(get_conf_command, shell=True)
          bar()
          if get_conf_process.returncode == 1:
             print("\033[91mFailure in getting account-server.conf\033[0m")
             
          get_conf_command =  f"ssh -p {str(port)} {user}@{ip} docker exec {container_name} cat /etc/swift/proxy-server.conf > Backup_dir_in_your_server/{container_name}-proxy-server.conf"
          get_conf_process = subprocess.run(get_conf_command, shell=True)
          bar()
          if get_conf_process.returncode == 1:
             print("\033[91mFailure in getting proxy-server.conf\033[0m")
            
          get_conf_command =  f"ssh -p {str(port)} {user}@{ip} docker exec {container_name} swift-ring-builder /rings/account.builder > Backup_dir_in_your_server/{container_name}-account-ring.txt"
          get_conf_process = subprocess.run(get_conf_command, shell=True)
          bar()
          if get_conf_process.returncode == 1:
             print("\033[91mFailure in getting account-ring\033[0m")
             
          get_conf_command =  f"ssh -p {str(port)} {user}@{ip} docker exec {container_name} swift-ring-builder /rings/container.builder > Backup_dir_in_your_server/{container_name}-container-ring.txt"
          get_conf_process = subprocess.run(get_conf_command, shell=True)
          bar()
          if get_conf_process.returncode == 1:
             print("\033[91mFailure in getting container-ring\033[0m")

          get_conf_command =  f"ssh -p {str(port)} {user}@{ip} docker exec {container_name} swift-ring-builder /rings/object.builder > Backup_dir_in_your_server/{container_name}-object-ring.txt"
          get_conf_process = subprocess.run(get_conf_command, shell=True)
          bar()
          if get_conf_process.returncode == 1:
             print("\033[91mFailure in getting object-ring\033[0m")

process_input_file(start_time_str, end_time_str)
