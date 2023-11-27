import os
import sys
import getopt
import subprocess
import time

# Defining paths
metric_sum_file = "./../conf/Status-reporter/sum_metric_list.txt"
metric_mean_file = "./../conf/Status-reporter/mean_metric_list.txt"
metric_max_file = "./../conf/Status-reporter/max_metric_list.txt"
metric_min_file = "./../conf/Status-reporter/min_metric_list.txt"
input_config_gen = "./input.txt"
output_config_gen = "./workloads"
result_path = "./../result"
script_file = "./pre_test_script.sh"
transformation_dir = "./../conf/Status-reporter/transformation-cpu"

def usage():
    print("""
   manager.py [OPTIONS]

Options:
        -s, --script-file <file> : Path to the script file. (Default: ./pre_test_script.sh)
  
Example usage:
              manager.py -s /path/to/script.sh
""")

# Extract start and end times from the "time" file
def extract_time_range(time_file_path):
    with open(time_file_path, 'r') as time_file:
        content = time_file.read().strip()  
        start_time, end_time = content.split(',')
        return start_time, end_time

def main(argv):
    global script_file

    # Parse command line arguments
    try:
        opts, args = getopt.getopt(argv, "hs:", ["script-file="])
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt in ("-s", "--script-file"):
            script_file = arg
            # Validate that the specified script file exists
            if not os.path.isfile(script_file):
                print(f"Error: The specified script file '{script_file}' does not exist. Exiting.")
                sys.exit(1)
    
    # Run config_gen.py
    config_gen = f"python3 ./config_gen.py -i {input_config_gen} -o {output_config_gen}"
    config_gen_process = subprocess.run(config_gen, shell=True)
    
    # Check if config_gen.py finished successfully
    if config_gen_process.returncode != 0:
        print("Error in config_gen.py. Exiting.")
        sys.exit(1)
    
    # Process config files in the output_config_gen directory
    for config_file in sorted(os.listdir(output_config_gen)):
        config_file_path = os.path.join(output_config_gen, config_file)
         
        # Run the pre-script before calling mrbench
        pre_script_process = subprocess.run(script_file, shell=True)
        if pre_script_process.returncode != 0:
            print(f"Error in {script_file}. Exiting.")
            sys.exit(1)

        # Call the main program for each XML file
        mrbench = f"python3 ./mrbench.py -i {config_file_path} -o {result_path}"
        mrbench_process = subprocess.run(mrbench, shell=True)

        # Check if mrbench.py finished successfully
        if mrbench_process.returncode != 0:
            print(f"Error in mrbench.py for {config_file_path}. Exiting.")
            sys.exit(1)

        # Extract start and end times from the "time" file
        time_file_path = os.path.join(result_path, config_file, "time")

        # Wait for the "time" file to be created 
        time.sleep(5)

        start_time, end_time = extract_time_range(time_file_path)

        # run status-reporter script 
        status = f"python3 ./../Status/status_reporter.py -m {metric_sum_file},{metric_mean_file} -t '{start_time},{end_time}' -d {result_path}/{config_file}"
        subprocess.call(status, shell=True)

        # run monstaver script 
        backup = f"python3 ./../Backup_restore/monstaver.py -i {result_path}/{config_file} -t '{start_time},{end_time}' -d"
        subprocess.call(backup, shell=True)
        
    # Run analyzer and merger script after all has finished
    merger = f"python3 ./../Status/csv_merger.py -i {result_path} -c *.csv"
    subprocess.call(merger, shell=True)
    analyzer = f"python3 ./../Status/status_analyzer.py -c {result_path}/*-merge.csv -d {transformation_dir}"
    subprocess.call(analyzer, shell=True)

if __name__ == "__main__":
    main(sys.argv[1:])
