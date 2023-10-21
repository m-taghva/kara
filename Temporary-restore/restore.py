import os
import subprocess
import argparse
import sys
import json

# Specify address to address.json file
address_file_path = "./../conf/Software/InfluxdbConfig.json"

# Load the JSON data from the file and define adresses as a variable 
with open(address_file_path, 'r') as file:
    json_data = json.load(file)
Secondry_influxdb_in_container_address = json_data['Backup_influxdb_in_container_address']
Secondary_influxdb_container_name = json_data['Backup_influxdb_container_name']
Secondary_influxdb_DB_name = json_data['Backup_influxdb_DB_name']
Secondary_influxdb_address_in_host = json_data['Backup_influxdb_address_in_host']
Temporary_datasource_name = json_data['Temporary_datasource_name']
Main_influxdb_DB_name = json_data['Main_influxdb_DB_name']
# Process given directory name as an arqument
argParser = argparse.ArgumentParser()
argParser.add_argument("-d", "--directoryname", help="Directory Name (Directory which contain *.tar,gz)")
args = argParser.parse_args()
directoryname = args.directoryname

print(f"*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-* START OF RESTORE FOR\033[92m {directoryname} \033[0m*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")

# Drop database
#drop_command = f"docker exec -it {Secondary_influxdb_container_name} influx -execute 'drop database {Secondary_influxdb_DB_name}'"
#drop_process = subprocess.run(drop_command, shell=True)
#exit_code = drop_process.returncode
#if exit_code == 0:
#   print(f"\033[92mDatabase {Secondary_influxdb_DB_name} successfully.\033[0m")
#   print()
#else:
#   print(f"\033[91mDropping {Secondary_influxdb_DB_name} failed.\033[0m")
#   print()

# Extract the backup.tar.gz
extract_command = f"tar -xf {Secondary_influxdb_address_in_host}/{directoryname}/*.tar.gz -C {Secondary_influxdb_address_in_host}/{directoryname}/backup/"
extract_process = subprocess.run(extract_command, shell=True)
exit_code = extract_process.returncode
if exit_code == 0:
   print("\033[92mBackup extracted successfully.\033[0m")
   print()
else:
   print("\033[91mExtraction failed.\033[0m")
   print() 

# Restore on influxdb phase
# Ckeck if it is first backup or not
# Define the command you want to run
check_command = f"docker exec -it {Secondary_influxdb_container_name} influx -execute 'show databases'"

# Run the command and capture its output
try:
    output_bytes = subprocess.check_output(check_command, shell=True)
    output = output_bytes.decode('utf-8')
except subprocess.CalledProcessError as e:
    # Handle any errors or exceptions here
    print(f"\033[91mChecking command failed with error : \033[0m: {e}")
    output = None

# Print the captured output and check for "opentsdb"
if output is not None and Main_influxdb_DB_name in output:
   restore_command = f"docker exec -it {Secondary_influxdb_container_name} influxd restore -portable -db {Main_influxdb_DB_name} -newdb {Temporary_datasource_name} {Secondry_influxdb_in_container_address}/{directoryname}/backup/ "
   restore_process = subprocess.run(restore_command, shell=True)
   restore_exit_code = restore_process.returncode
   if restore_exit_code == 1:
      print("\033[91mRestore failed.\033[0m")
      print()
      
      # Merge phase
      merge_command = f"docker exec -it {Secondary_influxdb_container_name} influx -execute 'SELECT * INTO \"{Main_influxdb_DB_name}\".autogen.:MEASUREMENT FROM \"{Temporary_datasource_name}\".autogen./.*/ GROUP BY *'"
      merge_process = subprocess.run(merge_command, shell=True)
      merge_exit_code = merge_process.returncode
      if merge_exit_code == 1:
         print("\033[91mFailure in merging.\033[0m")
         print()

      # Drop tmp db
      drop_tmp_command = f"docker exec -it {Secondary_influxdb_container_name} influx -execute 'drop database {Temporary_datasource_name}'"
      drop_tmp_process = subprocess.run(drop_tmp_command, shell=True)
      drop_tmp_exit_code = drop_tmp_process.returncode
      if drop_tmp_exit_code == 1:
         print(f"\033[91mFailure in dropping {Temporary_datasource_name}.\033[0m")
         print()

      if restore_exit_code & merge_exit_code & drop_tmp_exit_code == 1:
         print("\033[92mBackup restored successfully.\033[0m")
         print()

elif output is not None and Main_influxdb_DB_name not in output:
      restore_command = f"docker exec -it {Secondary_influxdb_container_name} influxd restore -portable -db {Main_influxdb_DB_name} {Secondry_influxdb_in_container_address}/{directoryname}/backup/ "
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


