import json
import redis
import asyncio
import aiocoap.resource as resource
from aiocoap.resource import ObservableResource
import aiocoap
import threading
import time

CONTENT_FORMAT_JSON = 50

class FaceSensorResource(resource.ObservableResource):
    def __init__(self):
        super(FaceSensorResource, self).__init__()
        self.face = {'value':False,
                     'rt':['oic.r.sensor.face'],
                     'if':['oic.if.r', 'oic.if.baseline'],
                     'face':['unknown']}
        self._store = redis.Redis()
        self.handle = None
        self.notify()  # start monitoring resource state

    def current_face(self):
        face = self._store.get('face')
        self._store.delete('face')
        dict = None
        if face != None :
            face = face.decode('utf-8')
            print('face = {}'.format(face))
            if '|' in face:
                dict = {'face': face.split('|')[1].split('#')}
        return dict

    def face_changed(self, new_face):
        if (new_face['face'] != self.face['face']):
            return True
        return False

    def notify(self):
        new_face = self.current_face()
        if (new_face != None and self.face_changed(new_face)):
            self.face['face'] = new_face['face']
            self.face['value'] = True
            self.updated_state()  # inform subscribers
        else:
            self.face['value'] = False
            print('No face change')
        # check again after 2 seconds
        asyncio.get_event_loop().call_later(2, self.notify)

    def reschedule(self):
        print('Enter reschedule')
        self.handle = asyncio.get_event_loop().call_later(2, self.notify)

    def update_observation_count(self, count):
        print('Enter update_observation_count')
        if count and self.handle is None:
            print("Starting the clock")
            self.handle = self.reschedule()
        if count == 0 and self.handle:
            print("Stopping the clock")
            self.handle.cancel()
            self.handle = None

    @asyncio.coroutine
    def render_get(self, request):
        print('Render get requested: {}'.format(self.face))
        mesg = aiocoap.Message(code=aiocoap.CONTENT,
                               payload=json.dumps(self.face).encode('UTF-8'))
        mesg.opt.content_format = CONTENT_FORMAT_JSON
        return mesg


def main():
    # Resource tree creation
    root = resource.Site()
    root.add_resource(('sensor','FaceRecognition'), FaceSensorResource())
    asyncio.Task(aiocoap.Context.create_server_context(root))
    asyncio.get_event_loop().run_forever()
    loop = asyncio.get_event_loop()

if __name__ == "__main__":
    main()