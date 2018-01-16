import cv2
import numpy
import subprocess as sp

import settings

ESC_CODE = settings.esc_code
FFMPEG_BIN = settings.ffmpeg_bin
# TODO(mf): Determine size and color by getting stream info
FRAME_C = 3
FRAME_X = 1280
FRAME_Y = 720
FRAME_SIZE = FRAME_X * FRAME_Y * FRAME_C
VIDEO_URL = settings.video_url
WINDOW_NAME = settings.window_name


async def stream_open(fps):
    cv2.namedWindow(WINDOW_NAME)

    stream_pipe = sp.Popen([FFMPEG_BIN, "-i", VIDEO_URL,
               "-loglevel", "quiet", # no text output
               "-an",   # disable audio
               "-f", "image2pipe",
               "-vf", "fps={}".format(fps),
               "-pix_fmt", "bgr24",
               "-vcodec", "rawvideo", "-"],
               stdin = sp.PIPE, stdout = sp.PIPE)
    return {"stream_pipe": stream_pipe}


def stream_close(params):
    pipe = params["stream_pipe"]
    if pipe:
        pipe.kill()
    params["stream_pipe"] = None
    cv2.destroyAllWindows()


# TODO(mf): maybe wait for a command to read next frame
# TODO(mf): check that video delay is stable
async def stream_read(params):
    pipe = params["stream_pipe"]
    if not pipe:
        println("Warning: stream pipe isn't set")
        return {"warning": "stream pipe isn't set"}
    
    try:
        # TODO(mf): communicate doesn't work here, figure out why:
        raw_image = pipe.stdout.read(FRAME_SIZE)
        # raw_image, err = pipe.communicate()
        # if (err):
        #   print("Error: stream error {}".format(err))
        #   return {"error": "read from stream"}
        image = numpy.fromstring(raw_image, dtype='uint8').reshape((FRAME_Y, FRAME_X, FRAME_C))
        cv2.imshow(WINDOW_NAME, image)
        # TODO(mf): waitKey sometimes interrupts keyboard input which stops whole app, bypass it
        cv2.waitKey(1)
        return {"frame": image}
    
    except:
        print("Error: unknown error from stream_read")
        return {"error": "unknown error from stream_read"}
