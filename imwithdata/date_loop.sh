#!/bin/bash
currentDateTs=$(date -j -f "%y.%m.%d" $1 "+%s")
endDateTs=$(date -j -f "%y.%m.%d" $2 "+%s")
offset=86400

while [ "$currentDateTs" -le "$endDateTs" ]
do
     date=$(date -j -f "%s" $currentDateTs "+%y.%m.%d")
     echo $date
     #python imwithdata/es_etl/es_etl.py --date $date
     python imwithdata/s3_etl/s3_etl.py s3 --date $date
     currentDateTs=$(($currentDateTs+$offset))
done
