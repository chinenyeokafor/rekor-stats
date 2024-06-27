#!/bin/bash

# Source the ~/.profile file to initialize the environment
source ~/.profile

touch /home/output.log
cd /home/rekor-stats/
python3 check-index.py > /home/output.log 2>&1


nohup python3 /home/rekor-stats/query.py >> /home/output.log 2>&1 &
