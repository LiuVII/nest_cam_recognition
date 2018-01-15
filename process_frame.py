from collections import Counter, defaultdict
import asyncio
import face_recognition
import glob
import os
import shutil

from lib import data_utils
import settings

CONFIDENCE_OVERALL = 0.3
CONFIDENCE_LOCAL = 0.5


async def process_frame(frame, params):
    # TODO(mf): use frame directly saving here should be async and mostly for debug purposes
    await data_utils.save_file_to_disk(frame, "jpg")
    compare_futures = [recognize_faces([known_face], file_names, remove=remove) for known_face in known_faces]
    compare_results = await asyncio.gather(*compare_futures)
    flatten_results = [result for results in compare_results for result in results]
    persons = await get_persons(flatten_results)
    return {"process_result": persons}

async def get_faces(faces_dir=settings.known_faces_dir, file_names=[], remove=True):
    valid_img_types = [".jpg",".gif",".png"]
    faces = []

    for img_type in valid_img_types:
        for img_file in glob.glob('{}/*{}'.format(faces_dir, img_type)):
            try:
                img = face_recognition.load_image_file(img_file)
                img_encoded = face_recognition.face_encodings(img)
                file_names += [img_file] * len(img_encoded)
                if len(img_encoded) > 1:
                    print("Info: file {} contains {} faces".format(img_file, len(img_encoded)))
                elif len(img_encoded) == 0 and remove:
                    os.remove(img_file)
                faces += img_encoded
            except:
                print("Error: failed to open and recognize single image")

    print("Info: total number of faces in {}: {}".format(faces_dir, len(faces)))
    return faces


async def recognize_faces(known_faces, file_names, save_res=True, move=True, remove=True):
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


async def get_persons(compare_results):
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
        print("Info: {} recognized".format(", ".join(persons)))
        return persons
    else:
        print("Info: a person wasn't recognized")
        return ["stranger"]
