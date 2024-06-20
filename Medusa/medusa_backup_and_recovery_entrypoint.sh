#!/bin/sh

echo "Starting Medusa Tests Container"

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

# Workaround for https://github.com/istio/istio/issues/6324 if a job
# This is never reached if the above doesn't terminate (i.e. not a job)
curl -sfI -X POST http://127.0.0.1:15020/quitquitquit

echo "Exiting Medusa Tests Container"

# exit with main job's exit code
exit $mainExit
