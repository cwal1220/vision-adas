import os.path
import traceback
from datetime import datetime

import numpy as np

from calibration.openpilot_calib import Calibrator
from model.openpilot_model import VisionModel
import research.lane_change as lc

import cv2

from image.camera_source import CameraSource
from image.image_sink import ImageSink

# open up our test file we can set this to be a webcam or video


cap = CameraSource(cam_id=0, save_video=True)
output_sink = ImageSink(fps=20, sink_name='Model Output')

# open up traffic output file for appending new data.
out_traffic = open('traffic_output.txt', "a+")

# Set this to true when conducting field experiment. It will enable lane change algorithm and GPS
field_experiment = False

# Instantiate an instance of the OpenPilot vision model
cam_calib_file = 'calibration.json' if os.path.exists('calibration.json') else None

cam_calib = Calibrator(calib_file=cam_calib_file)
vision_model = VisionModel(using_wide=False, show_vis=True, use_model_speed=not field_experiment, cam_calib=cam_calib)

ts = np.array([[1.42070485, 0.0, -30.16740088],
               [0.0, 1.42070485, 91.030837],
               [0.0, 0.0, 1.0]])

pos_lat = 0
pos_lon = 0


def log_traffic_info(lead_x, lead_y, lead_d, veh_speed):
    global pos_lat
    global pos_lon
    """
    Logs surrounding traffic info to traffic_output.txt.
    :param lead_x: Distance of lead horizontal offset from image in image.
    :param lead_y: Distance of lead vertical offset from image in image.
    :param lead_d: Distance of lead from image in metres
    :param veh_speed: Vehicle speed in m/s
    :return: None
    """
    date_time = datetime.now()

    info = "Date: " + str(date_time) + ", Type: Lead Vehicle" + ", Distance x: " + str(lead_x) + ", Distance y: " + \
           str(lead_y) + ", Distance_t: " + str(lead_d) + " m " + ", Vehicle Speed: " + str(veh_speed * 3.6)

    if field_experiment:
        info = info + ', lat:' + str(pos_lat)
        info = info + ', lon: ' + str(pos_lon)

    info = info + '\n'

    out_traffic.write(info)


def res_frame_2(frame):
    """
    Resizes frame to 1164 x 874 to match eon image frame.
    :param frame: RGB image (numpy array)
    :return: resized image (numpy array)
    """
    return cv2.resize(frame, (1164, 874), interpolation=cv2.INTER_NEAREST)


def res_frame(frame):
    """
    Resizes frame to 1164 x 874 to match eon image frame. (Zooms into frame)
    :param frame: RGB image (numpy array)
    :return: resized image (numpy array)
    """
    frame1_shape = frame.shape

    if frame1_shape[0] != 874 and frame1_shape[1] != 1168:  # check if we have to correct size
        if frame1_shape[0] >= 874 and frame1_shape[1] >= 1168:  # check if image has enough width

            crop_vertical = (frame1_shape[0] - 874) // 2  # crop equally horizontally and vertically
            crop_horizontal = (frame1_shape[1] - 1164) // 2

            return frame[crop_vertical:frame1_shape[0] - crop_vertical,  # return cropped image
                   crop_horizontal:frame1_shape[1] - crop_horizontal]
        else:
            raise Exception("This image source cannot be used for model!")

    return frame  # if image was correct size to begin with, just return it


def setup_image_stream():
    """
    Sets up video source streaming properties such as resolution and exposure
    :return: None
    """
    cap.set_parameter(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set_parameter(cv2.CAP_PROP_FRAME_HEIGHT, 720)


def get_frames():
    """
    Returns appropriate frames for openpilot model input from defined image source.
    :return: Tuple of 2 frames (frame_1, frame_2) for input into openpilot model (numpy array)
    """

    ret1, frame_1 = cap.get_frame()
    ret2, frame_2 = cap.get_frame()

    if not (ret1 or ret2):
        raise Exception("Error reading from image source")

    # frame_1 = res_frame(frame_1)  # resize frames
    # frame_2 = res_frame(frame_2)

    return frame_1, frame_2


def process_model(frame1, frame2):
    global pos_lat
    global pos_lon
    """
    Runs input frames through the openpilot model and extracts outputs from it
    :param frame1: First frame (numpy array)
    :param frame2: Second frame (numpy array)
    :return: None
    """
    global field_experiment

    # Run model
    lead_x, lead_y, lead_d, pose_speed, vis_image = vision_model.run_model(frame1, frame2)

    # Log relevant info
    log_traffic_info(lead_x, lead_y, lead_d, pose_speed)

    output_sink.sink_frame(vis_image)

    # Run lane change algo if doing field experiment
    if field_experiment:
        pos_lat = lc.get_last_lat()
        pos_lon = lc.get_last_lon()
        lc.lane_change_algo(b_dist=lead_d)
        vision_model.vehicle_speed = lc.get_last_speed()


def delete_invalid_files():
    directory = os.fsencode('Videos/')

    for file in os.listdir(directory):
        filename = os.fsdecode(file)

        if filename.endswith('.mp4'):
            fsize = os.path.getsize(os.path.join('Videos', filename))

            if fsize < 1000:
                try:
                    os.remove(os.path.join('Videos', filename))
                except PermissionError as pe:
                    print('Could not remove file ', filename, ' due to permission error')


if __name__ == "__main__":

    # setup_image_stream()

    try:
        # Run the pipelines as long as we have data
        while True:
            frame1, frame2 = get_frames()
            process_model(frame1, frame2)
    except BaseException as e:
        print('An exception occurred: {}'.format(e))
        traceback.print_exc()
    finally:
        cap.flush_unsaved_video()
        output_sink.flush_unsaved_video()
        delete_invalid_files()
