#! /bin/bash
#watch -n 60 python gdrive_downloader.py
eval `ssh-agent`
ssh-add ~/.ssh/id_rsa_github
while true; do python gdrive_downloader.py; sleep 60; done
