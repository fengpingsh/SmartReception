import cv2
import sys
import os
import time
from multiprocessing import Queue
import threading
from mvnc import mvncapi as mvnc
import numpy
import dlib
# ***************************************************************
# Defined for opencv face detection
# ***************************************************************
storagePath = '/home/fengping/Pictures/'
cascPath = 'haarcascade_frontalface_default.xml'
faceCascade = cv2.CascadeClassifier(cascPath)
eyePath = 'haarcascade_eye.xml'
eye_cascade = cv2.CascadeClassifier(eyePath)
detector = dlib.get_frontal_face_detector()
RESIZE = 4
video_capture = cv2.VideoCapture('rtsp://admin:Baustem123@192.168.1.153:554/Streaming/Channels/101?transportmode=unicast&profile=Profile_1')
facess = []
t_start = time.time()
fps = 0
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

def dlib_detection(image):
    faces = []
    dets = detector(image, 1)
    for i, d in enumerate(dets):
        faces.append((d.left(), d.top(), d.right(), d.bottom()))
    return faces
# ***************************************************************
# Define for ncs recognition
# ***************************************************************
exitFlag = 0
EXAMPLES_BASE_DIR='/home/fengping/Downloads/caffe/vggface/vgg12/'
# ***************************************************************
# get labels
# ***************************************************************
labels_file=EXAMPLES_BASE_DIR+'labels.txt'
labels=numpy.loadtxt(labels_file,str,delimiter='\t')

print(labels)
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
network_blob=EXAMPLES_BASE_DIR + 'graph'
#Load blob
with open(network_blob, mode='rb') as f:
	blob = f.read()

graph = device.AllocateGraph(blob)
#loading the mean file
ilsvrc_mean = numpy.load(EXAMPLES_BASE_DIR+'mean.npy').mean(1).mean(1)

class myThread(threading.Thread):
    def __init__(self, threadID, name, q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q

    def run(self):
        print("Starting " + self.name)
        process_data(self.name, self.q)
        print("Exiting " + self.name)

def process_data(threadName, q):
    while not exitFlag:
        queueLock.acquire()
        if not workQueue.empty():
            ticks = time.time()
            data = q.get()
            print("%s processing %s" % (threadName, data))
            frame = cv2.imread(data)
            txt = os.path.splitext(data)[0] + '.txt'
            document = open(txt, "r")
            num = document.readline()
            for i in range(int(num)):
                line = document.readline()
                elems = line.split(' ')
                left = int(elems[0])
                top = int(elems[1])
                right = int(elems[2])
                bottom = int(elems[3])
                face_image = frame[top:bottom, left:right]
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
                    cv2.putText(frame, 'unknown', (left + 6, top - 6), cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 255, 0),
                                1)
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                else:
                    cv2.putText(frame, labels[order[0]], (left + 6, top - 6), cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 255, 0), 1)
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            document.close()
            cv2.imwrite(os.path.splitext(data)[0] + '_labeled.jpg', frame)
            print("%s processing %s takes %f" % (threadName, data, time.time() - ticks))
        queueLock.release()
        time.sleep(1)
queueLock = threading.Lock()
workQueue = Queue(20)
thread = myThread(1, 'ncs', workQueue)
thread.start()
# ***************************************************************
# Processing the images
# ***************************************************************
lastsendTime = time.time()
while True:
    # Capture frame-by-frame
    ret, frame = video_capture.read()
    if not ret:
        time.sleep(1)
        print('read failed...')
        video_capture.release()
        video_capture = cv2.VideoCapture(
            'rtsp://admin:Baustem123@192.168.1.153:554/Streaming/Channels/101?transportmode=unicast&profile=Profile_1')
        continue
    if fps %10 == 0:
        small_frame = cv2.resize(frame, (0, 0), fx=1/RESIZE, fy=1/RESIZE)
        #gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        #faces = opencv_detection(gray)
        faces = dlib_detection(small_frame)
        if len(faces) > 0:
            facess = faces
            image = time.strftime("%Y%m%d%H%M%S", time.localtime()) + '.jpg'
            txt = os.path.splitext(image)[0] + '.txt'
            txt_outfile = open(storagePath + txt, "w")
            txt_outfile.write(str(len(faces)) + '\n')
            for (x, y, w, h) in facess:
                x *= RESIZE
                y *= RESIZE
                w *= RESIZE
                h *= RESIZE
                # roi_gray = gray[y:y+h, x:x+w]
                # roi_color = frame[y:y+h, x:x+w]
                # eyes = eye_cascade.detectMultiScale(roi_gray)
                # if len(eyes) == 0:
                #    break
                #face = frame[y:y + h, x:x + w]
                cv2.rectangle(frame, (x+2, y+2), ( w + 2, h + 2), (0, 0, 255), 2)
                txt_outfile.write('{} {} {} {}\n'.format(x, y, w, h))
            txt_outfile.close()
            cv2.imwrite(storagePath + image, frame)

            if time.time() - lastsendTime > 1.1:
                #send a message to the queue
                queueLock.acquire()
                print('putting {} enter'.format(storagePath + image))
                workQueue.put(storagePath + image)
                queueLock.release()
                lastsendTime = time.time()
                print('putting {} exit'.format(storagePath + image))
        else:
            facess = []
    # Calculate and show the FPS
    fps = fps + 1
    #sfps = fps / (time.time() - t_start)
    #cv2.putText(frame, "FPS : " + str(int(sfps)), (10, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    # Display the resulting frame
    #cv2.imshow('Video', frame)
    #if cv2.waitKey(1) & 0xFF == ord('q'):
    #    break

# When everything is done, release the capture
exitFlag = 1
graph.DeallocateGraph()
device.CloseDevice()
video_capture.release()
#cv2.destroyAllWindows()

