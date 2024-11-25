#!/bin/bash
#Method: 
#       we return check1+check2+....
#       If the result is 0 -> is healthy


check1=1
cosbench_STAT=$( ps aux | grep start-all.sh | wc -l)
if [ "$cosbench_STAT" == "5" ]
then
    check1=0
fi

if [ "$check1" == "0" ]
then
    echo OK
else
    echo ERR
fi

