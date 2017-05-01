from multiprocessing import Process, Queue, Pipe
from time import sleep, time
from messages import Message
from gps3 import agps3
from pipewatcher import PipeWatcher

from general import *

import logging, os

logger = logging.getLogger('root')

config = loadConfig()
PIPE_TIMEOUT = config.getfloat('Application', 'Pipe Timeout')
HOST = '127.0.0.1'
PORT = '2947'
PROTOCOL = 'json'

class GPS(Process):

    def __init__(self,
                 resultQue,                      # Queue to put the results
                 controlPipe):                   # Worker <-> Application

        super(GPS,self).__init__()
        #self.daemon=False
        self.name = 'GPS'
        self.__gpsd = agps3.GPSSocket()
        self.__gpsd.connect(HOST, PORT)
        self.__gpsd.watch(gpsd_protocol=PROTOCOL)
        self.__stream = agps3.DataStream()
        self.__frequency = 1
        self.__running = False
        self.__paused = True
        self.__pollCount = 0
        self.__resultQue = resultQue
        self.__pid = None
        self.__pipes['GPS'] = PipeWatcher(self, controlPipe, 'GPS.APPLICATION')
        seld.__pipes['GPS'].start()

        logger.debug('GPS process initalised')

    def run(self):
        self.__running = True
        self.__pid = os.getpid()
        logger.info('Starting GPS process on PID {}'.format(self.__pid))
        try:
            while self.__running:
                if not self.__paused and self.__running:
                    t = time()
                    self.__gpsd.next()
                    self.__pollCpunt += 1
                    self.__resultQue.put(Message('ALTITUDE', VALUE=self.__stream.alt))
                    self.__resultQue.put(Message('LATITUDE', VALUE=self.__stream.lat))
                    self.__resultQue.put(Message('LONGITUDE', VALUE=self.__stream.lon))
                    self.__resultQue.put(Message('HEADING', VALUE=self.__stream.track))
                    self.__resultQue.put(Message('GPS_SPEED', VALUE=self.__stream.speed))
                    self.__resultQue.put(Message('CLIMB', VALUE=self.__stream.climb))
                    sleeptime = time() - t - (1.0 / self.__frequency)
                    if sleeptime > 0: sleep(sleeptime)
                else:
                    sleep(1)
            logger.info('GPS process stopping')
            return
        except (KeyboardInterrupt, SystemExit):
            self.__running = False
            return

    def pause(self):
        if not self.__paused:
            logger.info('Pausing GPS process')
            self.__paused = True

    def resume(self):
        if self.__paused:
            logger.info('Resuming GPS process')
            self.__paused = False

    def status(self):
        #returns a dict of que status
        d = dict()
        d['Name'] = self.name
        d['Frequency'] = self.__frequency
        d['Running'] = self.__running
        d['Paused'] = self.__paused
        d['Poll Count'] = self.__pollCount
        d['Pid'] = self.__pid
        return Message('STATUS', STATUS = d)

    def stop(self):
        logger.info('Stopping GPS process')
        self.__running = False

