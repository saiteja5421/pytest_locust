#!/bin/bash -xe

cd $WORKSPACE/Medusa
python3 -m venv venv && . venv/bin/activate && pip3 install -r requirements_dev.txt

git diff --relative --name-only origin/master...HEAD --diff-filter=ACM | grep '\.py$'| rev | cut -d'/' -f-20 | rev | awk -F"Medusa/" '{print $NF}' | awk '{print "'"'"'" $1 "'"'"'"}' | xargs -r black --line-length 120 --check --diff
retVal=$?
if [ $retVal -ne 0 ]; then
    echo "ERROR: Consider code formatting with black"
fi