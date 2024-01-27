import os
import subprocess
import argparse

def get_conf(host_file_path):

    # Read first line of hosts to execute ring files
    with open(host_file_path, 'r') as file:
        lines = file.readlines()
        for line in lines:
            words = line.strip().split(',')

            user = words[0].strip()
            monster_host_ip = words[1].strip()
            monster_container_name = words[2].strip()

            # excute *.conf with cat ?
            # execute container-server.conf
            container_server_command = f"ssh {user}@{monster_host_ip} docker exec {monster_container_name} cat /etc/swift/container-server.conf > ./{monster_host_ip}-container-server.conf"
            container_server_process = subprocess.run(container_server_command, shell=True)
            container_server_exit_code = container_server_process.returncode
            
            # execute account-server.conf
            account_server_command = f"ssh {user}@{monster_host_ip} docker exec {monster_container_name} cat /etc/swift/account-server.conf > ./{monster_host_ip}-account-server.conf"
            account_server_process = subprocess.run(account_server_command, shell=True)
            account_server_exit_code = account_server_process.returncode
            
            # execute account-server.conf
            object_server_command = f"ssh {user}@{monster_host_ip} docker exec {monster_container_name} cat /etc/swift/object-server.conf > ./{monster_host_ip}-object-server.conf"
            object_server_process = subprocess.run(object_server_command, shell=True)
            object_server_exit_code = object_server_process.returncode
            
            # execute proxy-server.conf
            proxy_server_command = f"ssh {user}@{monster_host_ip} docker exec {monster_container_name} cat /etc/swift/proxy-server.conf > ./{monster_host_ip}-proxy-server.conf"
            proxy_server_process = subprocess.run(proxy_server_command, shell=True)
            proxy_server_exit_code = proxy_server_process.returncode

        # Print output
        if container_server_exit_code & account_server_exit_code & object_server_exit_code & proxy_server_exit_code == 0:
            #print(f"\033[92mALL conf files generated successfully\n\033[0m")
            print()
        elif container_server_exit_code == 1:
            print("\033[91mFailure in generating container-server.conf\033[0m")
        elif account_server_exit_code == 1:
            print("\033[91mFailure in generating account-server.conf\033[0m")
        elif object_server_exit_code == 1:
            print("\033[91mFailure in generating object-server.conf\033[0m")
        elif proxy_server_exit_code == 1:
            print("\033[91mFailure in generating proxy-server.conf\033[0m")

if __name__ == "__main__":
    # Parse command-line arguments
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-f", "--hostfile", help="host file path")
    args = argParser.parse_args()

    if args.hostfile:
        # Call the function with the provided arguments
        result = get_conf(args.hostfile)
    else:
        print("Please provide a host file using the -f or --hostfile argument.")
