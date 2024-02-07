import sys
import os
import subprocess
import time
import yaml

sys.path.append('./../Status_reporter/')
sys.path.append('./../Monstaver/')
sys.path.append('./../Analyzer/')
sys.path.append('./../Config_gen/')
sys.path.append('./../Report_recorder/')
sys.path.append('./../Mrbench/')

import mrbench
import config_gen
import status_reporter
import monstaver
import analyzer_merger

# Defining paths
config_file = "./../Manager/manager_sc1.conf"

def load_config(config_file):
    with open(config_file, "r") as stream:
        try:
           data_loaded = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
           print(f"Error loading the configuration: {exc}")
           sys.exit(1)
    return data_loaded

def config_gen_agent():
    data_loaded = load_config(config_file)
    if 'scenario' in data_loaded:
        for task in data_loaded['scenario']:
            if 'Config_gen' in task:
                config_params = task['Config_gen']
                input_files = config_params.get('conf_templates', [])
                output_dir = config_params.get('output_path')
                for input_file in input_files:
                    # Create output directory for each input file
                    output_subdir = os.path.join(output_dir, os.path.splitext(os.path.basename(input_file))[0])
                    os.makedirs(output_subdir, exist_ok=True)
                    config_gen.main(input_file, output_subdir)
                break
    else:
        print("No scenario found in the configuration file.")

def mrbench_agent(config_path, result_dir):
    data_loaded = load_config(config_file)
    start_time, end_time, result_file_path = mrbench.main(config_path, result_dir)
    return start_time, end_time, result_file_path

def status_reporter_agent(result_file_path, start_time, end_time):
    data_loaded = load_config(config_file)
    status_reporter.main(path_dir=result_file_path, time_range=f"{start_time},{end_time}", img=True)

def monstaver_backup_agent(result_file_path, start_time, end_time):
    data_loaded = load_config(config_file)
    monstaver.main(time_range=f"{start_time},{end_time}", inputs=[result_file_path], delete=True)

def monstaver_restore_agent():
    data_loaded = load_config(config_file)
    monstaver.restore()

def analyzer_merge_agent(input_dir, selected_csv):
    data_loaded = load_config(config_file)
    analyzer_merger.main_merge(input_directory=input_dir, selected_csv=selected_csv)

def analyzer_analyze_agent(csv_original, transformation_dir):
    data_loaded = load_config(config_file)
    analyzer_merger.main_analyze(csv_original=csv_original, transformation_directory=transformation_dir)

def report_recorder_agent( input_template, output_html, kateb_title):
    data_loaded = load_config(config_file)
    pybot = f"python3 ./../../pywikibot/report_recorder.py  -it {input_template} -oh {output_html} -kt {kateb_title}"
    subprocess.call(pybot, shell=True)

def main():
    data_loaded = load_config(config_file)
    config_gen_agent()
    start_time, end_time, result_file_path = mrbench_agent(input_config, output_parent)
    status_reporter_agent(result_file_path, start_time, end_time)
    monstaver_backup_agent(result_file_path, start_time, end_time)
    monstaver_restore_agent()
    analyzer_merge_agent(input_parent, csv)
    time.sleep(10)
    analyzer_analyze_agent(input_parent + "/*-merge.csv", transformation_dir)
    report_recorder_agent(input_template, output_html, kateb_title)

if __name__ == "__main__":
    main()
