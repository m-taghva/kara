import sys
import getopt
import os
import subprocess
import shutil

# Defining paths
metric_sum_file = "./../conf/Status-reporter/sum_metric_list.txt"
metric_mean_file = "./../conf/Status-reporter/mean_metric_list.txt"
metric_max_file = "./../conf/Status-reporter/max_metric_list.txt"
metric_min_file = "./../conf/Status-reporter/min_metric_list.txt"
input_txt = "./input.txt"
output_xml = "./workloads"
result = "./../result"
script_file = "./pre_test_script.sh"

def usage():
    print("""
   manager.py [OPTIONS]

Options:
        -s, --script-file <file> : Path to the script file. (Default: ./pre_test_script.sh)
  
Example usage:
              manager.py -s /path/to/script.sh
""")

def perform_backup_and_report(start_time, end_time, result_path):
    # Construct the status-reporter command with the variables
    status = f"python3 ./../Status/status_reporter.py -m {metric_sum_file},{metric_mean_file} -t '{start_time},{end_time}' -d {result_path}"
    subprocess.call(status, shell=True) 
 
    # Run another Python script after run_test.py has finished
    merge = ["python3", "./../Status/csv_merger.py", f"{result},*-transformation-*.csv"]
    subprocess.run(merge, check=True)

    # Construct the backup command with the variables
    backup = f"python3 ./../Backup_restore/monstaver.py -t '{start_time},{end_time}' -d"
    subprocess.call(backup, shell=True)

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
    config_gen = f"python3 ./config_gen.py {input_txt},{output_xml}"
    config_gen_process = subprocess.run(config_gen, shell=True)
    
    # Check if config_gen.py finished successfully
    if config_gen_process.returncode != 0:
        print("Error in config_gen.py. Exiting.")
        sys.exit(1)

    # Process XML files in the ./workloads directory
    for xml_file in sorted(os.listdir(output_xml)):
        if xml_file.endswith(".xml"):
            xml_file_path = os.path.join(output_xml, xml_file)

            # Run the pre-script before calling run_test.py
            pre_script_process = subprocess.run(script_file, shell=True)
            if pre_script_process.returncode != 0:
                print(f"Error in {script_file}. Exiting.")
                sys.exit(1)
            
            # Call the main program for each XML file
            work = f"python3 ./mrbench.py {xml_file_path},{result}"
            work_process = subprocess.run(work, shell=True)
    
if __name__ == "__main__":
    main(sys.argv[1:])
