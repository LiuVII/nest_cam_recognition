import sys
import os
import select
import face_recognition
import glob
import shutil
from collections import Counter, defaultdict
import sseclient
import urllib3
import json

from lib import nest_lib
from lib import data_utils
import settings
import interaction


CONFIDENCE_OVERALL = 0.3
CONFIDENCE_LOCAL = 0.5


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

    if len(unknown_faces) > 0:
        name_tags = [data_utils.get_name_tag(file_name) for file_name in file_names]
        for i in range(len(unknown_faces)):
            unknown_face = unknown_faces[i]
            res = face_recognition.compare_faces(known_faces, unknown_face)
            name_res = [name_tags[j] for j in range(len(known_faces)) if res[j]]
            compare_results.append(name_res)
            if save_res:
                data_utils.save_result(unknown_files[i], name_res[0] if len(name_res) > 0 else settings.unknown) 
        if move:
            shutil.rmtree(settings.snapshot_dir)
            data_utils.set_dirs([settings.snapshot_dir])
    else:
        print("Info: no faces were detected")
    return compare_results


def get_persons(compare_results):
    if len(compare_results) == 0:
        return []

    persons = []
    probable_persons = defaultdict(int)
    for compare_result in compare_results:
        total_matches = len(compare_result)
        if total_matches > 0:
            (name, occurences) = Counter(compare_result).most_common(1)[0]
            if occurences >= total_matches * CONFIDENCE_LOCAL:
                probable_persons[name] += 1
    for name, occurences in probable_persons.iteritems():
        if occurences >= len(compare_results) * CONFIDENCE_OVERALL:
            persons.append(name)

    if len(persons) > 0:
        print("Info: {0} recognized".format(", ".join(persons)))
        return persons
    else:
        print("Info: a person wasn't recognized")
        return ["stranger"]


def get_data_stream(old_action_time, token, camera_id, url=settings.nest_api_url):
    
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    headers = {
        'Authorization': "Bearer {0}".format(token),
        'Accept': 'text/event-stream'
    }
    http = urllib3.PoolManager()
    response = http.request('GET', url, headers=headers, preload_content=False)
    client = sseclient.SSEClient(response)
    
    for event in client.events(): # returns a generator
        event_type = event.event
        print "event: ", event_type
        if event_type == 'open': # not always received here
            print "The event stream has been opened"
        elif event_type == 'put':
            print "The data has changed (or initial data sent)"
            dict_json = json.loads(event.data)
            data = dict_json.get("data")
            last_event = data["devices"]["cameras"][camera_id]["last_event"]
            new_action_time = last_event["start_time"]
            if old_action_time != new_action_time:
                yield last_event
        elif event_type == 'keep-alive':
            print "No data updates. Receiving an HTTP header to keep the connection open."
        elif event_type == 'auth_revoked':
            print "The API authorization has been revoked."
        elif event_type == 'error':
            print "Error occurred, such as connection closed."
            print "error message: ", event.data
        else:
            print "Unknown event, no handler for it."


# TODO: get images from HQ stream
# TODO: send a killer signal to get_data_stream
def make_action(token, camera_id, known_faces, file_names):
    try:
        old_action_time = nest_lib.get_action_time(token, camera_id)
    except:
        print("Info: No prior action stored, resetting to empty")
    old_action_time = ""
    last_event_data = {"start_time": old_action_time, "has_person": False}
    is_streamimg = False
    remove = True
    print("Info: camera is ready")
    # TODO: make this async
    while True:
        key = 0
        while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.read(1)
            if not key:
                exit(0)

        if key == 'q':
            print("Info: quitting...")
            return
        
        elif key == 'c':
            print("Info: streaming turned on")
            is_streamimg = True
            action_gen = get_data_stream(old_action_time, token, camera_id)
            last_event_data = action_gen.next()

        elif key == 'd':
            print("Info: streaming turned off")
            is_streamimg = False

        elif key == 'e':
            remove = not remove
            print("Info: remove is {0}".format("on" if remove else "off"))

        elif key == 'l':
            file_names = []
            known_faces = get_faces(file_names=file_names, remove=False)

        elif key == 'r' or key == 's':
            img_url = nest_lib.get_data(token, nest_lib.get_snapshot_url(camera_id))["results"]
            data_utils.record_data(img_url, "jpg")
            if key == 'r':
                print(recognize_faces(known_faces, file_names, remove=remove))

        elif key == 'a' or key == 'm' or key == 't':
            last_event_data = nest_lib.get_data(token, nest_lib.get_action_url(camera_id))["results"]
            if key == 't' or (last_event_data["has_person"] and last_event_data["start_time"] != old_action_time):
                print("Info: someone detected")
                data_utils.record_data(last_event_data["animated_image_url"], "gif")
                if key != 't':
                    old_action_time = last_event_data["start_time"]
                if key == 'a':
                    compare_results = recognize_faces(known_faces, file_names, remove=remove)
                    persons = get_persons(compare_results)
                    interaction.interact(persons)
            else:
                print("Info: no new action or person detected")
        

        elif is_streamimg and last_event_data["has_person"] and last_event_data["start_time"] != old_action_time:
            print("Info: someone detected")
            data_utils.record_data(last_event_data["animated_image_url"], "gif")
            compare_results = recognize_faces(known_faces, file_names, remove=remove)
            persons = get_persons(compare_results)
            interaction.interact(persons)
            old_action_time = last_event_data["start_time"]
            action_gen = get_data_stream(old_action_time, token, camera_id)
            last_event_data = action_gen.next()


print("Info: started")
token = data_utils.get_token()
print("Info: got token")
data_utils.set_dirs([settings.snapshot_dir, settings.known_faces_dir, settings.results_dir, settings.interactions_dir])
print("Info: dirs setup")
camera_id = nest_lib.get_camera_id(token)
print("Info: got camera id")
file_names = []
known_faces = get_faces(file_names=file_names, remove=False)
make_action(token, camera_id, known_faces, file_names)
print("Info: finished")
