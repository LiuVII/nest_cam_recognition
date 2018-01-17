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
VALID_IMG_TYPES = [".jpg", ".gif", ".png"]


async def process_frame(frame, params):
    # TODO(mf): use frame directly saving here should be async and mostly for debug purposes
    await data_utils.save_file_to_disk(frame, "jpg")
    compare_futures = [recognize_faces(
        [known_face], params["file_names"], remove=params["remove"]
    ) for known_face in params["known_faces"]]
    compare_results = await asyncio.gather(*compare_futures)
    flatten_results = [result for results in compare_results for result in results]
    persons = await get_persons(flatten_results)
    return {"process_result": persons}


async def get_face(image_file, remove):
    try:
        img = face_recognition.load_image_file(image_file)
        faces = face_recognition.face_encodings(img)

    # TODO(mf): make proper error handling
    except:
        print("Error: failed to open and recognize single image")
        faces = []

    file_names = [image_file] * len(faces)
    if len(faces) > 1:
        print("Info: file {} contains {} faces".format(image_file, len(faces)))
    elif len(faces) == 0 and remove:
        os.remove(image_file)
    return file_names, faces


async def get_faces(faces_dir=settings.known_faces_dir, remove=True):
    img_files = [file for img_type in VALID_IMG_TYPES for file in glob.glob('{}/*{}'.format(faces_dir, img_type))]
    get_faces_result = await asyncio.gather(*[get_face(img_file, remove) for img_file in img_files])
    file_names, faces = map(list, zip(*get_faces_result))
    print("Info: total number of faces in {}: {}".format(faces_dir, len(faces)))
    return faces, file_names


async def recognize_faces(known_faces, file_names, save_res=True, move=True, remove=True):
    if len(known_faces) == 0:
        print("Info: recognition isn't active due to zero known faces in folder")
        return []
    compare_results = []
    # TODO(mf): instead of simply awaiting run async for every unknown and gather futures
    unknown_faces, unknown_files = await get_faces(settings.snapshot_dir, remove)

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
            (name, occurrences) = Counter(compare_result).most_common(1)[0]
            if occurrences >= total_matches * CONFIDENCE_LOCAL:
                probable_persons[name] += 1
    for name, occurrences in probable_persons.items():
        if occurrences >= len(compare_results) * CONFIDENCE_OVERALL:
            persons.append(name)

    if len(persons) > 0:
        print("Info: {} recognized".format(", ".join(persons)))
        return persons
    else:
        print("Info: a person wasn't recognized")
        return ["stranger"]
