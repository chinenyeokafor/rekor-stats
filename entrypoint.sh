#!/bin/bash

WATCH_DIR="/home"
QUIET_PERIOD=10

sleep 10

echo "Waiting for the volume to be fully populated..."

previous_file_count=$(find "$WATCH_DIR" -type f | wc -l)
sleep 5

# Function to check if the directory is stable
wait_for_stable_directory() {
  while ! is_directory_stable; do
    echo "Changes detected, waiting for $QUIET_PERIOD seconds of inactivity..."
    sleep $QUIET_PERIOD
  done
}

# Function to check if the directory is stable
is_directory_stable() {
  # Get the current file count
  current_file_count=$(find "$WATCH_DIR" -type f | wc -l)

  # Check if the current count has increased from the previous count
  if [ "$current_file_count" -gt "$previous_file_count" ]; then
    echo "False: revious_file_count $previous_file_count and current_file_count $current_file_count ..."
    previous_file_count=$current_file_count
    return 1 
  else
    echo "True: previous_file_count $previous_file_count and current_file_count $current_file_count ..."
    return 0  
  fi

}

wait_for_stable_directory

echo "Volume is fully populated. Starting the script"

# Run custom script
bash /home/rekor-stats/getrekordata.sh


tail -f /dev/null
