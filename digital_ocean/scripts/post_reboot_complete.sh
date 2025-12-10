#!/bin/bash

# This script logs that all post-setup processes have completed.
LOGFILE="/home/deploy/setup_complete.log"

echo "$(date) - All setup processes completed successfully." | tee -a "$LOGFILE"
