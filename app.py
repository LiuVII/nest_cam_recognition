import sys
import os
import select
import face_recognition
import glob
import shutil

from lib import nest_lib
from lib import data_utils
import settings

ACCURACY_THRESHOLD = 0.3

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
    print("Info: total number of faces in {0}: {1}".format(faces_dir, len(faces)))
    return faces

def recognize_faces(known_faces, file_names, save_res=True, move=True, remove=True):
    if len(known_faces) == 0:
        print("Info: recognition isn't active due to zero known faces in folder")
        return []
    compare_results = []
    unknown_files = []
    unknown_faces = get_faces(settings.snapshot_dir, unknown_files, remove)
    name_tags = [data_utils.get_name_tag(file_name) for file_name in file_names]
    for i in range(len(unknown_faces)):
        unknown_face = unknown_faces[i]
        res = face_recognition.compare_faces(known_faces, unknown_face)
        name_res = [name_tags[j] for j in range(len(known_faces)) if res[j]]
        compare_results.append(name_res)
        if save_res:
            # print("{0}:|{1}|{2}|".format(i, unknown_files[i], name_res[0] if len(name_res) > 0 else settings.unknown))
            data_utils.save_result(unknown_files[i], name_res[0] if len(name_res) > 0 else settings.unknown) 
    if move:
        shutil.rmtree(settings.snapshot_dir)
        data_utils.set_dirs([settings.snapshot_dir])
    return compare_results

def make_action(token, device_id, known_faces, file_names):
    try:
        prev_action_time = nest_lib.get_action_time(token, device_id)
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
        
        elif key == 'l':
            file_names = []
            known_faces = get_faces(file_names=file_names, remove=False)
        
        elif key == 'r' or key == 's':
            img_url = nest_lib.get_data(token, nest_lib.get_snapshot_url(device_id))["results"]
            data_utils.record_data(img_url, "jpg")
            if key == 'r':
                print(recognize_faces(known_faces, file_names))
        
        elif key == 'a' or key == 'm' or key == 't':
            last_event_data = nest_lib.get_data(token, nest_lib.get_action_url(device_id))["results"]
            if key == 't' or (last_event_data["has_person"] and last_event_data["start_time"] != prev_action_time):
                print("Info: someone detected")
                data_utils.record_data(last_event_data["animated_image_url"], "gif")
                if key != 't':
                    prev_action_time = last_event_data["start_time"]
                if key == 'a':
                    print(recognize_faces(known_faces, file_names))
            else:
                print("Info: no new action or person detected")

token = data_utils.get_token()
data_utils.set_dirs([settings.snapshot_dir, settings.known_faces_dir, settings.results_dir])
device_id = nest_lib.get_camera_id(token)
file_names = []
known_faces = get_faces(file_names=file_names, remove=False)
make_action(token, device_id, known_faces, file_names)
