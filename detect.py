import cv2
import sys
import os
import io
import time
from multiprocessing import Queue
import threading
import json
import argparse
from mvnc import mvncapi as mvnc
import numpy
import dlib
import redis
# ***************************************************************
# Arguement parse
# ***************************************************************
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True,
	help="path to the JSON configuration file")
args = vars(ap.parse_args())
conf = json.load(open(args["conf"]))

# ***************************************************************
# Globals
# ***************************************************************
zoom_out = int(conf['resize'])
video_capture = cv2.VideoCapture(conf['url'])
debug = int(conf['debug'])
debug_path = '/tmp/'
t_start = time.time()
fps = int(conf['fps'])
labels_file=conf['label']
graph_file = conf['graph']
mean_file = conf['mean']
# ***************************************************************
# Defined for opencv face detection
# ***************************************************************
cascPath = 'haarcascade_frontalface_default.xml'
faceCascade = cv2.CascadeClassifier(cascPath)
eyePath = 'haarcascade_eye.xml'
eye_cascade = cv2.CascadeClassifier(eyePath)
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
        #roi_gray = gray[y:y + h, x:x + w]
        #eyes = eye_cascade.detectMultiScale(roi_gray)
        #if len(eyes) == 0:
        #    print("eyes not found")
        #    continue
        faces.append((x, y, x + w, y +h))
    return faces
# ***************************************************************
# Defined for dlib face detection
# ***************************************************************
detector = dlib.get_frontal_face_detector()
def dlib_detection(image):
    faces = []
    dets = detector(image, 1)
    for i, d in enumerate(dets):
        faces.append((d.left(), d.top(), d.right(), d.bottom()))
    return faces
# ***************************************************************
# Define for ncs recognition
# ***************************************************************
labels=numpy.loadtxt(labels_file,str,delimiter='\t')
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
network_blob=graph_file
#Load blob
with open(network_blob, mode='rb') as f:
    blob = f.read()

graph = device.AllocateGraph(blob)
#loading the mean file
ilsvrc_mean = numpy.load(mean_file).mean(1).mean(1)
# ***************************************************************
# For the running process
# ***************************************************************
exitFlag = 0
class myThread(threading.Thread):
    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self._store = redis.Redis()
        self._prev_image_id = None

    def run(self):
        print("Starting " + self.name)
        while not exitFlag:
            image_id = self._store.get('image_id').decode('utf-8')
            if image_id != self._prev_image_id:
                image = self._store.get('image')
                array_dtype, l, w, d = image_id.split('|')[1].split('#')
                image = numpy.fromstring(image, dtype=array_dtype).reshape(int(l), int(w), int(d))
                self._prev_image_id = image_id
                process_data(image_id, image)
        print("Exiting " + self.name)

def process_data(image_id, image):
    ticks = time.time()
    small_frame = cv2.resize(image, (0, 0), fx=1/zoom_out, fy=1/zoom_out)
    faces = dlib_detection(small_frame)
    for i, (left, top, right, bottom) in enumerate(faces):
        left *= zoom_out
        top *= zoom_out
        right *= zoom_out
        bottom *= zoom_out
        face_image = image[top:bottom, left:right]
        face_image = cv2.resize(face_image, (224, 224))
        face_image = face_image.astype(numpy.float32)
        face_image[:, :, 0] = (face_image[:, :, 0] - ilsvrc_mean[0])
        face_image[:, :, 1] = (face_image[:, :, 1] - ilsvrc_mean[1])
        face_image[:, :, 2] = (face_image[:, :, 2] - ilsvrc_mean[2])
        graph.LoadTensor(face_image.astype(numpy.float16), 'user object')
        output, userobj = graph.GetResult()
        order = output.argsort()[::-1][:3]
        print('\n------- predictions --------')
        for i in range(0, 3):
            print('prediction ' + str(i) + ' (probability ' + str(output[order[i]]) + ') is ' + labels[
                order[i]] + '  label index is: ' + str(order[i]))
        if output[order[0]] < 1.0:
            cv2.putText(image, 'unknown', (left + 6, top - 6), cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 255, 0),
                        1)
            cv2.rectangle(image, (left, top), (right, bottom), (0, 255, 0), 2)
        else:
            cv2.putText(image, labels[order[0]], (left + 6, top - 6), cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 255, 0), 1)
            cv2.rectangle(image, (left, top), (right, bottom), (0, 255, 0), 2)
    if debug and len(faces) > 0:
        cv2.imwrite(image_id + '_labeled.jpg', image)
    print("processing %s takes %f" % (image_id, time.time() - ticks))

thread = myThread(1, 'face detection and recognition')
thread.start()
# ***************************************************************
# Create client to the Redis store.
# ***************************************************************
store = redis.Redis()
index = 0
while True:
    # Capture frame-by-frame
    ret, frame = video_capture.read()
    if not ret:
        time.sleep(1)
        print('failed to read frame, restarting...')
        video_capture.release()
        video_capture = cv2.VideoCapture(conf['url'])
        index = 0
        continue
    if index % fps == 0:
        l, w, d = frame.shape
        array_dtype = str(frame.dtype)
        frame = frame.ravel().tostring()
        frame_id = '{0}|{1}#{2}#{3}#{4}'.format(index, array_dtype, l, w, d).encode('utf-8')
        store.mset({'image':frame, 'image_id':frame_id})
        print("write {} image".format(frame_id))
    index = index + 1
# When everything is done, release the capture
exitFlag = 1
graph.DeallocateGraph()
device.CloseDevice()
video_capture.release()

