import datetime
import time
import os
import subprocess
import argparse
import sys
import pytz
import yaml
from alive_progress import alive_bar

config_file = "./../conf/Backup_Restore/monstaver.conf"

def load_config(config_file):
    with open(config_file, "r") as stream:
        try:
           data_loaded = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
           print(f"Error loading the configuration: {exc}")
           sys.exit(1)
    return data_loaded

def tehran_time_to_utc(tehran_time_str):
    tehran_tz = pytz.timezone('Asia/Tehran')
    utc_tz = pytz.utc
    tehran_time = tehran_tz.localize(tehran_time_str)
    utc_time = tehran_time.astimezone(utc_tz)
    return utc_time

def convert_time(start_time_str, end_time_str, margin_start, margin_end):
      start_datetime = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
      end_datetime = datetime.datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")

      # Convert Tehran time to UTC
      start_datetime_utc = tehran_time_to_utc(start_datetime)
      end_datetime_utc = tehran_time_to_utc(end_datetime)
    
      # Add the margins to datetime objects
      start_datetime_utc -= datetime.timedelta(seconds=margin_start)
      end_datetime_utc += datetime.timedelta(seconds=margin_end)

      # Convert the UTC datetime objects back to strings
      start_datetime_utc_str = start_datetime_utc.strftime("%Y-%m-%d %H:%M:%S")
      end_datetime_utc_str = end_datetime_utc.strftime("%Y-%m-%d %H:%M:%S")

      # Creating backup time format
      backup_start_date, backup_start_time = start_datetime_utc_str.split(" ")
      start_time_backup = backup_start_date + "T" + backup_start_time + "Z"
      backup_end_date, backup_end_time = end_datetime_utc_str.split(" ")
      end_time_backup = backup_end_date + "T" + backup_end_time + "Z"

      # Directory name creation
      dir_start_date, dir_start_time = start_time_str.split(" ")
      dir_start_date = dir_start_date[2:].replace("-", "")
      dir_start_time = dir_start_time.replace(":", "")
      dir_end_date, dir_end_time = end_time_str.split(" ")
      dir_end_date = dir_end_date[2:].replace("-", "")
      dir_end_time = dir_end_time.replace(":", "")
      time_dir_name = dir_start_date + "T" + dir_start_time + "_" + dir_end_date + "T" + dir_end_time
      return start_time_backup,end_time_backup,time_dir_name

