import os
import sys
import getopt
import subprocess
import time
sys.path.append('./../Status/')
sys.path.append('./../Backup_restore/')
import mrbench
import config_gen
import status_reporter
import monstaver
import analyzer_merger

# Defining paths
input_config_gen = "./input.txt"
output_config_gen = "./workloads"
result_path = "./../results"
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

def main(argv):
    global script_file
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

    # RUN congig_gen
    config_gen.main(input_config_gen, output_config_gen)

    # Process config files in the output_config_gen directory
    for config_file in sorted(os.listdir(output_config_gen)):
        config_file_path = os.path.join(output_config_gen, config_file)     
        # Run the pre-script before calling mrbench
        pre_script_process = subprocess.run(script_file, shell=True)
        if pre_script_process.returncode != 0:
            print(f"Error in {script_file}. Exiting.")
            sys.exit(1)

        # RUN mrbench
        start_time, end_time, result_file_path = mrbench.main(config_file_path, result_path)

        # run status-reporter script 
        status_reporter.main(path_dir=result_file_path, time_range=f"{start_time},{end_time}", img=True)

        # run monstaver script 
        monstaver.main(time_range=f"{start_time},{end_time}", inputs=[result_file_path], delete=True)

    # Run analyzer and merger script after all has finished
    analyzer_merger.main_m(merge=True, input_directory=result_path, selected_csv="*.csv")
    time.sleep(10)
    analyzer_merger.main_a(analyze=True, csv_original=result_path + "/*-merge.csv", transformation_directory=transformation_dir)

if __name__ == "__main__":
    main(sys.argv[1:])
