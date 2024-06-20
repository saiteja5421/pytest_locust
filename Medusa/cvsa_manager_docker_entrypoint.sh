#!/bin/sh

echo "Starting cVSA Manager Functional Tests."

python3 -m utils.cvsa_cleaner

# trap the TERM and INT signals
# we need this to pass them to the actual application and ensure graceful shutdown
trap 'kill -TERM $PID' TERM INT

# execute passed-in parameters
$@ &

# wait for the program to end and capture main command exit code
PID=$!
wait $PID
trap - TERM INT
wait $PID
mainExit=$?

echo "Exiting cVSA Manager Functional Tests."

# Attempt to send XML file to S3.
python3 tests/functional/aws_protection/cvsa_manager/upload_test_results_to_s3.py || true # discard the error for sending XML file

# Workaround for https://github.com/istio/istio/issues/6324 if a job
# This is never reached if the above doesn't terminate (i.e. not a job)
curl -sfI -X POST http://127.0.0.1:15020/quitquitquit

# exit with main job's exit code
exit $mainExit
