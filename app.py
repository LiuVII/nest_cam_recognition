from concurrent.futures import FIRST_COMPLETED
import asyncio
import json
import sys
import time

from lib import data_utils
import control
import interaction
import process_frame
import settings
import stream_capture


async def parse_result(result, futures, params):
    if "frame" in result:
        if params["process"]:
            futures.append(process_frame.process_frame(result["frame"]))
    elif "input" in result:
        await control.parse_command(result["input"], params, futures)
    elif "stream_pipe" in result:
        params["stream_pipe"] = result["stream_pipe"]
    elif "info":
        print("Info: {}".format(result["info"]))
    elif "warning":
        print("Warning: {}".format(result["warning"]))
    elif "error":
        print("Error: {}".format(result["error"]))
    else:
        print("Info: some result recieved")



# TODO(mf): make a class instead of a dict
def init_params():
    return {
        "stream": False,
        "stream_pipe": None,
        "process": False,
        "remove": True,
        "frame_num": 0,
        "data_frame": 0,
        "fps": DEFAULT_FPS,
    }


async def main_loop():
    params = init_params()
    futures = [control.read_from_input()]
    while futures:
        print("Loop")
        if params["stream"] and params["stream_pipe"]:
            futures.append(stream_capture.read_from_stream(fps=params["fps"]))
            params["frame_num"] += 1
        done, pending = await asyncio.wait(futures, return_when=FIRST_COMPLETED)
        pending = list(pending)
        await parse_result(done.pop().result(), pending, params)
        futures = pending


print("Info: started")
data_utils.set_dirs([settings.snapshot_dir, settings.known_faces_dir, settings.results_dir, settings.interactions_dir])
print("Info: dirs setup")
file_names = []

# TODO(mf): make async
# TODO(mf): calculate face recognition sensitivity level
# known_faces = get_faces(file_names=file_names, remove=False)
# TODO(mf): calculate processing speed based on known faces and some face example
DEFAULT_FPS = 4

ioloop = asyncio.get_event_loop()
ioloop.run_until_complete(main_loop())
ioloop.close()
print("Info: finished")
