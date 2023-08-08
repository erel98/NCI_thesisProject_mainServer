#!/bin/bash
while true; do
    echo "Starting data synchronization at $(date)"
    
    rsync -az -e 'ssh -i ./x21245312_key.pem' ./NCI_thesisProject_mainServer/main.py ec2-13-40-224-46.eu-west-2.compute.amazonaws.com:/home/ubuntu/NCI_thesisProject_backupServer
    
    echo "Service synchronization completed at $(date)" 
    
    sleep 3600
done