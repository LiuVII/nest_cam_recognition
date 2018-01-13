from collections import namedtuple
import time
import asyncio
import aioconsole
from concurrent.futures import FIRST_COMPLETED
from random import randint

start = time.time()
DEFAULT_FPS = 1.0
FRAME_PROCESS_SPEED = 2.5


def tic():
    return 'at %1.2f seconds' % (time.time() - start)


async def read_from_stream(frame_num=0, fps=DEFAULT_FPS):
    print('Reading form stream {} | {}'.format(frame_num, tic()))
    await asyncio.sleep(1.0/fps)
    return {"frame": frame_num}


async def read_from_input():
    command = await aioconsole.ainput('Entrer your command: ')
    return {"input": command}


async def process_stream_data(frame_num, tasks):
    print("Processing frame {} | {}".format(frame_num, tic()))
    await asyncio.gather(*[asyncio.sleep(task) for task in tasks])
    print('Frame {} finished | {}'.format(frame_num, tic()))
    return {"data": frame_num}


async def interaction_(result_num):
    print("Interacting on result {} | {}".format(result_num, tic()))
    await asyncio.sleep(1)
    print('Interaction {} finished | {}'.format(result_num, tic()))


def parse_result(result, futures, params):
    if "frame" in result:
        if params["process"]:
            futures.append(process_stream_data(result["frame"], params["tasks_time"]))
    elif "input" in result:
        command = result["input"]
        print("Command: {}".format(command))
        if command == "quit":
            for future in futures:
                future.cancel()
        else:
            if command == "stream":
                params["stream"] = not params["stream"]
                print("Info: streaming is {}".format("on" if params["stream"] else "off"))
            elif command == "process":
                params["process"] = not params["process"]
                print("Info: frame processing is {}".format("on" if params["process"] else "off"))
            elif command.split() > 1 and command.split()[0] == "fps":
                fps = int(command.split()[1])
                if fps > 0:
                    params["fps"] = fps
                    print("Info: stream fps set to {}".format(fps))
                else:
                    print("Warning: fps cannot be set to zero")
            else:
                print("Warning: command not recognized")
            futures.append(read_from_input())


def init_params():
    return {
        "stream": False,
        "process": False,
        "frame_num": 0,
        "data_frame": 0,
        "fps": DEFAULT_FPS,
        "tasks_time": [1 for _ in range(8)]
    }


async def asynchronous():
    params = init_params()
    futures = [read_from_input()]
    while futures:
        print("Loop")
        if params["stream"]:
            futures.append(read_from_stream(frame_num=params["frame_num"], fps=params["fps"]))
            params["frame_num"] += 1
        done, pending = await asyncio.wait(futures, return_when=FIRST_COMPLETED)
        pending = list(pending)
        parse_result(done.pop().result(), pending, params)
        futures = pending
    print("done")


ioloop = asyncio.get_event_loop()
ioloop.run_until_complete(asynchronous())
ioloop.close()

