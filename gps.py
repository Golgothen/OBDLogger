from multiprocessing import Process, Queue, Pipe
from time import sleep, time
from messages import Message
from gps3 import agps3
from pipewatcher import PipeWatcher

from general import *

import logging

logging.config.dictConfig(worker_config)
logger = logging.getLogger(__name__)

config = loadConfig()
PIPE_TIMEOUT = config.getfloat('Application', 'Pipe Timeout')
HOST = 'localhost'
PORT = 2947
PROTOCOL = 'json'

class GPS(Process):

    def __init__(self,
                 resultQue,                      # Queue to put the results
                 controlPipe):                   # Worker <-> Application

        super(GPS, self).__init__()
        #self.daemon=False
        self.name = 'GPS'
        self.__gpsd = agps3.GPSDSocket()
        self.__gpsd.connect(host = HOST, port = PORT)
        self.__gpsd.watch() #gpsd_protocol=PROTOCOL)
        self.__stream = agps3.DataStream()
        self.__frequency = 1
        self.__running = False
        self.__paused = True
        self.__pollCount = 0
        self.__resultQue = resultQue
        self.__pipes = {}
        self.__pipes['GPS'] = PipeWatcher(self, controlPipe, 'APP->GPS')

        logger.debug('GPS process initalised')

    def run(self):
        logger.info('Starting GPS process on PID {}'.format(self.pid))
        self.__pipes['GPS'].start()
        self.__running = True
        while self.__running:
            try:
                logger.debug('Running = {}, Paused = {}'.format(self.__running, self.__paused))
                t = time()
                for new_data in self.__gpsd:
                    if new_data:
                        logger.debug('New Data')
                        self.__stream.unpack(new_data)
                        logger.debug('Stream values: {},{},{},{}'.format(self.__stream.lat,self.__stream.lon,self.__stream.speed,self.__stream.alt))
                        if not self.__paused:
                            logger.debug('Inserting values to queue')
                            self.__pollCount += 1
                            self.__resultQue.put(Message('ALTITUDE', VALUE = None if type(self.__stream.alt) is not float else self.__stream.alt))
                            self.__resultQue.put(Message('LATITUDE', VALUE =  None if type(self.__stream.lat) is not float else self.__stream.lat))
                            self.__resultQue.put(Message('LONGITUDE', VALUE =  None if type(self.__stream.lon) is not float else self.__stream.lon))
                            self.__resultQue.put(Message('HEADING', VALUE =  None if type(self.__stream.track) is not float else self.__stream.track))
                            self.__resultQue.put(Message('GPS_SPD', VALUE =  None if type(self.__stream.speed) is not float else self.__stream.speed*3.6)) # GPS reports speed in m/s
                    sleep(1)
            except (KeyboardInterrupt, SystemExit):
                self.__running = False
                self.__gpsd.close()
                return
            except:
                logger.critical('Unhandled exception occured in GPS process:', exc_info = True, stack_info = True)
                continue
        logger.info('GPS process stopping')


    def pause(self, p = None):
        self.__paused = True
        logger.info('GPS process paused = {}'.format(self.__paused))

    def resume(self, p = None):
        logger.debug('GPS process resuming')
        self.__paused = False
        logger.debug('GPS process paused = {}'.format(self.__paused))

    def getstatus(self, p = None):
        #returns a dict of que status
        d = dict()
        d['Name'] = self.name
        d['Frequency'] = self.__frequency
        d['Running'] = self.__running
        d['Paused'] = self.__paused
        d['Poll Count'] = self.__pollCount
        d['Pid'] = self.pid
        return Message('GPSSTATUS', STATUS = d)

    def stop(self, p = None):
        #logger.info('Stopping GPS process')
        self.__running = False

