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
import subprocess as sp
import numpy
import cv2
import time

from lib import nest_lib
from lib import data_utils
import settings
import interaction


WINDOW_NAME = "SigmaSpy"
FFMPEG_BIN = "ffmpeg"
FRAME_X = 1280
FRAME_Y = 720
FRAME_C = 3
FRAME_SIZE = FRAME_X * FRAME_Y * FRAME_C
ESC_CODE = 27

CONFIDENCE_OVERALL = 0.3
CONFIDENCE_LOCAL = 0.5


def get_faces(faces_dir=settings.known_faces_dir, file_names=[], remove=True):
    valid_img_types = [".jpg",".gif",".png"]
    faces = []

    for img_type in valid_img_types:
        for img_file in glob.glob('{0}/*{1}'.format(faces_dir, img_type)):
            try:
                img = face_recognition.load_image_file(img_file)
                img_encoded = face_recognition.face_encodings(img)
                file_names += [img_file] * len(img_encoded)
                if len(img_encoded) > 1:
                    print("Info: file {0} contains {1} faces".format(img_file, len(img_encoded)))
                elif len(img_encoded) == 0 and remove:
                    os.remove(img_file)
                faces += img_encoded
            except:
                print("Error: failed to open and recognize single image")

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


def capture_video_stream(new_event, old_event):
    cv2.namedWindow(WINDOW_NAME)

    pipe = sp.Popen([FFMPEG_BIN, "-i", VIDEO_URL,
               "-loglevel", "quiet", # no text output
               "-an",   # disable audio
               "-f", "image2pipe",
               "-pix_fmt", "bgr24",
               "-vcodec", "rawvideo", "-"],
               stdin = sp.PIPE, stdout = sp.PIPE)
    while True:
        raw_image = pipe.stdout.read(FRAME_SIZE)
        image =  numpy.fromstring(raw_image, dtype='uint8').reshape((FRAME_Y, FRAME_X, FRAME_C))
        cv2.imshow(WINDOW_NAME, image)
        if cv2.waitKey(5) == ESC_CODE:
            break
        # time.sleep( 1.0 / FPS)
    cv2.destroyAllWindows()


def copy_events(new_event, old_event):
    for key in new_event.keys():
        old_event[key] = new_event[key]
    return old_event


def get_data_from_event(event_data):
    return {"start_time": event_data["start_time"],
        "has_person": event_data["has_person"],
        "animated_image_url": event_data["animated_image_url"],
        "image_url": event_data["image_url"],
        "face_detected": False}


def get_event_client(url=settings.nest_api_url):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    headers = {
        'Authorization': "Bearer {0}".format(token),
        'Accept': 'text/event-stream'
    }
    http = urllib3.PoolManager()
    response = http.request('GET', url, headers=headers, preload_content=False)
    client = sseclient.SSEClient(response)
    return client


def get_data_stream(old_event, token, camera_id, client):
    for event in client.events(): # returns a generator
        event_type = event.event
        print "event: ", event_type

        if event_type == 'open': # not always received here
            print "The event stream has been opened"

        elif event_type == 'put':
            print "The data has changed (or initial data sent)"
            data = json.loads(event.data).get("data")
            event_data = data["devices"]["cameras"][camera_id]["last_event"]
            new_event = get_data_from_event(event_data)
            if new_event["start_time"] != old_event["start_time"]:
                print "New event happened", new_event["start_time"]
                new_event_happened = True
            else:
                new_event_happened = False
            need_to_detect_face = not old_event["face_detected"] and\
                new_event["animated_image_url"] != old_event["animated_image_url"] and\
                new_event["image_url"] != old_event["image_url"]
            if need_to_detect_face or new_event_happened:
                yield new_event

        elif event_type == 'keep-alive':
            print "No data updates. Receiving an HTTP header to keep the connection open."

        elif event_type == 'auth_revoked':
            print "The API authorization has been revoked."

        elif event_type == 'error':
            print "Error occurred, such as connection closed."
            print "error message: ", event.data

        else:
            print "Unknown event, no handler for it."


# TODO: send a killer signal to get_data_stream
def make_action(token, camera_id, known_faces, file_names):
    is_streamimg = False
    remove = True
    is_recognizing = True
    old_event = {}
    action_url = nest_lib.get_action_url(camera_id)
    snapshot_url = nest_lib.get_snapshot_url(camera_id)
    try:
        event_data = nest_lib.get_data(token, action_url)["results"]
        new_event = get_data_from_event(event_data)
    except:
        print("Info: No prior action stored, resetting to empty")
        new_event = {"start_time": False, "has_person": False, "animated_image_url": "", "image_url": ""}
    new_event["face_detected"] = True
    copy_events(new_event, old_event)
    client = ""
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
            if not is_streamimg:
                print("Info: streaming turned on")
                is_streamimg = True
                client = get_event_client()
                action_gen = get_data_stream(old_event, token, camera_id, client)
                new_event = action_gen.next()
            else:
                print("Info: streaming turned off")
                is_streamimg = False
                client = ""

        elif key == 'r':
            is_recognizing = not is_recognizing
            print("Info: recognition is {0}".format("on" if is_recognizing else "off"))

        elif key == 'd':
            remove = not remove
            print("Info: remove is {0}".format("on" if remove else "off"))

        elif key == 'k':
            file_names = []
            known_faces = get_faces(file_names=file_names, remove=False)

        elif key == 's':
            img_url = nest_lib.get_data(token, snapshot_url)["results"]
            data_utils.record_data(img_url, "jpg")
            if is_recognizing:
                compare_results = recognize_faces(known_faces, file_names, remove=remove)
                persons = get_persons(compare_results)
                interaction.interact(persons)

        elif key == 'a':
            new_event = get_data_from_event(nest_lib.get_data(token, action_url)["results"])
            if (new_event["has_person"] and new_event["animated_image_url"] != old_event["animated_image_url"]):
                print("Info: someone detected")
                data_utils.record_data(new_event["image_url"], "jpg")
                data_utils.record_data(new_event["animated_image_url"], "gif")
                if is_recognizing:
                    compare_results = recognize_faces(known_faces, file_names, remove=remove)
                    new_event["face_detected"] = len(compare_results) > 0
                    persons = get_persons(compare_results)
                    interaction.interact(persons)
                copy_events(new_event, old_event)
            else:
                print("Info: no new action or person detected")

        elif is_streamimg and new_event["has_person"]:
            animated_changed = new_event["animated_image_url"] != old_event["animated_image_url"]
            static_changed = new_event["image_url"] != old_event["image_url"]
            if animated_changed and static_changed:
                print("Info: someone detected")
                if animated_changed:
                    data_utils.record_data(new_event["animated_image_url"], "gif")
                if static_changed:
                    data_utils.record_data(new_event["image_url"], "jpg")
                if is_recognizing:
                    compare_results = recognize_faces(known_faces, file_names, remove=remove)
                    new_event["face_detected"] = len(compare_results) > 0
                    persons = get_persons(compare_results)
                    interaction.interact(persons)
                copy_events(new_event, old_event)
                action_gen = get_data_stream(old_event, token, camera_id, client)
                new_event = action_gen.next()


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
