# RealTimeFaceRecognition
Recogtition the face in real time with pre-trained VGG face model and Movidius ncs.

Installation：
1. install the dlib
  a. git clone https://github.com/davisking/dlib.git
  b. cd dlib;mkdir build; cd build; cmake .. -DDLIB_USE_CUDA=0 -DUSE_AVX_INSTRUCTIONS=1; cmake --build .
  c. cd ..;python3 setup.py install --yes USE_AVX_INSTRUCTIONS --no DLIB_USE_CUDA
2. install dependency
  a. pip3 install numpy redis
  b. sudo apt-get update; sudo apt-get install redis-server
3. install ncs sdk

For CoAP Server:
1. pip3 install LinkHeader
4. install aiocoap
