#!/bin/bash

echo -e "\033[1mWelcome to cos-bench\033[0m"
echo -e "1 -> \033[32mBackup\033[0m"
echo -e "2 -> \033[34mRestore\033[0m"
echo -n "Enter the number of the action to perform: "
read number

case $number in
    1)
        clear
        echo -e "-*-*-*-*-*-*-*-*-> \033[32mRunning backup\033[0m <-*-*-*-*-*-*-*-*-"
        cd ./app
        python3 send_load.py 
        ;;
    2)
        clear
        echo -e "-*-*-*-*-*-*-*-*-> \033[34mRunning restore\033[0m <-*-*-*-*-*-*-*-*-"
        echo -ne "\033[1mEnter Dir name to Restore\033[0m: "
        read dir_name
        cd ./Temporary-restore
        python3 restore.py -d $dir_name
        ;;
    *)
        echo -e "\033[31m Unknown Process\033[0m"
        ;;
esac