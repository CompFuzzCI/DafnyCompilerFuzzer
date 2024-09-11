#!/bin/bash

#arguments: fuzz, duration, author, branch | bisect, folder path, author, branch | process, issue no

if [ $# -eq 0 ]; then
    echo "Usage: $0 <option>"
    exit 1
fi

aws s3 cp s3://compfuzzci/base-files/scripts/ . --recursive
aws s3 cp s3://compfuzzci/base-files/jars/ . --recursive

chmod +x *.sh
chmod +x *.py

case "$1" in
    fuzz)
        python3 fuzzing_entrypoint.py $2 $3 $4
        ;;
    bisect)
        python3 bisect_entrypoint.py $2 $3 $4
        ;;
    process)
        python3 process_entrypoint.py $2
        ;;
    *)
        echo "Invalid option: $1"
        echo "Valid options are: fuzz, validate, process"
        exit 2
        ;;
esac