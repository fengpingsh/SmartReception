SmartReception
=====================================================
This is an implement of smart reception. Now, it's just an single sense which only support to unlock the door if known employees come.

# Precondition
1. an IPC installed in front of the office entrance;  
2. a smart locker should be installed;  
3. both the IPC and the locker and the device which run this code should in the same network;  

# About the code
In this code, we simply finished the following sense:  
1. real time face detection: two ways are supported which are opencv and dlib;  
2. face recogtition: After detection, the face will be sent to a pre-trained VGG model to estimate who are they with the acceration by Movidius ncs,
then, record the results to redis database;  
3. faceSensor: subscribe the recognition result, and envelop the result as a self-defined OCF face sensor. As soon as face recognized, it will notify all subscribers;  
4. faceApp: Observe the faceSensor resource and the smart locker resource as well, if the sensor report the known face, it will post a unlock message to the smart locker
to unlock the door, and if not, nothing will be done.  

Note: this sense has been performed on RaspberryPI + Intel Movidius ncs + Wulian smart home devices. The smart locker OCF device is not included in this code.

# Installation：
==============
1. install the dlib  
2. install opencv3, python-opencv and associated  
3. install dependency: like numpy, redis, redis-server  
4. install ncs sdk  
5. install for CoAP Server:  
    a. pip3 install LinkHeader  
    b. install aiocoap  
6. install the iotivity sdk  
7. compile the faceApp and faceSensor  

# Configuration
url: the rtsp stream url of the IPC  
graph: the graph file loadable by Movidius ncs  
mean: mean file of the all trained faces;  
label: label file of the pre-trained model, here is the names of the faces;  
fps: skip how many frames when processing;  
resize: for acceration in some low performance platform like raspberry pi, zoom out the size of the frame to be processed;  
debug: int value. set to none zero if you want to enable debug;  

# Run
1. python3 detect.py -c conf.json  
2. python3 server.py  
3. run the face app and face sensor  

# Donation
If you like this code or idea, please consider donating to the
address below.

fengping <fengping@baustem.com>  
1HDHUQGjU42ytfJDud1vGuJb4HksUcATjh

# TODO
replace the detection and recognition with the face-comparation or realtime-face-recognition.  
connect to the attendance system, which should also detect the off work;  
support the legacy unlock device;




