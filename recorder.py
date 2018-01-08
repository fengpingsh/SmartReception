#!/usr/bin/env python3
"""
Continuously capture images from a webcam and write to a Redis store.
Usage:
   python recorder.py [width] [height]
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
USE_FACE_RECOGNITION = 1
if USE_FACE_RECOGNITION:
    import face_recognition
    import dlib
else:
    cascPath = 'haarcascade_frontalface_default.xml'
    faceCascade = cv2.CascadeClassifier(cascPath)
    eyePath = 'haarcascade_eye.xml'
    eye_cascade = cv2.CascadeClassifier(eyePath)
process_frame= True
# Retrieve command line arguments.
width = None if len(sys.argv) <= 1 else int(sys.argv[1])
height = None if len(sys.argv) <= 2 else int(sys.argv[2])

# Create video capture object, retrying until successful.
max_sleep = 5.0
cur_sleep = 0.1
while True:
    cap = cv2.VideoCapture(-1)
    if cap.isOpened():
        break
    print('not opened, sleeping {}s'.format(cur_sleep))
    time.sleep(cur_sleep)
    if cur_sleep < max_sleep:
        cur_sleep *= 2
        cur_sleep = min(cur_sleep, max_sleep)
        continue
    cur_sleep = 0.1

# Create client to the Redis store.
store = redis.Redis()

# Set video dimensions, if given.
if width: cap.set(3, width)
if height: cap.set(4, height)

# Monitor the framerate at 1s, 5s, 10s intervals.
fps = coils.RateTicker((1, 5, 10))

class myFaceDetectionThread (threading.Thread):
    def __init__(self, image, zoom):
        threading.Thread.__init__(self)
        self.image = image
        self.zoom = zoom
    def run(self):
        print("Start...")
        face_locations = face_recognition.face_locations(self.image)
        print("{} faces detected".format(len(face_locations)))
        # Provide the tracker the initial position of the object
        if len(face_locations) != Tracking.tracking_num():
            # retrack
            print("tracking_reset")
            Tracking.tracking_reset()
            Tracking.start(self.image, face_locations, 1)
        else:
            print("keep tracking")
        for i, (top, right, bottom, left) in enumerate(face_locations):
            # Draw a box around the face
            top *= self.zoom
            right *= self.zoom
            bottom *= self.zoom
            left *= self.zoom
            face_image = self.image[top:bottom, left:right]

            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(self.image, 'face', (left + 6, top - 6), font, 0.5, (0, 0, 255), 1)
            cv2.rectangle(self.image, (left, top), (right, bottom), (0, 0, 255), 2)
        print("Exit")
        return face_locations

class Track:
    def __init__(self):
        print("Track init called")
        self.obj = dlib.correlation_tracker()
        self.name = 'idle'

    def tracked(self, name):
        self.name = name

class TrackSet:
    tracker = dict.fromkeys(range(4))
    def __init__(self):
        for i in range(len(TrackSet.tracker)):
            TrackSet.tracker[i] = Track()
    def tracking_num(self):
        num = 0
        for key, values in TrackSet.tracker.items():
            if values.name != 'idle':
                num += 1
        return num

    def tracking_reset(self):
        for i in range(len(TrackSet.tracker)):
            TrackSet.tracker[i] = Track()
    def capability(self):
        return len(TrackSet.tracker)
    def start(self, frame, face_locations,zoom):
        for i, (top, right, bottom, left) in enumerate(face_locations):
            top *= zoom
            right *= zoom
            bottom *= zoom
            left *= zoom
            print("start track on {},{},{},{}".format(left, top, right, bottom))
            Tracking.tracker[i].obj.start_track(frame, dlib.rectangle(left, top, right, bottom))
            TrackSet.tracker[i].name = 'unknown'
    def update(self, frame):
        #print("Tracking.capability() = {}".format(Tracking.capability()))
        for i in range(Tracking.capability()):
            if Tracking.tracker[i].obj == None or TrackSet.tracker[i].name == 'idle':
                continue
            ret = Tracking.tracker[i].obj.update(frame)
            print("tracking {} return {}".format(i, ret))
            rect = Tracking.tracker[i].obj.get_position()
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, Tracking.tracker[i].name, (int(rect.left()) + 6, int(rect.top()) - 6), font, 0.5, (255, 0, 0), 1)
            cv2.rectangle(frame, (int(rect.left()), int(rect.top())), (int(rect.right()), int(rect.bottom())), (255, 0, 0),
                          2)
        return frame
    # Repeatedly capture current image,
# encode, serialize and push to Redis database.
# Then create unique ID, and push to database as well.
frame_idx = -1
Tracking = TrackSet()
while True:
    hello, image = cap.read()
    if image is None:
        time.sleep(0.5)
        continue
    frame_idx +=1
    image = cv2.flip(image, 0)
    small_frame = image#cv2.resize(image, (0, 0), fx=0.5, fy=0.5)
    #process_frame = not process_frame
    if USE_FACE_RECOGNITION and process_frame:
        if frame_idx % 30 == 0:
            # invoke face detection
            mythread = myFaceDetectionThread(small_frame, 1)
            mythread.start()
        else:
            #update
            image = Tracking.update(small_frame)
    elif process_frame:
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        face_locations = faceCascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        # Draw a rectangle around the faces
        for (x, y, w, h) in face_locations:
            roi_gray = gray[y:y + h, x:x + w]
            roi_color = small_frame[y:y + h, x:x + w]
            eyes = eye_cascade.detectMultiScale(roi_gray)
            if len(eyes) == 0:
                break
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(image, 'face', (x*2 + 6, y*2 - 6), font, 0.5, (0, 255, 0), 1)
            cv2.rectangle(image, (x * 2, y * 2), ((x + w) * 2, (y + h) * 2), (0, 255, 0), 2)

    hello, image = cv2.imencode('.jpg', image)
    #sio = StringIO.StringIO()
    #np.save(sio, image)
    sio = io.BytesIO()
    sio.write(image)
    value = sio.getvalue()
    store.set('image', value)
    image_id = os.urandom(4)
    store.set('image_id', image_id)
    
    # Print the framerate.
    text = '{:.2f}, {:.2f}, {:.2f} fps'.format(*fps.tick())
    #print(text)
