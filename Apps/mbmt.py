#!/usr/bin/env python3

import sys
import getopt
import os
import subprocess

def usage():
    print("""
    send_load.py [OPTIONS]

Options:
  -s, --script-file <file>    : Path to the script file. (Default: ./pre_test_script.sh)

Description:
  This script sends load to a cluster based on the provided benchmark and default files.
  Script-file is executed before every test.

Example usage:

  send_load.py -s /path/to/script.sh    (uses default benchmark and default files)
""")


def main(argv):
    # Default input and default files
    script_file = "./pre_test_script.sh"

    # Parse command line arguments
    try:
        opts, args = getopt.getopt(argv, "hs:", ["script-file="])
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt in ("-s", "--script-file"):
            script_file = arg
 
    # Call the main program 
    run = f"python3 main2.py  {script_file}"
    run_process = subprocess.run(run,shell=True)

    # Check if the subprocess has finished
    if run_process.returncode == 0:
       # Run another Python script after workloadgen.py has finished
       merge = ["python3", "csv-merger.py", "./../result,all_hosts_output.csv"] 
       subprocess.run(merge, check=True)

if __name__ == "__main__":
    main(sys.argv[1:])
