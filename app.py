import json
import sys
import os
import select
import time
from lib import nest_lib
import settings
from requests import request, get
from datetime import datetime
from PIL import Image
from io import BytesIO
import face_recognition
import glob

def set_dirs():
    dirs = [settings.snapshot_dir, settings.known_faces_dir]
    for dr in dirs:
        if not os.path.exists(dr):
            os.makedirs(dr)

def get_faces(faces_dir):
    valid_img_types = [".jpg",".gif",".png"]
    faces = []
    for img_type in valid_img_types:
        for img_file in glob.glob('{0}/*{1}'.format(faces_dir, img_type)):
            img = face_recognition.load_image_file(img_file)
            img_encoded = face_recognition.face_encodings(img)
            faces += img_encoded
    print("Total number of faces in {0}: {1}".format(faces_dir, len(faces)))
    return faces

known_faces = get_faces(settings.known_faces_dir)

def recognize_faces(known_faces=known_faces):
    if len(known_faces) == 0:
        print("Info: recognition isn't active due to zero known faces in folder")
        return []
    compare_results = []
    unknown_faces = get_faces(settings.snapshot_dir)
    for unknown_face in unknown_faces:
        res = face_recognition.compare_faces(known_faces, unknown_face)
        compare_results.append(res)
    return compare_results

def get_camera_url(nest_api_url=settings.nest_api_url):
    return "{0}/devices/cameras/".format(nest_api_url)

def get_snapshot_url(device_id, nest_api_url=settings.nest_api_url):
    return "{0}/devices/cameras/{1}/snapshot_url".format(nest_api_url, device_id)

def get_action_url(device_id, nest_api_url=settings.nest_api_url):
    return "{0}/devices/cameras/{1}/last_event".format(nest_api_url, device_id)

def get_camera_id(token):
    try:
        cameras = list(nest_lib.get_data(token, get_camera_url())["results"].keys())
        return cameras[0]
    except:
        print('No cameras were found')
        return ""


def split_animated(image, name_prefix):

    def iter_frames(image):
        try:
            palette = image.getpalette()
            i = 0
            while 1:
                image.seek(i)
                image_frame = image.copy()
                image_frame.putpalette(palette)
                yield image_frame
                i += 1
        except EOFError:
            pass

    for i, frame in enumerate(iter_frames(image)):
        frame.save("{0}_{1}.png".format(name_prefix, i), **frame.info)

def record_data(img_url, img_type, dir_name=settings.snapshot_dir):
    response = get(img_url)
    if response.status_code == 200:
        img_data = response.content
        if len(img_data) > 0:
            try:
                current_time = time.time()
                string_time = datetime.fromtimestamp(current_time).strftime('%Y%m%d-%H%M%S-%f')[:-4]
                if img_type == "jpg":
                    img_name = "{0}/{1}.jpg".format(dir_name, string_time)
                    print("snapshot", img_name)
                    with open(img_name, 'wb') as handler:
                        handler.write(img_data)
                elif img_type == "gif":
                    img_name_prefix = "{0}/{1}".format(dir_name, string_time)
                    img = Image.open(BytesIO(img_data))
                    split_animated(img, img_name_prefix)
            except:
                print("Error: something went wrong when saving the image")
        else:
            print("Warning: camera is most likely offline")
    else:
        print("Warning: response status from image url: {0}".format(response.status_code))
    return

def make_action(token, device_id):
    try:
        prev_action_time = nest_lib.get_data(token, get_action_url(device_id))["results"]["start_time"]
    except:
        print("Info: No prior action stored, resetting to empty")
        prev_action_time = ""

    print("Info: camera is ready")
    while True:
        key = 0
        while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.read(1)
            if not key:
                exit(0)

        if key == 'q':
            return
        elif key == 's':
            try:
                img_url = nest_lib.get_data(token, get_snapshot_url(device_id))["results"]
                record_data(img_url, "jpg")
            except:
                print("Error: unknown in record_data")
            print(recognize_faces())
        elif key == 'a':
            last_event_data = nest_lib.get_data(token, get_action_url(device_id))["results"]
            if last_event_data["has_person"] and last_event_data["start_time"] != prev_action_time:
                prev_action_time = last_event_data["start_time"]
                print("someone detected")
                try:
                    record_data(last_event_data["animated_image_url"], "gif")
                except:
                    print("Error: unknown in record_data")
                print(recognize_faces())
            else:
                print("Info: no new action or person detected")


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
set_dirs()
make_action(token, device_id)
