# RealTimeFaceRecognition
In this code, we simply finished the following sense:
1. using the opencv or dlib to detect human-faces
2. Recogtition the face in real time with fine-tuned VGG face model on Movidius ncs
3. record the recognition result to redis database;
4. there is a faceApp subscribed the event above and do the validation of an known person
5. if the face is known, unlock the door-locker which is enveloped as an OCF device

Note: this sense has been performed on RaspberryPI + Intel Movidius ncs + Wulian smart home devices.

Installation：
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

Run:
==============
1. python3 detect.py -c conf.json
2. python3 server.py
3. run the face app and face sensor
