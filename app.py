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
import shutil

def set_dirs(dirs):
    for dr in dirs:
        if not os.path.exists(dr):
            os.makedirs(dr)

def save_result(file_name, name, results_dir=settings.results_dir):
    save_dir = "{0}/{1}".format(results_dir, name)
    set_dirs([save_dir])
    shutil.copy(file_name, save_dir)

def get_name_tag(file_name):
    return file_name.split('/')[-1].split('.')[0].split('_')[0]

def get_faces(faces_dir=settings.known_faces_dir, file_names=[], remove=True):
    valid_img_types = [".jpg",".gif",".png"]
    faces = []
    for img_type in valid_img_types:
        for img_file in glob.glob('{0}/*{1}'.format(faces_dir, img_type)):
            img = face_recognition.load_image_file(img_file)
            img_encoded = face_recognition.face_encodings(img)
            file_names += [img_file] * len(img_encoded)
            if len(img_encoded) > 1:
                print("Info: file {0} contains {1} faces".format(img_file, len(img_encoded)))
            elif len(img_encoded) == 0 and remove:
                os.remove(img_file)
            faces += img_encoded
    print("Total number of faces in {0}: {1}".format(faces_dir, len(faces)))
    return faces

def recognize_faces(known_faces, file_names, save_res=True, move=True, remove=True):
    if len(known_faces) == 0:
        print("Info: recognition isn't active due to zero known faces in folder")
        return []
    compare_results = []
    unknown_files = []
    unknown_faces = get_faces(settings.snapshot_dir, unknown_files, remove)
    name_tags = [get_name_tag(file_name) for file_name in file_names]
    for i in range(len(unknown_faces)):
        unknown_face = unknown_faces[i]
        res = face_recognition.compare_faces(known_faces, unknown_face)
        name_res = [name_tags[j] for j in range(len(known_faces)) if res[j]]
        compare_results.append(name_res)
        if save_res:
            print("{0}:|{1}|{2}|".format(i, unknown_files[i], name_res[0] if len(name_res) > 0 else settings.unknown))
            save_result(unknown_files[i], name_res[0] if len(name_res) > 0 else settings.unknown) 
    if move:
        shutil.rmtree(settings.snapshot_dir)
        set_dirs([settings.snapshot_dir])
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
        print("{0}_{1}.png".format(name_prefix, i))
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

def make_action(token, device_id, known_faces, file_names):
    try:
        prev_action_time = nest_lib.get_data(token, get_action_url(device_id))["results"]["start_time"]
    except:
        print("Info: No prior action stored, resetting to empty")
    # prev_action_time = ""

    print("Info: camera is ready")
    while True:
        key = 0
        while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.read(1)
            if not key:
                exit(0)

        if key == 'q':
            return
        elif key == 'l':
            file_names = []
            known_faces = get_faces(file_names=file_names, remove=False)
        elif key == 'r' or key == 's':
            try:
                img_url = nest_lib.get_data(token, get_snapshot_url(device_id))["results"]
                record_data(img_url, "jpg")
            except:
                print("Error: unknown in record_data")
            if key == 'r':
                print(recognize_faces(known_faces, file_names))
        elif key == 'a' or key == 'm' or key == 't':
            last_event_data = nest_lib.get_data(token, get_action_url(device_id))["results"]
            if key == 't'or last_event_data["has_person"] and last_event_data["start_time"] != prev_action_time:
                if key != 't':
                    prev_action_time = last_event_data["start_time"]
                print("someone detected")
                try:
                    record_data(last_event_data["animated_image_url"], "gif")
                except:
                    print("Error: unknown in record_data")
                if key == 'a':
                    print(recognize_faces(known_faces, file_names))
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
set_dirs([settings.snapshot_dir, settings.known_faces_dir, settings.results_dir])
device_id = get_camera_id(token)
file_names = []
known_faces = get_faces(file_names=file_names, remove=False)
make_action(token, device_id, known_faces, file_names)
