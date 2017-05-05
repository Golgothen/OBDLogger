from multiprocessing import Process, Queue, Pipe
from time import sleep, time
from messages import Message
from gps3 import agps3
from pipewatcher import PipeWatcher

from general import *

import logging, os, sys

logger = logging.getLogger('root')

config = loadConfig()
PIPE_TIMEOUT = config.getfloat('Application', 'Pipe Timeout')
HOST = 'localhost'
PORT = 2947
PROTOCOL = 'json'

class GPS(Process):

    def __init__(self,
                 resultQue,                      # Queue to put the results
                 controlPipe):                   # Worker <-> Application

        super(GPS,self).__init__()
        #self.daemon=False
        self.name = 'GPS'
        #self.__gpsd = agps3.GPSDSocket()
        #self.__gpsd.connect(host = HOST, port = PORT)
        #self.__gpsd.watch() #gpsd_protocol=PROTOCOL)
        #self.__stream = agps3.DataStream()
        self.__frequency = 1
        self.__running = False
        self.__paused = True
        self.__pollCount = 0
        self.__resultQue = resultQue
        self.__pid = None
        self.__pipes = {}
        self.__pipes['GPS'] = PipeWatcher(self, controlPipe, 'APP->GPS')
        self.__pipes['GPS'].start()

        logger.debug('GPS process initalised')

    def run(self):
        self.__running = True
        self.__pid = os.getpid()
        logger.info('Starting GPS process on PID {}'.format(self.__pid))
        try:
            while self.__running:
                #logger.debug('Running = {}, Paused = {}'.format(self.__running, self.__paused))
                t = time()
                #for new_data in self.__gpsd:
                #    if new_data:
                #        logger.debug('New Data')
                #        self.__stream.unpack(new_data)
                if not self.__paused:
                    self.__resultQue.put(Message('ALTITUDE', VALUE = 56.7))
                    self.__resultQue.put(Message('LATITUDE', VALUE =  -37.8136))
                    self.__resultQue.put(Message('LONGITUDE', VALUE =  144.9631))
                    self.__resultQue.put(Message('HEADING', VALUE =  270.0))
                    self.__resultQue.put(Message('GPS_SPD', VALUE =  0.0)) # GPS reports speed in m/s
                #    self.__pollCount += 1
                #    self.__resultQue.put(Message('ALTITUDE', VALUE = None if type(self.__stream.alt) is not float else self.__stream.alt))
                #    self.__resultQue.put(Message('LATITUDE', VALUE =  None if type(self.__stream.lat) is not float else self.__stream.lat))
                #    self.__resultQue.put(Message('LONGITUDE', VALUE =  None if type(self.__stream.lon) is not float else self.__stream.lon))
                #    self.__resultQue.put(Message('HEADING', VALUE =  None if type(self.__stream.track) is not float else self.__stream.track))
                #    self.__resultQue.put(Message('GPS_SPD', VALUE =  None if type(self.__stream.speed) is not float else self.__stream.speed*3.6)) # GPS reports speed in m/s
                sleeptime = time() - t - (1.0 / self.__frequency)
                if sleeptime > 0: sleep(sleeptime)
            #logger.info('GPS process stopping')
            return
        except (KeyboardInterrupt, SystemExit):
            self.__running = False
            #self.__gpsd.close()
            return
        except:
            logger.critical('Unhandled exception occured in GPS process: {}'.format(sys.exc_info))


    def pause(self, p = None):
        if not self.__paused:
            self.__paused = True
            logger.info('GPS process paused = {}'.format(self.__paused))

    def resume(self, p = None):
        if self.__paused:
            self.__paused = False
            logger.info('GPS process paused = {}'.format(self.__paused))

    def status(self, p = None):
        #returns a dict of que status
        d = dict()
        d['Name'] = self.name
        d['Frequency'] = self.__frequency
        d['Running'] = self.__running
        d['Paused'] = self.__paused
        d['Poll Count'] = self.__pollCount
        d['Pid'] = self.__pid
        return Message('STATUS', STATUS = d)

    def stop(self, p = None):
        #logger.info('Stopping GPS process')
        self.__running = False

