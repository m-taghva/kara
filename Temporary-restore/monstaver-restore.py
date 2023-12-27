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
print()
print(f"*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-* START OF RESTORE FOR\033[92m {directoryname} \033[0m*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")

for mc_server, config in data_loaded.get('influxdbs', {}).items(): 
    ip_influxdb = config.get('ip')
    ssh_port = config.get('ssh_port')
    ssh_user = config.get('ssh_user')
    container_name = config.get('container_name')
    backup_location = config.get('backup_location')
    influx_mount_point = config.get('influx_mount_point')
    database = config.get('database')
    second_db = config.get('second_db')

    # Drop second_db
    drop_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} \"sudo docker exec -i -u root {container_name} influx -execute 'drop database {second_db}'\""
    drop_process = subprocess.run(drop_command, shell=True)
    exit_code = drop_process.returncode
    if exit_code == 0:
       print()
       print(f"\033[92mDrop database {second_db} successfully.\033[0m")
       print()
    else:
       print(f"\033[91mDrop database {second_db} failed.\033[0m")
       print()

    # Create seconf_db
    create_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} \"sudo docker exec -i -u root {container_name} influx -execute 'create database {second_db}'\""
    create_process = subprocess.run(create_command, shell=True)
    exit_code = create_process.returncode
    if exit_code == 0:
       print(f"\033[92mCreate database {second_db} successfully.\033[0m")
       print()
    else:
       print(f"\033[91mCreate database {second_db} failed.\033[0m")
       print()

    # Ensure the target restore directory exists
    create_dir_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec -i -u root {container_name} mkdir -p {influx_mount_point}/MPK_RESTORE/{directoryname}/backup_tar && sudo docker exec -i -u root {container_name} mkdir -p {influx_mount_point}/MPK_RESTORE/{directoryname}/backup_untar'"
    create_dir_process = subprocess.run(create_dir_command, shell=True)
    create_dir_exit_code = create_dir_process.returncode
    if create_dir_exit_code == 0:
       print("\033[92mRestore directory created successfully.\033[0m")
       print()
    else:
       print("\033[91mFailed to create restore directory.\033[0m")
       print()
       sys.exit(1)

    # Copy backup file to container mount point
    copy_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker cp {backup_location} {container_name}:{influx_mount_point}/MPK_RESTORE/{directoryname}/backup_tar'"
    copy_process = subprocess.run(copy_command, shell=True)
    exit_code = copy_process.returncode
    if exit_code == 0:
       print(f"\033[92mCopy to mount point successfully.\033[0m")
       print()
    else:
       print(f"\033[91mCopy to mount point failed.\033[0m")
       print()
    
    # Extract the backup.tar.gz
    extract_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec -i -u root {container_name} tar -xf {influx_mount_point}/MPK_RESTORE/{directoryname}/backup_tar/{container_name}.tar.gz -C {influx_mount_point}/MPK_RESTORE/{directoryname}/backup_untar/'"
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
       print()
       output = None

    # Print the captured output and check for "opentsdb"
    if output is not None and database in output:
       restore_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec -i -u root {container_name} influxd restore -portable -db {database} -newdb tempdb {influx_mount_point}/MPK_RESTORE/{directoryname}/backup_untar/{database} > /dev/null 2>&1'"
       restore_process = subprocess.run(restore_command, shell=True)
       restore_exit_code = restore_process.returncode
       if restore_exit_code == 0:
          print("\033[92mRestore data to temporary database successfully.\033[0m")
          print()
       else:
          print("\033[91mRestore data to temporary database failed.\033[0m")
          print()
      
       # Merge phase
       merge_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} \"sudo docker exec -i -u root {container_name} influx -execute 'SELECT * INTO \"{second_db}\".autogen.:MEASUREMENT FROM \"tempdb\".autogen./.*/ GROUP BY *'\" > /dev/null 2>&1 "
       merge_process = subprocess.run(merge_command, shell=True)
       merge_exit_code = merge_process.returncode
       if merge_exit_code == 0:
          print("\033[92mMerging data to second database successfully.\033[0m")
          print()
       else:
          print("\033[91mFailure in merging data to second database.\033[0m")
          print()

       # Drop tmp db
       drop_tmp_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} \"sudo docker exec -i -u root {container_name} influx -execute 'drop database tempdb'\""
       drop_tmp_process = subprocess.run(drop_tmp_command, shell=True)
       drop_tmp_exit_code = drop_tmp_process.returncode
       if drop_tmp_exit_code == 0:
          print("\033[92mDropping temporary database successfully.\033[0m")
          print()
          print("\033[92mAll restore processes complete.\033[0m")
          print()
       else:
          print("\033[91mDropping temporary database failed.\033[0m")
          print()

    elif output is not None and database not in output:
         restore_command = f"ssh -p {ssh_port} {ssh_user}@{ip_influxdb} 'sudo docker exec -i -u root {container_name} influxd restore -portable -db {database} {influx_mount_point}/MPK_RESTORE/{directoryname}/backup_untar'"
         restore_process = subprocess.run(restore_command, shell=True)
         restore_exit_code = restore_process.returncode
         if restore_exit_code == 1:
           print("\033[91mRestore failed.\033[0m")
           print()
         else:
            print("\033[92mBackup restored successfully(First Time Backup!).\033[0m")
    else:
         print("error") 
print(f"*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-* END OF RESTORE FOR\033[92m {directoryname} \033[0m*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
print()
