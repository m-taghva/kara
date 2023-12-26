import os
import subprocess
import argparse
import sys
import yaml

config_file = "./../conf/Backup_Restore/monstaver-restore.conf"
with open(config_file, "r") as stream:
    try:
        data_loaded = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(f"Error loading the configuration: {exc}")
        sys.exit(1)

# Process given directory name as an arqument
argParser = argparse.ArgumentParser()
argParser.add_argument("-d", "--directoryname", help="Directory Name (Directory which contain *.tar,gz)")
args = argParser.parse_args()
directoryname = args.directoryname

print(f"*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-* START OF RESTORE FOR\033[92m {directoryname} \033[0m*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")

for mc_server, config in data_loaded.get('influxdbs', {}).items(): 
    ip_influxdb = config.get('ip')
    ssh_port = config.get('ssh_port')
    ssh_user = config.get('ssh_user')
    container_name = config.get('container_name')
    influx_extracted_data = config.get('influx_extracted_data')
    influx_restore_volume = config.get('influx_restore_volume')
    tempdb_name = config.get('temp_db')
    database = config.get('database')

    # Ensure the target restore directory exists
    create_dir_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec -i -u root {container_name} mkdir -p {influx_restore_volume}/{directoryname}/dbs/restore/'"
    create_dir_process = subprocess.run(create_dir_command, shell=True)
    create_dir_exit_code = create_dir_process.returncode
    if create_dir_exit_code == 0:
       print("\033[92mRestore directory created successfully.\033[0m")
    else:
       print("\033[91mFailed to create restore directory.\033[0m")
       sys.exit(1)

    # Extract the backup.tar.gz
    extract_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec -i -u root {container_name} tar -xf {influx_extracted_data}/{directoryname}/dbs/{container_name}.tar.gz -C {influx_restore_volume}/{directoryname}/dbs/restore/'"
    extract_process = subprocess.run(extract_command, shell=True)
    exit_code = extract_process.returncode
    if exit_code == 0:
       print("\033[92mBackup extracted successfully.\033[0m")
       print()
    else:
       print("\033[91mExtraction failed.\033[0m")
       print() 

    # Restore on influxdb phase - Ckeck if it is first backup or not - Define the command you want to run
    check_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} \"sudo docker exec -i -u root {container_name} influx -execute 'SHOW DATABASES'\""
    try:
       output_bytes = subprocess.check_output(check_command, shell=True)
       output = output_bytes.decode('utf-8')
    except subprocess.CalledProcessError as e:
       # Handle any errors or exceptions here
       print(f"\033[91mChecking command failed with error : \033[0m: {e}")
       output = None

    # Print the captured output and check for "opentsdb"
    if output is not None and database in output:
       restore_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec -i {container_name} influxd restore -portable -db {database} -newdb {tempdb_name} {influx_restore_volume}/{directoryname}/dbs/restore/{database}'"
       restore_process = subprocess.run(restore_command, shell=True)
       restore_exit_code = restore_process.returncode
       if restore_exit_code == 1:
           print("\033[91mRestore failed.\033[0m")
           print()
      
           # Merge phase
           merge_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec -i {container_name} influx -execute 'SELECT * INTO \"{database}\".autogen.:MEASUREMENT FROM \"{tempdb_name}\".autogen./.*/ GROUP BY *''"
           merge_process = subprocess.run(merge_command, shell=True)
           merge_exit_code = merge_process.returncode
           if merge_exit_code == 1:
              print("\033[91mFailure in merging.\033[0m")
              print()

           # Drop tmp db
           drop_tmp_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec -i {container_name} influx -execute 'drop database {tempdb_name}''"
           drop_tmp_process = subprocess.run(drop_tmp_command, shell=True)
           drop_tmp_exit_code = drop_tmp_process.returncode
           if drop_tmp_exit_code == 1:
              print(f"\033[91mFailure in dropping {tempdb_name}.\033[0m")
              print()
           if restore_exit_code & merge_exit_code & drop_tmp_exit_code == 1:
              print("\033[92mBackup restored successfully.\033[0m")
              print()

    elif output is not None and database not in output:
         restore_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec -i {container_name} influxd restore -portable -db {database} {influx_restore_volume}/{directoryname}/dbs/restore/{database}' "
         restore_process = subprocess.run(restore_command, shell=True)
         restore_exit_code = restore_process.returncode
         if restore_exit_code == 1:
            print("\033[91mRestore failed.\033[0m")
            print()
         else:
            print("\033[92mBackup restored successfully(First Time Backup!).\033[0m")
    else:
         print("error") 

print(f"*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-* END OF RESTORE FOR\033[92m {directoryname} \033[0m*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
