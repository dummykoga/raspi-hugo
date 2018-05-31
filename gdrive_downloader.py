from __future__ import print_function
from apiclient.discovery import build
from apiclient.http import MediaIoBaseDownload
from httplib2 import Http
from oauth2client import file, client, tools
import subprocess
from re import findall
import sys
from twython import Twython
import json,httplib

def delete_downloaded():
    # Delete directory "downloaded"
    subprocess.call(['rm', '-rf', 'downloaded'])
    print("\nDeleted temporary directory 'downloaded'")

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
    print('Parent folder found: ', end="")
    for parent in parent_folder:
        print(parent['name'], end=" ")
        parent_folder_id = parent['id']
        print('<' + parent_folder_id + '>\n')

    # Create a list of posts
    post_list = service.files().list(
                q="'" + parent_folder_id + "' in parents").execute().get('files', [])
    for post in post_list:
        post_data.append((post['id'], post['name']))

    # Download each post
    # Create temporary directory "downloaded"
    subprocess.call(['mkdir', download_dir])
    print("Created temporary directory 'downloaded/'\n")

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

    output = ""
    process = subprocess.Popen(command.split(), stdout = subprocess.PIPE)
    for line in iter(process.stdout.readline, ''):
        output += line
    # output, error = subprocess.Popen(command.split(), stdout = subprocess.PIPE, stderr = subprocess.PIPE).communicate()
    
    regex_in_downloaded = "Only in " + download_dir + ": (.*)\s*"
    regex_in_posts = "Only in " + post_dir + ": (.*)\s*"

    new_found_files = findall(regex_in_downloaded, output)
    deleted_found_files = findall(regex_in_posts, output)
    
    new_outputs = ""
    deleted_outputs = ""

    if output != "":
        
        print("\nChange detected")
        subprocess.call(['cp', '-r', download_dir+".", post_dir]) 
        print("Changes applied to " + post_dir + '\n')

        if new_found_files != -1:
            for found_file in new_found_files:
                new_files.append(found_file)
            new_outputs += "\n"

        for new_file in new_files:
            new_output = "+ new file: " + new_file
            print(new_output)
            new_outputs += new_output
        
        if deleted_found_files != -1:
            for found_file in deleted_found_files:
                deleted_files.append(found_file)
            deleted_outputs += "\n"

        for deleted_file in deleted_files:
            subprocess.call(['rm', post_dir+deleted_file])
            deleted_output = "- deleted file: " + deleted_file
            print(deleted_output)
            deleted_outputs += deleted_output
                    
        # Run deploy.sh to update website
        delete_downloaded()
        confirm = raw_input("\nPress Enter to continue:")
        print(confirm)
        subprocess.call(['./deploy.sh'])

        print("\nWebsite Updated!")

        # Tweet new article
        for new_file in new_files:
            postName = new_file[0:len(new_file)-3]
            blogUrl = "https://dummykoga.github.io/post/"
            tweetStr = "New Article Posted!\n" + blogUrl + postName

            # your twitter consumer and access information goes here
            apiKey = '187pyRShtHu1JIbprKcGNZHrF'
            apiSecret = 'qqwNc2rDH6OEy7VNfXqIGT4yhakuVRN2rYxEYSAmFsBrimHLGS'
            accessToken = '998793059922931712-87TnX00CNTZcARhbBQH81if597fTQMK'
            accessTokenSecret = 'HrVbgRJYZuTKQj2z6gXSsAXobjS67yv0OtK0xm58dkWdM'

            api = Twython(apiKey,apiSecret,accessToken,accessTokenSecret)
            api.update_status(status=tweetStr)
            print("Tweet posted!")

        connection = httplib.HTTPSConnection('api.pushed.co', 443)
        connection.connect()
        connection.request('POST', '/1/push', json.dumps({
            "app_key": "MwN9OerBuXGTcspFjn7k",
            "app_secret": "r475WFlMSc1yMZG92J1gzhck6sLaCRNdQPWezgPHT0ywWfevhp9nRhjZCPlJDQUH",
            "target_type": "app",
            "content": "Website updated." + new_outputs + deleted_outputs}),
            {
                "Content-Type": "application/json"
            }
        )
        result = json.loads(connection.getresponse().read())
        print("\nNotification pushed!")

    else:
        print("\nNo change detected")
        delete_downloaded()    

