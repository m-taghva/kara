#!/bin/bash
if [ -z "$(ls -A "/etc/kara/analyzer.conf")" ]; then
  cp manager/sample_configs/analyzer.conf /etc/kara
fi 2> /dev/null

if [ -z "$(ls -A "/etc/kara/monstaver.conf")" ]; then
  cp manager/sample_configs/monstaver.conf /etc/kara
fi 2> /dev/null

if [ -z "$(ls -A "/etc/kara/mrbench.conf")" ]; then
  cp manager/sample_configs/mrbench.conf /etc/kara
fi 2> /dev/null

if [ -z "$(ls -A "/etc/kara/status_reporter.conf")" ]; then
  cp manager/sample_configs/status_reporter.conf /etc/kara
fi 2> /dev/null

if [ -z "$(ls -A "/etc/kara/report_recorder.conf")" ]; then
  cp manager/sample_configs/report_recorder.conf /etc/kara
fi 2> /dev/null

if [ -z "$(ls -A "/home/kara/manager/scenario_dir/")" ]; then
  cp manager/sample_configs/scenario_dir/* /home/kara/manager/scenario_dir/
fi 2> /dev/null

if [ -z "$(ls -A "/home/kara/status_reporter/jsons/")" ]; then
  cp manager/sample_configs/jsons/* /home/kara/status_reporter/jsons/
fi 2> /dev/null

if [ -z "$(ls -A "/home/kara/status_reporter/metrics")" ]; then
  cp manager/sample_configs/metrics/* /home/kara/status_reporter/metrics/
fi 2> /dev/null

if [ -z "$(ls -A "/home/kara/config_gen/workloads-configs")" ]; then
  cp manager/sample_configs/workloads-configs/* /home/kara/config_gen/workloads-configs
fi 2> /dev/null
