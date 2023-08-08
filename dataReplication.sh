#!/bin/bash
rsync -az -e 'ssh -i ./x21245312_key.pem' ./checkpoint.json ec2-13-40-224-46.eu-west-2.compute.amazonaws.com:/home/ubuntu/NCI_thesisProject_backupServer