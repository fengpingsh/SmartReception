#!/usr/bin/env python3
"""
Continuously capture images from a webcam and write to a Redis store.
Usage:
   python recorder.py path2video [width] [height]
"""
import os
import io
import sys
import time
import coils
import cv2
import numpy as np
import redis
import threading
from PIL import Image
from PIL import ImageOps
from mvnc import mvncapi as mvnc
import dlib

detector = dlib.get_frontal_face_detector()
dim=(224,224)
# ***************************************************************
# configure the NCS
# ***************************************************************
mvnc.SetGlobalOption(mvnc.GlobalOption.LOG_LEVEL, 2)

# ***************************************************************
# Get a list of ALL the sticks that are plugged in
# ***************************************************************
devices = mvnc.EnumerateDevices()
if len(devices) == 0:
	print('No devices found')
	quit()

# ***************************************************************
# Pick the first stick to run the network
# ***************************************************************
device = mvnc.Device(devices[0])

# ***************************************************************
# Open the NCS
# ***************************************************************
device.OpenDevice()

network_blob='VGG6Net.graph'
#Load blob
with open(network_blob, mode='rb') as f:
	blob = f.read()

graph = device.AllocateGraph(blob)
# ***************************************************************
# get labels
# ***************************************************************
labels_file='labels.txt'
labels=np.loadtxt(labels_file,str,delimiter='\t')
# ***************************************************************
# Load the image
# ***************************************************************
ilsvrc_mean = np.load('mean.npy').mean(1).mean(1)

# Create video capture object, retrying until successful.
max_sleep = 5.0
cur_sleep = 0.1
def main(video_uri):
    global  max_sleep, cur_sleep
    while True:
        cap = cv2.VideoCapture('rtsp://admin:Baustem123@192.168.1.153:554/Streaming/Channels/101?transportmode=unicast&profile=Profile_1')
        if cap.isOpened():
            break
        print('not opened, sleeping {}s'.format(cur_sleep))
        time.sleep(cur_sleep)
        if cur_sleep < max_sleep:
            cur_sleep *= 2
            cur_sleep = min(cur_sleep, max_sleep)
            continue
        cur_sleep = 0.1
    cap.set(cv2.CAP_PROP_FRAME_COUNT, 3)
    # Create client to the Redis store.
    store = redis.Redis()
    width = None if len(sys.argv) <= 2 else int(sys.argv[2])
    height = None if len(sys.argv) <= 3 else int(sys.argv[3])
    # Set video dimensions, if given.
    if width: cap.set(3, width)
    if height: cap.set(4, height)

    # Monitor the framerate at 1s, 5s, 10s intervals.
    fps = coils.RateTicker((1, 5, 10))

    # encode, serialize and push to Redis database.
    # Then create unique ID, and push to database as well.
    while True:
        ticks = time.time()
        ret, image = cap.read()
        while time.time() - ticks < 3.0:
            ret, image = cap.read()
            if image is None:
                print('image is none')
                time.sleep(0.1)
                continue
        ticks1 = time.time()
        small_frame = cv2.resize(image, (0, 0), fx=0.5, fy=0.5)
        dets = detector(small_frame, 1)
        ticks2 = time.time()
        print("detection {} faces takes {} s".format(len(dets), ticks2 - ticks1))
        for i, d in enumerate(dets):
            img = image[d.top() *2:d.bottom()*2, d.left()*2:d.right()*2]
            cv2.imwrite("{}{}.jpg".format('/home/fengping/Pictures/faces/', time.strftime("%Y%m%d%H%M%S", time.localtime())), img)
            img = cv2.resize(img, dim)
            img = img.astype(np.float32)
            img[:, :, 0] = (img[:, :, 0] - ilsvrc_mean[0])
            img[:, :, 1] = (img[:, :, 1] - ilsvrc_mean[1])
            img[:, :, 2] = (img[:, :, 2] - ilsvrc_mean[2])
            ticks3 = time.time()
            # ***************************************************************
            # Send the image to the NCS
            # ***************************************************************
            graph.LoadTensor(img.astype(np.float16), 'user object')

            # ***************************************************************
            # Get the result from the NCS
            # ***************************************************************
            output, userobj = graph.GetResult()
            print("movidius calssfication cost {}".format(time.time() - ticks3))
            # ***************************************************************
            # Print the results of the inference form the NCS
            # ***************************************************************
            order = output.argsort()[::-1][:6]
            print('\n------- predictions --------')
            for i in range(0, 6):
                print('prediction ' + str(i) + ' (probability ' + str(output[order[i]]) + ') is ' + labels[
                    order[i]] + '  label index is: ' + str(order[i]))
            cv2.rectangle(image, (int(d.left()) * 2, int(d.top()) * 2), (int(d.right()) * 2, int(d.bottom()) * 2), (255, 0, 0), 2)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(image, labels[order[0]], (int(d.left()) * 2 + 6, int(d.top()) * 2 - 6),
                        font, 0.5, (255, 0, 0), 1)
        hello, image = cv2.imencode('.jpg', image)
        sio = io.BytesIO()
        sio.write(image)
        value = sio.getvalue()
        store.set('image', value)
        image_id = os.urandom(4)
        store.set('image_id', image_id)

        # Print the framerate.
        text = '{:.2f}, {:.2f}, {:.2f} fps'.format(*fps.tick())
        print(text)

if  __name__ == '__main__':
    main(None)