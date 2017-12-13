import json
import sys
import os
import select
import time
from lib import nest_lib
import settings
from requests import request, get
from datetime import datetime


def set_dirs():
    dirs = [settings.snapshot_dir]
    for dr in dirs:
        if not os.path.exists(dr):
            os.makedirs(dr)


def get_camera_url(nest_api_url=settings.nest_api_url):
    return "{0}/devices/cameras/".format(nest_api_url)


def get_snapshot_url(device_id, nest_api_url=settings.nest_api_url):
    return "{0}/devices/cameras/{1}/snapshot_url".format(nest_api_url, device_id)


def get_camera_id(token):
    try:
        cameras = list(nest_lib.get_data(token, get_camera_url())["results"].keys())
        return cameras[0]
    except:
        print('No cameras were found')
        return ""



def record_data(img_url, dir_name=settings.snapshot_dir):
    img_data = get(img_url).content
    current_time = time.time()
    string_time = datetime.fromtimestamp(current_time).strftime('%Y%m%d-%H%M%S-%f')[:-4]
    img_name = "{0}/{1}.jpg".format(dir_name, string_time)
    print("snapshot", img_name)
    with open(img_name, 'wb') as handler:
        handler.write(img_data)
    return


def make_snapshot(token, snapshot_url):
    key = 0
    while True:
        while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.read(1)
            if not key:
                exit(0)

        if key == 'q':
            return
        elif key == 's':
            img_url = nest_lib.get_data(token, snapshot_url)["results"]
            record_data(img_url)
        key = 0


with open('credentials.json', 'r+') as credfile:
    json_str = credfile.read()
    json_data = json.loads(json_str)
    
    #store token if none is present in credentials
    if not json_data["token"]:
        token = nest_lib.get_access(settings.authorization_code)
        json_data["token"] = token
        credfile.seek(0)
        json.dump(json_data, credfile)
        credfile.truncate()
    token = json_data["token"]

#data = nest_lib.get_data(token=token)
device_id = get_camera_id(token)
snapshot_url = get_snapshot_url(device_id)
print("cam is ready")
set_dirs()
make_snapshot(token, snapshot_url)
