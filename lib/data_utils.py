
import json
import os
import shutil
import time
from datetime import datetime
from PIL import Image
from io import BytesIO
from requests import get

import nest_lib
import settings


def get_token():
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
        return json_data["token"]


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
    try:
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
    except:
        print("Error: unknown in record_data")