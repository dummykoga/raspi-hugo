from __future__ import print_function
from apiclient.discovery import build
from apiclient.http import MediaIoBaseDownload
from httplib2 import Http
from oauth2client import file, client, tools
import subprocess
from re import findall

base_dir = "ci/"
# Setup the Drive v3 API
SCOPES = 'https://www.googleapis.com/auth/drive.readonly'
store = file.Storage(base_dir + 'credentials.json')
creds = store.get()
if not creds or creds.invalid:
    flow = client.flow_from_clientsecrets(base_dir + 'client_secret.json', SCOPES)
    creds = tools.run_flow(flow, store)
service = build('drive', 'v3', http=creds.authorize(Http()))

# Define variables
parent_folder_id = ""
post_data = []

new_files = []
deleted_files = []
download_dir = "downloaded/"
post_dir = "content/post/"

# Retrieve the parent folder
parent_folder = service.files().list(
    fields="nextPageToken, files(id, name)", 
    q="name = 'posts' and mimeType = 'application/vnd.google-apps.folder'").execute().get('files', [])

# Get parent folder id
if not parent_folder:
    print('Parent folder not found.')
else:
    print('Parent Folder: ', end="")
    for parent in parent_folder:
        print(parent['name'], end=" ")
        parent_folder_id = parent['id']
        print('<' + parent_folder_id + '>')

    # Create a list of posts
    post_list = service.files().list(
                q="'" + parent_folder_id + "' in parents").execute().get('files', [])
    for post in post_list:
        post_data.append((post['id'], post['name']))

    # Download each post
    # Create temporary directory "downloaded"
    subprocess.call(['mkdir', download_dir])
    for datum in post_data:
        request = service.files().get_media(fileId=datum[0])
        fh = open(download_dir + datum[1], 'w')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
                status, done = downloader.next_chunk()
                print("Downloaded", datum[1])
        fh.close()

    # Check for difference in files
    command = "diff " + download_dir + " " + post_dir
    output, error = subprocess.Popen(command.split(), stdout = subprocess.PIPE, stderr = subprocess.PIPE).communicate()
    
    regex_in_downloaded = "Only in " + download_dir + ": (.*)\s*"
    regex_in_posts = "Only in " + post_dir + ": (.*)\s*"

    new_found_files = findall(regex_in_downloaded, output)
    deleted_found_files = findall(regex_in_posts, output)

    if output != "":
        
        print("Change detected")
        subprocess.call(['cp', '-r', download_dir+".", post_dir]) 
        print("Changes applied to " + post_dir)

        if new_found_files != -1:
            for found_file in new_found_files:
                new_files.append(found_file)
        for new_file in new_files:     
            print("new file: " + new_file)

        if deleted_found_files != -1:
            for found_file in deleted_found_files:
                deleted_files.append(found_file)
        for deleted_file in deleted_files:
            subprocess.call(['rm', post_dir+deleted_file])
            print("deleted file: " + deleted_file)
    
    else:
        print("No change detected")
    
    # Delete directory "downloaded"
    subprocess.call(['rm', '-rf', 'downloaded'])

    # subprocess.call(['./sample.sh', '"yeah"'])
