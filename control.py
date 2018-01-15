import aioconsole

import stream_capture


async def read_from_input():
    command = await aioconsole.ainput('Entrer your command: ')
    return {"input": command}


async def parse_command(command, params, futures):
    print("Command: {}".format(command))
    if command == "quit":
        for future in futures:
            future.cancel()
    else:
        if command == "stream":
            params["stream"] = not params["stream"]
            print("Info: streaming is {}".format("on" if params["stream"] else "off"))
            if params["stream"]:
                futures.append(stream_capture.stream_open(params["fps"]))
        elif command == "process":
            params["process"] = not params["process"]
            print("Info: frame processing is {}".format("on" if params["process"] else "off"))
        elif command == "remove":
            params["remove"] = not params["remove"]
            print("Info: removing processed frame is {}".format("on" if params["remove"] else "off"))
        elif command == "snapshot":
            # TODO(mf): take a snapshot
            # futures.append(snapshot(params))
            pass
        elif command.split() > 1 and command.split()[0] == "fps":
            fps = int(command.split()[1])
            if fps > 0:
                params["fps"] = fps
                print("Info: stream fps set to {}".format(fps))
            else:
                print("Warning: fps should be a positive number")
        else:
            print("Warning: command not recognized")
        futures.append(read_from_input())
    return {"info": "command completed"}
