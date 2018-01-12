#!/usr/bin/env python3
"""
Continuously capture images from a webcam and write to a Redis store.
Usage:
   python recorder.py path2video
"""
import os
import io
import sys
import time
import datetime
import coils
import cv2
import numpy as np
import redis
from mvnc import mvncapi as mvnc
import dlib

dim=(224,224)
# ***************************************************************
# defines for opencv
# ***************************************************************
cascPath = 'haarcascade_frontalface_default.xml'
faceCascade = cv2.CascadeClassifier(cascPath)
eyePath = 'haarcascade_eye.xml'
eye_cascade = cv2.CascadeClassifier(eyePath)
# ***************************************************************
# defines for dlib
# ***************************************************************
detector = dlib.get_frontal_face_detector()

def opencv_detection(gray):
    faces = []
    face_locations = faceCascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30),
        flags=cv2.CASCADE_SCALE_IMAGE
    )
    for (x, y, w, h) in face_locations:
        roi_gray = gray[y:y + h, x:x + w]
        eyes = eye_cascade.detectMultiScale(roi_gray)
        if len(eyes) == 0:
            print("eyes not found")
            continue
        faces.append((x, y, x + w, y +h))
    return faces

def dlib_detection(image):
    faces = []
    dets = detector(image, 1)
    for i, d in enumerate(dets):
        faces.append((d.left(), d.top(), d.right(), d.bottom()))
    return faces

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
avg = None
lastUploaded = datetime.datetime.now()
motionCounter = 0
def main(video_uri):
    global  max_sleep, cur_sleep, avg,lastUploaded
    while True:
        cap = cv2.VideoCapture(video_uri)
        if cap.isOpened():
            break
        print('not opened, sleeping {}s'.format(cur_sleep))
        time.sleep(cur_sleep)
        if cur_sleep < max_sleep:
            cur_sleep *= 2
            cur_sleep = min(cur_sleep, max_sleep)
            continue
        cur_sleep = 0.1
    #cap.set(cv2.CAP_PROP_FRAME_COUNT, 3)
    #cap.release()
    # Create client to the Redis store.
    store = redis.Redis()

    # Monitor the framerate at 1s, 5s, 10s intervals.
    fps = coils.RateTicker((1, 5, 10))

    # encode, serialize and push to Redis database.
    # Then create unique ID, and push to database as well.
    while True:
        text = "Unoccupied"
        ticks = time.time()
        timestamp = datetime.datetime.now()
        ret, image = cap.read()
        if image is None:
            print('image is none')
            time.sleep(0.1)
            continue
        #cap.release()
        ticks1 = time.time()
        small_frame = cv2.resize(image, (0, 0), fx=0.5, fy=0.5)
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.GaussianBlur(gray, (21, 21), 0)
        # if the average frame is None, initialize it
        if avg is None:
            print("[INFO] starting background model...")
            avg = gray2.copy().astype("float")
            continue
        # accumulate the weighted average between the current frame and
        # previous frames, then compute the difference between the current
        # frame and running average
        cv2.accumulateWeighted(gray2, avg, 0.5)
        frameDelta = cv2.absdiff(gray2, cv2.convertScaleAbs(avg))

        # threshold the delta image, dilate the thresholded image to fill
        # in holes, then find contours on thresholded image
        thresh = cv2.threshold(frameDelta, 5, 255,
                               cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        _, cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # loop over the contours
        for c in cnts:
            # if the contour is too small, ignore it
            if cv2.contourArea(c) < 5000:
                continue

            # compute the bounding box for the contour, draw it on the frame,
            # and update the text
            (x, y, w, h) = cv2.boundingRect(c)
            cv2.rectangle(image, (x*2, y*2), ((x + w)*2, (y + h)*2), (255, 0, 0), 2)
            text = "Occupied"
        if text == "Occupied":
            # check to see if enough time has passed between uploads
            if (timestamp - lastUploaded).seconds >= 2.0:
                # increment the motion counter
                motionCounter += 1
                # check to see if the number of frames with consistent motion is
                # high enough
                if motionCounter >= 5:
                    lastUploaded = timestamp
                    motionCounter = 0
                    #face_locations = opencv_detection(gray)
                    face_locations = dlib_detection(small_frame)
                    if len(face_locations) == 0:
                        print("no face detected at all")
                    # Draw a rectangle around the faces
                    for (left, top, right, bottom) in face_locations:
                        font = cv2.FONT_HERSHEY_DUPLEX
                        cv2.putText(image, 'face', (left * 2 + 6, top * 2 - 6), font, 0.5, (0, 255, 0), 1)
                        cv2.rectangle(image, (left * 2, top * 2), (right * 2, bottom * 2), (0, 255, 0), 2)
                        ticks2 = time.time()
                        print("detection {} faces takes {} s".format(len(face_locations), ticks2 - ticks1))
                        img = image[top * 2:bottom * 2, left * 2:right * 2]
                        # cv2.imwrite("{}{}.jpg".format('/home/fengping/Pictures/faces/', time.strftime("%Y%m%d%H%M%S", time.localtime())), img)
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
                        cv2.rectangle(image, (left * 2, top * 2), (right * 2, bottom * 2), (255, 0, 0), 2)
                        font = cv2.FONT_HERSHEY_DUPLEX
                        cv2.putText(image, labels[order[0]], (left * 2 + 6, top * 2 - 6),
                                    font, 0.5, (255, 0, 0), 1)
                        path = timestamp.strftime("%b-%d_%H_%M_%S" + ".jpg")
                        cv2.imwrite(path, image)
        # otherwise, the room is not occupied
        else:
            motionCounter = 0
        hello, image = cv2.imencode('.jpg', image)
        sio = io.BytesIO()
        sio.write(image)
        value = sio.getvalue()
        store.set('image', value)
        image_id = os.urandom(4)
        store.set('image_id', image_id)

        # Print the framerate.
        #text = '{:.2f}, {:.2f}, {:.2f} fps'.format(*fps.tick())
        #print(text)
    cap.relsese()

if  __name__ == '__main__':
    main(sys.argv[1])
    graph.DeallocateGraph()