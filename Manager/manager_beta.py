import sys
import os
import subprocess
import time
import yaml
import argparse

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
    output_subdirs = []
    if 'scenario' in data_loaded:
        for task in data_loaded['scenario']:
            if 'Config_gen' in task:
                config_params = task['Config_gen']
                input_files = config_params.get('conf_templates', [])
                output_path = config_params.get('output_path')
                for input_file in input_files:
                    # Create output directory for each input file
                    output_subdir = os.path.join(output_path, os.path.splitext(os.path.basename(input_file))[0])
                    config_gen.main(input_file, output_subdir)
                    output_subdirs.append(output_subdir)
    else:
        print("No scenario found in the configuration file.")
    return output_subdirs

def mrbench_agent(output_subdirs):
    data_loaded = load_config(config_file)
    all_start_times = []
    all_end_times = []
    if 'scenario' in data_loaded:
        for task in data_loaded['scenario']:
            if 'Mrbench' in task:
                config_params = task['Mrbench']
                one_input_conf = config_params.get('input_config')
                result_dir = config_params.get('output_path')
                run_status_reporter = config_params.get('Status_Reporter', False)
                run_monstaver = config_params.get('monstaver', False)
                ring_dir = config_params.get('ring_dir')
                conf_dir = config_params.get('conf_dir')
                mrbench.copy_swift_conf(ring_dir, conf_dir)
                if one_input_conf:
                   start_time, end_time, result_file_path = mrbench.main(one_input_conf, result_dir)
                   all_start_times.append(start_time)
                   all_end_times.append(end_time)
                   if run_status_reporter:
                      status_reporter.main(result_file_path, start_time, end_time)
                   if run_monstaver:
                      monstaver.main(time_range=f"{start_time},{end_time}", inputs=[result_file_path], delete=True)        
                else:
                    subdirs = output_subdirs
                    for subdir in subdirs:
                        if os.path.basename(subdir) == "workloads":
                           for test_config in os.listdir(subdir):
                               test_config_path = os.path.join(subdir, test_config)
                               start_time, end_time, result_file_path = mrbench.main(test_config_path, result_dir)
                               all_start_times.append(start_time)
                               all_end_times.append(end_time)
                               if run_status_reporter:
                                  status_reporter.main(result_file_path, start_time, end_time)  
                               if run_monstaver:
                                  monstaver.main(time_range=f"{start_time},{end_time}", inputs=[result_file_path], delete=True)                         
    else:
        print("No scenario found in the configuration file.")
    # Extract first start time and last end time
    first_start_time = all_start_times[0] 
    last_end_time = all_end_times[-1] 
    return first_start_time, last_end_time, result_file_path

def monstaver_backup_agent(first_start_time, last_end_time, result_file_path):
    data_loaded = load_config(config_file)
    if 'scenario' in data_loaded:
        for task in data_loaded['scenario']:
            if 'Monstaver' in task:
                config_params = task['Monstaver']
                operation = config_params.get('operation')
                batch_mode = config_params.get('batch_mode', False)
                times_file = config_params.get('time')
                input_path = config_params.get('input_path')
                if times_file:
                   with open(times_file, 'r') as file:
                        times = file.readlines()
                        for time_range in times:
                            start_time, end_time = time_range.strip().split(',')
                            if input_path:
                               if operation == "backup":
                                  monstaver.main(time_range=f"{start_time},{end_time}", inputs=[input_path], delete=True)
                            elif operation == "restore":
                                 monstaver.restore()          
                elif operation == "backup":
                     if batch_mode:
                        monstaver.main(time_range=f"{first_start_time},{last_end_time}", inputs=[result_file_path], delete=True)
                elif operation == "restore":
                     monstaver.restore()
    else:
        print("No scenario found in the configuration file.")

def status_reporter_agent():
    data_loaded = load_config(config_file)
    if 'scenario' in data_loaded:
        for task in data_loaded['scenario']:
            if 'Status-Reporter' in task:
                config_params = task['Status-Reporter']
                result_dir = config_params.get('output_path')
                times = config_params.get('times')

    #status_reporter.main(path_dir=result_file_path, time_range=f"{start_time},{end_time}", img=True)



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

    output_subdirs = config_gen_agent()
   
    first_start_time, last_end_time, result_file_path  = mrbench_agent(output_subdirs)
   
    #status_reporter_agent(result_file_path, start_time, end_time)
   
    monstaver_backup_agent(first_start_time, last_end_time, result_file_path)

    #monstaver_restore_agent()
    #analyzer_merge_agent(input_parent, csv)
    #time.sleep(10)
    #analyzer_analyze_agent(input_parent + "/*-merge.csv", transformation_dir)
    #report_recorder_agent(input_template, output_html, kateb_title)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='kara tools manager')
    parser.add_argument('-sn', '--scenario_name', help='input scenario path')
    args = parser.parse_args()
    config_file = args.scenario_name
    main()