def main(time_range=None, inputs=None, delete=False): 
    data_loaded = load_config(config_file)
    backup_dir = data_loaded['default'].get('backup_output')
    start_time_str, end_time_str = time_range.split(',')
    margin_start, margin_end = map(int, data_loaded['default'].get('time_margin').split(',')) 

    start_time_backup, end_time_backup, time_dir_name = convert_time(start_time_str, end_time_str, margin_start, margin_end)

    total_steps = 2 + (len(data_loaded['influxdbs']) * 6 + sum([len(data_loaded["influxdbs"][x]["databases"]) for x in data_loaded["influxdbs"]]) + len(data_loaded['swift']) * 9)
    with alive_bar(total_steps, title=f'\033[1mProcessing Backup\033[0m:\033[92m {start_time_str} - {end_time_str}\033[0m') as bar:

     subprocess.run(f"sudo mkdir -p {backup_dir}", shell=True)
     #create dbs-swif-other_info sub dirs in {time} directory 
     os.makedirs(f"{backup_dir}/{time_dir_name}", exist_ok=True)
     os.makedirs(f"{backup_dir}/{time_dir_name}/dbs", exist_ok=True)
     os.makedirs(f"{backup_dir}/{time_dir_name}/swift", exist_ok=True)
     os.makedirs(f"{backup_dir}/{time_dir_name}/other_info", exist_ok=True)
     os.makedirs(f"{backup_dir}/{time_dir_name}/hardware", exist_ok=True)
     subprocess.run(f"sudo chmod -R 777 {backup_dir}", shell=True)
     bar()

     database_names = [ db_name for config in data_loaded.get('influxdbs', {}).values() if isinstance(config, dict) and 'databases' in config for db_name in config['databases'].keys() ]
     for mc_server, config in data_loaded.get('influxdbs', {}).items(): 
         ip_influxdb = config.get('ip')
         ssh_port = config.get('ssh_port')
         ssh_user = config.get('ssh_user')
         container_name = config.get('container_name')
         influx_volume = config.get('influx_volume')
         for db_name in database_names:
             # Perform backup using influxd backup command
             backup_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec -i -u root {container_name} influxd backup -portable -db {db_name} -start {start_time_backup} -end {end_time_backup} {influx_volume}/{time_dir_name}/{container_name}/{db_name} > /dev/null 2>&1'"
             backup_process = subprocess.run(backup_command, shell=True)
             if backup_process.returncode == 0:
                  bar()
             else:
                  print("\033[91mBackup failed.\033[0m")
                  sys.exit(1)
        
         # New_location_backup_in_host = value['temporary_location_backup_host']
         tmp_backup = "/tmp/influxdb-backup-tmp"
         mkdir_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo mkdir -p {tmp_backup} && sudo chmod -R 777 {tmp_backup}'"
         mkdir_process = subprocess.run(mkdir_command, shell=True)
         if mkdir_process.returncode == 0:
             bar()
         else:
             print("\033[91mDirectory creation and permission setting failed.\033[0m")
             sys.exit(1)

         # copy backup to temporary dir 
         cp_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker cp {container_name}:{influx_volume}/{time_dir_name}/{container_name} {tmp_backup}'"
         cp_process = subprocess.run(cp_command, shell=True)
         if cp_process.returncode == 0:
             bar()
         else:
             print("\033[91mcopy failed.\033[0m")
             sys.exit(1)

         # tar all backup
         tar_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo tar -cf {tmp_backup}/{container_name}.tar.gz -C {tmp_backup}/{container_name}/ .'"
         tar_process = subprocess.run(tar_command, shell=True)
         if tar_process.returncode == 0:
             bar()
         else:
             print("\033[91mTar failed.\033[0m")
             sys.exit(1)

         # move tar file to dbs dir inside your server
         mv_command = f"scp -r -P {ssh_port} {ssh_user}@{ip_influxdb}:{tmp_backup}/*.tar.gz {backup_dir}/{time_dir_name}/dbs/ > /dev/null 2>&1"
         mv_process = subprocess.run(mv_command, shell=True)
         if mv_process.returncode == 0:
             bar()
         else:
             print("\033[91mMoving files failed.\033[0m")
             sys.exit(1)

         # remove temporary location of backup in host
         del_command_tmp_loc = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo rm -rf {tmp_backup}'"
         del_process = subprocess.run(del_command_tmp_loc, shell=True)
         if del_process.returncode == 0:
             bar()
         else:
             print("\033[91mRemove temp dir failed.\033[0m")
             sys.exit(1)

         # delete {time_dir} inside container
         del_time_cont = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec {container_name} rm -rf {influx_volume}'"
         del_time_process = subprocess.run(del_time_cont, shell=True)
         if del_time_process.returncode == 0:
             bar()
         else:
             print("\033[91mRemove time dir inside container failed.\033[0m")
             sys.exit(1)

     #copy other files
     for path in inputs:
         other_dir = f"sudo cp -rp {path} {backup_dir}/{time_dir_name}/other_info/"
         other_dir_process = subprocess.run(other_dir, shell=True)
         if other_dir_process.returncode == 0:
             time.sleep(1)
         else:
             print("\033[91mCopy paths failed.\033[0m")
             sys.exit(1)  

     # copy ring and config to output
     for key,value in data_loaded['swift'].items():
         container_name = key
         user = value['ssh_user']
         ip = value['ip_swift']
         port = value['ssh_port']
   
         get_conf_one_command =  f"ssh -p {str(port)} {user}@{ip} docker exec {container_name} cat /etc/swift/object-server.conf > {backup_dir}/{time_dir_name}/swift/{container_name}-object-server.conf"
         get_conf_one_process = subprocess.run(get_conf_one_command, shell=True)
         if get_conf_one_process.returncode == 0:
             bar()
         else:
             print("\033[91mFailure in getting object-server.conf\033[0m")
             sys.exit(1) 
    
         get_conf_two_command =  f"ssh -p {str(port)} {user}@{ip} docker exec {container_name} cat /etc/swift/container-server.conf > {backup_dir}/{time_dir_name}/swift/{container_name}-container-server.conf"
         get_conf_two_process = subprocess.run(get_conf_two_command, shell=True)
         if get_conf_two_process.returncode == 0:
             bar()
         else: 
             print("\033[91mFailure in getting container-server.conf\033[0m")
             sys.exit(1)
 
         get_conf_three_command =  f"ssh -p {str(port)} {user}@{ip} docker exec {container_name} cat /etc/swift/account-server.conf > {backup_dir}/{time_dir_name}/swift/{container_name}-account-server.conf"
         get_conf_three_process = subprocess.run(get_conf_three_command, shell=True)
         if get_conf_three_process.returncode == 0:
             bar()
         else: 
             print("\033[91mFailure in getting account-server.conf\033[0m")
             sys.exit(1)
 
         get_conf_four_command =  f"ssh -p {str(port)} {user}@{ip} docker exec {container_name} cat /etc/swift/proxy-server.conf > {backup_dir}/{time_dir_name}/swift/{container_name}-proxy-server.conf"
         get_conf_four_process = subprocess.run(get_conf_four_command, shell=True)
         if get_conf_four_process.returncode == 0:
             bar()
         else: 
             print("\033[91mFailure in getting proxy-server.conf\033[0m")
             sys.exit(1)

         get_conf_five_command =  f"ssh -p {str(port)} {user}@{ip} docker exec {container_name} swift-ring-builder /rings/account.builder > {backup_dir}/{time_dir_name}/swift/{container_name}-account-ring.txt"
         get_conf_five_process = subprocess.run(get_conf_five_command, shell=True)
         if get_conf_five_process.returncode == 0:
             bar()
         else: 
             print("\033[91mFailure in getting account-ring\033[0m")
             sys.exit(1)

         get_conf_six_command =  f"ssh -p {str(port)} {user}@{ip} docker exec {container_name} swift-ring-builder /rings/container.builder > {backup_dir}/{time_dir_name}/swift/{container_name}-container-ring.txt"
         get_conf_six_process = subprocess.run(get_conf_six_command, shell=True)
         if get_conf_six_process.returncode == 0:
             bar()
         else:  
             print("\033[91mFailure in getting container-ring\033[0m")
             sys.exit(1)
            
         get_conf_seven_command =  f"ssh -p {str(port)} {user}@{ip} docker exec {container_name} swift-ring-builder /rings/object.builder > {backup_dir}/{time_dir_name}/swift/{container_name}-object-ring.txt"
         get_conf_seven_process = subprocess.run(get_conf_seven_command, shell=True)
         if get_conf_seven_process.returncode == 0:
             bar()
         else: 
             print("\033[91mFailure in getting object-ring\033[0m")
             sys.exit(1)

         # run and save lshw & sysctl in host
         hwsys_command= f"ssh -p {str(port)} {user}@{ip} sudo lshw -html > {backup_dir}/{time_dir_name}/hardware/{container_name}-HW.html ; sudo sysctl -a > {backup_dir}/{time_dir_name}/hardware/{container_name}-SYS.txt"
         hwsys_process = subprocess.run(hwsys_command, shell=True)
         if hwsys_process.returncode == 0:
             bar()
         else:
             print("\033[91mlshw & sysctl failed.\033[0m")
             sys.exit(1)

         swift_init_command =  f"ssh -p {str(port)} {user}@{ip} 'docker exec {container_name} swift-init all status' > {backup_dir}/{time_dir_name}/swift/{container_name}-swift-status.txt"  
         swift_init_process = subprocess.run(swift_init_command, shell=True)
         if swift_init_process:
            bar()
                 
     # tar all result inside output dir
     tar_output = f"sudo tar -C {backup_dir} -cf {backup_dir}/{time_dir_name}.tar.gz {time_dir_name}"
     tar_output_process = subprocess.run(tar_output, shell=True)
     if tar_output_process.returncode == 0:
         bar()
     else:
         print("\033[91mTar time dir inside output dir failed.\033[0m")
         sys.exit(1)
 
     # delete orginal time dir inside output dir use -d switch        
     if delete:
        time_del = f"sudo rm -rf {backup_dir}/{time_dir_name}"
        time_del_process = subprocess.run(time_del, shell=True)
        if time_del_process.returncode == 0:
             time.sleep(1)
        else:
             print("\033[91mRemove time dir inside output dir failed.\033[0m")
             sys.exit(1)

if __name__ == "__main__":
    # Command-line argument parsing
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-t", "--time_range", help="Start and end times for backup (format: 'start_time,end_time')")
    argParser.add_argument("-r", "--delete", action="store_true", help="Remove the original time dir inside output dir")
    argParser.add_argument("-i", "--inputs", help="Input paths for copying to result")
    args = argParser.parse_args()
    data_loaded = load_config(config_file)
    main(time_range=args.time_range if args.time_range else data_loaded['default'].get('time'), inputs=args.inputs.split(',') if args.inputs else data_loaded['default'].get('input_paths') if data_loaded['default'].get('input_paths') else [], delete=args.delete)
