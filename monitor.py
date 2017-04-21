from multiprocessing import Queue #, Manager
#from threading import Thread
from ecu import ECU
from worker import Worker
from collector import Collector
from que import Que
from logger import DataLogger
from messages import Message, PipeCont
from time import sleep

from gps import GPS
from general import *

import sys, logging

logger = logging.getLogger('root')

config = loadConfig()
PIPE_TIMEOUT = config.getfloat('Application','Pipe Timeout')

class Monitor():

    def __init__(self, port, baud):
        #super(Monitor,self).__init__()
        ecuWorkerPipe = PipeCont()                                     # ECU <-> Worker
        ecuDataPipe = PipeCont()                                       # ECU <-> Collector
        ecuControlPipe = PipeCont()                                    # ECU <-> Application
        workerDataPipe = PipeCont()                                    # Worker <-> Collector
        workerControlPipe = PipeCont()                                 # Worker <-> Application
        collectorControlPipe = PipeCont()                              # Collector <-> Application
        loggerControlPipe = PipeCont()                                 # Logger <-> Application
        loggerDataPipe = PipeCont()                                    # Logger <-> Collector
        loggerWorkerPipe = PipeCont()                                  # Logger <-> Worker
        gpsControlPipe = PipeCont()                                    # GPS <-> Application

        workQue = Queue()
        resultQue = Queue()

        self.__ecuComm = ecuControlPipe.s                              # Handle for communication to ECU process
        self.__workerComm = workerControlPipe.s                        # Handle for communication to Worker process
        self.__dataComm = collectorControlPipe.s                       # Handle for communication to Collector process
        self.__logComm = loggerControlPipe.s                           # Handle for communication to Logger process
        self.__gpsComm = gpsControlPipe.s                              # Handle for communication to GPS process

        self.__ecu = ECU(workQue,
                         ecuWorkerPipe.s,                              # ECU <-> Worker
                         ecuControlPipe.r,                             # ECU <-> Application
                         ecuDataPipe.s)                                # ECU <-> Collector

        self.__worker = Worker(workQue,
                               resultQue,
                               ecuWorkerPipe.r,                        # Worker <-> ECU
                               workerControlPipe.r,                    # Worker <-> Application
                               workerDataPipe.s,                       # Worker <-> Collector
                               loggerWorkerPipe.s,                     # Worker <-> Logger
                               port,
                               baud)

        self.__collector = Collector(ecuDataPipe.r,                    # Collector <-> ECU
                                     collectorControlPipe.r,           # Collector <-> Application
                                     loggerDataPipe.r,                 # Collector <-> Logger
                                     workerDataPipe.r,                 # Collector <-> Worker
                                     resultQue)

        self.__logger = DataLogger(loggerControlPipe.r,                # Logger <-> Application
                                   loggerDataPipe.s,                   # Logger <-> Collector
                                   loggerWorkerPipe.r)                 # Logger <-> Worker

        self.__gps = GPS(resultQue,
                         gpsControlPipe.r)                             # GPS <-> Application

        self.__gpsEnabled = config.getboolean('Application', 'GPS Enabled')

        self.__ecu.start()
        self.__worker.start()
        self.__collector.start()
        self.__logger.start()
        if self.__gpsEnabled:
            self.__gps.start()

    def __checkWorkerPipe(self, message, timeout):
        # Check Worker pipe
        while self.__workerComm.poll(timeout):
            m = self.__workerComm.recv()
            logger.debug('Received {} on Worker pipe'.format(m.message))
            if m.message == message: 
                return m.params
            else:
                logger.info('Discarding out of sync message {}.  Expected {}'.format(m.message, message))
        return None

    def __checkDataPipe(self, message, timeout):
        # Check Collector pipe
        while self.__dataComm.poll(timeout):
            m = self.__dataComm.recv()
            logger.debug('Received {} on Collector pipe'.format(m.message))
            if m.message == message: 
                return m.params
            else:
                logger.info('Discarding out of sync message {}. Expected {}'.format(m.message, message))
        return None

    def __checkECUPipe(self, message, timeout):
        # Check ECU pipe
        while self.__ecuComm.poll(timeout):
            m = self.__ecuComm.recv()
            logger.debug(m.message + 'Received {} on ECU pipe'.format(m.message))
            if m.message == message:
                return m.params
            else:
                logger.info('Discarding out of sync message {}. Expected {}'.format(m.message, message))
        return None

    def __checkLoggerPipe(self, message, timeout):
        # Check Logger pipe
        while self.__logComm.poll(timeout):
            m = self.__logComm.recv()
            logger.debug('Received {} on Logger pipe'.format(m.message))
            if m.message == message:
                return m.params
            else:
                logger.info('Discarding out of sync message {}. Expected {}'.format(m.message, message))
        return None

    def isConnected(self):
        self.__workerComm.send(Message('CONNECTED'))
        r = self.__checkWorkerPipe('CONNECTED', PIPE_TIMEOUT)
        if r is not None:
            return r['STATUS']
        else:
            logger.warning('Worker Timeout requesting connection status')
            return False

    def addQue(self, que, frequency):
        self.__ecuComm.send(Message('ADDQUE',QUE = que, FREQUENCY = frequency))
        logger.debug('Add Que {} message sent'.format(que))

    def getQueues(self):
        self.__ecuComm.send(Message('GETQUEUES'))
        r = self.__checkECUPipe('GETQUEUES', PIPE_TIMEOUT)
        if r is not None:
            return r['QUEUES']
        else:
            logger.warning('ECU Timeout requesting Que List')

    def getQueCommands(self, que):
        self.__ecuComm.send(Message('GETCOMMANDS', QUE = que))
        r = self.__checkECUPipe('GETCOMMANDS', PIPE_TIMEOUT)
        if r is not None:
            return r['COMMANDS']
        else:
            logger.warning('ECU timeout requesting que commands')

    def getInterface(self):
        self.__ecuComm.send(Message('INTERFACE'))
        r = self.__checkECUPipe('INTERFACE', PIPE_TIMEOUT)
        if r is not None:
            return r['INTERFACE']
        else:
            logger.warning('ECU Timeout requesting interface')

    def addCommand(self, que, command, override=False):
        self.__ecuComm.send(Message('ADDCOMMAND',QUE = que, COMMAND = command, OVERRIDE = override))
        logger.debug('Add Command {} on que {} sent'.format(command, que))

    def setQueFrequency(self, que, frequency):
        self.__ecuComm.send(Message('SETFREQUENCY',QUE = que, FREQUENCY = frequency))
        logger.debug('Set frequency on que {} sent'.format(que))

    def deleteAfterPoll(self, que, flag):
        self.__ecuComm.send(Message('DELETEAFTERPOLL',QUE = que, FLAG = flag))
        logger.debug('Delete after poll on que {} sent'.format(que))

    def commands(self):
        self.__workerComm.send(Message('COMMANDS'))
        r = self.__checkWorkerPipe('COMMANDS', PIPE_TIMEOUT)
        if r is not None:
            return r['COMMANDS']
        else:
            logger.warning('ECU Timeout requesting commands')

    def supportedcommands(self):
        self.__workerComm.send(Message('SUPPORTED_COMMANDS'))
        r = self.__checkWorkerPipe('SUPPORTED_COMMANDS', PIPE_TIMEOUT)
        if r is not None:
            return r['SUPPORTED_COMMANDS']
        else:
            logger.warning('ECU Timeout requesting commands')

    def status(self):
        d = dict()
        self.__ecuComm.send(Message('STATUS'))
        self.__dataComm.send(Message('STATUS'))
        self.__workerComm.send(Message('STATUS'))
        self.__logComm.send(Message('STATUS'))

        r = self.__checkWorkerPipe('STATUS', PIPE_TIMEOUT)
        if r is not None:
            d['Worker Status'] = r['STATUS']
        else:
            logger.warning('Worker Timeout requesting status')

        r = self.__checkECUPipe('STATUS',PIPE_TIMEOUT)
        if r is not None:
            d['ECU Status'] = r['STATUS']
        else:
            logger.warning('ECU Timeout requesting status')

        r = self.__checkLoggerPipe('STATUS', PIPE_TIMEOUT)
        if r is not None:
            d['Logger Status'] = r['STATUS']
        else:
            logger.warning('Logger Timeout requesting status')

        r = self.__checkDataPipe('STATUS', PIPE_TIMEOUT)
        if r is not None:
            d['Collector Status'] = r['STATUS']
        else:
            logger.warning('Collector Timeout requesting status')
        return d

    def stop(self):
        self.__ecuComm.send(Message('STOP'))
        self.__logComm.send(Message('STOP'))

    def pause(self):
        self.__ecuComm.send(Message('PAUSE'))
        self.__logComm.send(Message('PAUSE'))

    def resume(self):
        self.__ecuComm.send(Message('RESUME'))
        logger.info('Starting logger')
        self.__logComm.send(Message('RESUME'))

    def sum(self, name):
        self.__dataComm.send(Message('SUM',NAME = name))
        r = self.__checkDataPipe('SUM', PIPE_TIMEOUT)
        if r is not None:
            return r['SUM']

    def avg(self, name):
        self.__dataComm.send(Message('AVG',NAME = name))
        r = self.__checkDataPipe('AVG', PIPE_TIMEOUT)
        if r is not None:
            return r['AVG']

    def min(self, name):
        self.__dataComm.send(Message('MIN', NAME = name))
        r = self.__checkDataPipe('MIN', PIPE_TIMEOUT)
        if r is not None:
            return r['MIN']

    def max(self, name):
        self.__dataComm.send(Message('MAX',NAME = name))
        r = self.__checkDataPipe('MAX', PIPE_TIMEOUT)
        if r is not None:
            return r['MAX']

    @property
    def gpsEnable(self):
        return self.__gpsEnabled

    @gpsEnable.setter
    def gpsEnable(self, v):
        self.__gpsEnabled = v
        if self.__gpsEnabled:
            if self.__gps.is_alive():
                self.__gpsComm.send(Message('RESUME'))
            else:
                self.__gps.start()
            self.__logComm.send('ADD_HEADINGS', HEADINGS = ['LATITUDE','LOGITUDE','ALTITUDE','GPS_SPEED','HEADING','CLIMB'])
        else:
            self.__gpsComm.send(Message('PAUSE'))
            self.__logComm.send('REMOVE_HEADINGS', HEADINGS = ['LATITUDE','LOGITUDE','ALTITUDE','GPS_SPEED','HEADING','CLIMB'])

    @property
    def snapshot(self):
        self.__dataComm.send(Message('SNAPSHOT'))
        r = self.__checkDataPipe('SNAPSHOT', PIPE_TIMEOUT)
        if r is not None:
            return r['SNAPSHOT']

    def reset(self):
        self.__dataComm.send(Message('RESET'))

    def save(self):
        self.__logComm.send(Message('SAVE'))

    def discard(self):
        self.__logComm.send(Message('DISCARD'))

    def logPath(self, path):
        self.__logComm.send(Message('LOGPATH',PATH = path))

    def logFrequency(self, frequency):
        self.__logComm.send(Message('FREQUENCY', FREQUENCY = frequency))

    def logName(self):
        self.__logComm.send(Message('LOGNAME'))
        r = self.__checkLoggerPipe('LOGNAME', PIPE_TIMEOUT)
        if r is not None:
            return r['NAME']

    def addLogHeadings(self, headings):
        self.__logComm.send(Message('ADD_HEADINGS', HEADINGS = headings))

    def removeLogHeadings(self, headings):
        self.__logComm.send(Message('REMOVE_HEADINGS', HEADINGS = headings))

    def tripTimeout(self, timeout):
        self.__logComm.send(Message('TIMEOUT', TIMEOUT = timeout))

    @property
    def summary(self):
        self.__dataComm.send(Message('SUMMARY'))
        r = self.__checkDataPipe('SUMMARY', PIPE_TIMEOUT)
        if r is not None:
            return r['SUMMARY']

