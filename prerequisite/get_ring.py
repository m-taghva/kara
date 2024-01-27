import os
import subprocess
import argparse

def get_ring(host_file_path):

    # Read first line of hosts to execute ring files
    with open(host_file_path, 'r') as file:
        first_line = file.readline().strip()
        words = first_line.strip().split(',')

        user = words[0].strip()
        monster_host_ip = words[1].strip()
        monster_container_name = words[2].strip()
    
    # Account ring executaion
    account_ring_exec_command = f"ssh {user}@{monster_host_ip} docker exec {monster_container_name} swift-ring-builder /rings/account.builder > ./account-ring.txt"
    account_ring_exec_process = subprocess.run(account_ring_exec_command, shell=True)
    account_ring_exec_exit_code = account_ring_exec_process.returncode

    # Object ring executaion
    object_ring_exec_command = f"ssh {user}@{monster_host_ip} docker exec {monster_container_name} swift-ring-builder /rings/object.builder > ./object-ring.txt"
    object_ring_exec_process = subprocess.run(object_ring_exec_command, shell=True)
    object_ring_exec_exit_code = object_ring_exec_process.returncode

    # Container ring executaion
    container_ring_exec_command = f"ssh {user}@{monster_host_ip} docker exec {monster_container_name} swift-ring-builder /rings/container.builder > ./container-ring.txt"
    container_ring_exec_process = subprocess.run(container_ring_exec_command, shell=True)
    container_ring_exec_exit_code = container_ring_exec_process.returncode

    # Check and print output
    if container_ring_exec_exit_code & object_ring_exec_exit_code & account_ring_exec_exit_code == 0:
        #print(f"\033[92mALL ring files generated successfully\n\033[0m")
        print()
    elif container_ring_exec_exit_code == 1:
        print("\033[91mFailure in generating container-ring.txt\033[0m")
    elif object_ring_exec_exit_code == 1:
        print("\033[91mFailure in generating object-ring.txt\033[0m")
    elif account_ring_exec_exit_code == 1:
        print("\033[91mFailure in generating account-ring.txt\033[0m")

if __name__ == "__main__":
    # Parse command-line arguments
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-f", "--hostfile", help="host file path")
    args = argParser.parse_args()

    if args.hostfile:
        # Call the function with the provided arguments
        result = get_ring(args.hostfile)
    else:
        print("Please provide a host file using the -f or --hostfile argument.")
