from multiprocessing import Queue, Event
#from threading import Thread
from ecu import ECU
from worker import Worker
from collector import Collector
from que import Que
from logger import DataLogger
from messages import Message, PipeCont
from time import sleep

from gps import GPS
from pipewatcher import PipeWatcher
from configparser import ConfigParser

from general import *

import logging, _thread

logging.config.dictConfig(worker_config)
logger = logging.getLogger(__name__)

config = loadConfig()
PIPE_TIMEOUT = config.getfloat('Application','Pipe Timeout')

class Monitor():

    def __init__(self):
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

        self.__events = {}

        workQue = Queue()
        resultQue = Queue()

        self.__pipes = {}
        self.__pipes['ECU'] = PipeWatcher(self, ecuControlPipe.s, 'ECU->APP')
        self.__pipes['WORKER'] = PipeWatcher(self, workerControlPipe.s, 'WORKER->APP')
        self.__pipes['COLLECTOR'] = PipeWatcher(self, collectorControlPipe.s, 'COLLECTOR->APP')
        self.__pipes['LOG'] = PipeWatcher(self, loggerControlPipe.s, 'LOG->APP')
        self.__pipes['GPS'] = PipeWatcher(self, gpsControlPipe.s, 'GPS->APP')

        self.__event = {}
        self.__event['ISCONNECTED'] = Event()
        self.__event['GETQUEUES'] = Event()
        self.__event['GETCOMMANDS'] = Event()
        self.__event['SUPPORTED_COMMANDS'] = Event()
        self.__event['GETSTATUS'] = Event()
        self.__event['SUM'] = Event()
        self.__event['AVG'] = Event()
        self.__event['MIN'] = Event()
        self.__event['MAX'] = Event()
        self.__event['VAL'] = Event()
        self.__event['DATALINE'] = Event()
        self.__event['LOGNAME'] = Event()
        self.__event['SNAPSHOT'] = Event()
        self.__event['SUMMARY'] = Event()

        self.__ecu = ECU(workQue,
                         ecuWorkerPipe.s,                              # ECU <-> Worker
                         ecuControlPipe.r,                             # ECU <-> Application
                         ecuDataPipe.s)                                # ECU <-> Collector

        self.__worker = Worker(workQue,
                               resultQue,
                               ecuWorkerPipe.r,                        # Worker <-> ECU
                               workerControlPipe.r,                    # Worker <-> Application
                               workerDataPipe.s,                       # Worker <-> Collector
                               loggerWorkerPipe.s)                     # Worker <-> Logger

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

        self.gpsEnable = config.getboolean('Application', 'GPS Enabled')

        self.__ecu.start()
        self.__collector.start()
        self.__worker.start()
        self.__logger.start()
        self.__gps.start()

        for p in self.__pipes:
            self.__pipes[p].start()
        # monitor needs to listen for a connection event triggered by WORKER

    def connection(self):
        if self.isConnected:
            self.resume()
        else:
            self.pause()

    def addQue(self, que, frequency):
        self.__pipes['ECU'].send(Message('ADDQUE',QUE = que, FREQUENCY = frequency))

    def addCommand(self, que, command, override=False):
        self.__pipes['ECU'].send(Message('ADDCOMMAND',QUE = que, COMMAND = command, OVERRIDE = override))

    def setQueFrequency(self, que, frequency):
        self.__pipes['ECU'].send(Message('SETFREQUENCY',QUE = que, FREQUENCY = frequency))

    def deleteAfterPoll(self, que, flag):
        self.__pipes['ECU'].send(Message('DELETEAFTERPOLL',QUE = que, FLAG = flag))

    def stop(self):
        self.__pipes['ECU'].send(Message('STOP'))
        self.__pipes['COLLECTOR'].send(Message('STOP'))
        self.__pipes['WORKER'].send(Message('STOP'))
        self.__pipes['LOG'].send(Message('STOP'))
        self.__pipes['GPS'].send(Message('STOP'))
        #self.__ecu.join()
        #self.__collector.join()
        #self.__worker.join()
        #self.__logger.join()
        #self.__gps.join()


    def pause(self):
        self.__pipes['ECU'].send(Message('PAUSE'))
        self.__pipes['LOG'].send(Message('PAUSE'))
        self.__pipes['GPS'].send(Message('PAUSE'))

    def resume(self):
        logger.info('Resuming co-processes')
        self.__pipes['ECU'].send(Message('RESUME'))
        self.__pipes['LOG'].send(Message('RESUME'))
        self.__pipes['GPS'].send(Message('RESUME'))

    def reset(self):
        self.__pipes['COLLECTOR'].send(Message('RESET'))

    def save(self):
        self.__pipes['LOG'].send(Message('SAVE'))

    def discard(self):
        self.__pipes['LOG'].send(Message('DISCARD'))

    def logPath(self, path):
        self.__pipes['LOG'].send(Message('LOGPATH',PATH = path))

    def logFrequency(self, frequency):
        self.__pipes['LOG'].send(Message('FREQUENCY', FREQUENCY = frequency))

    def logHeadings(self, headings):
        self.__pipes['LOG'].send(Message('ADD_HEADINGS', HEADINGS = headings))

    @property
    def isConnected(self):
        self.__connected_return = None                                        # Stores the response from the callback
        self.__pipes['WORKER'].send(Message('CONNECTED'))                     # Send message for incomming request
        self.__event['ISCONNECTED'].wait()
        self.__event['ISCONNECTED'].clear()
        return self.__connected_return['STATUS']                              # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def connected(self, p):                                                   # Callback function for IsConnected
        self.__connected_return = p                                            # Store the response returned for the caller to find
        self.__event['ISCONNECTED'].set()

    @property
    def queues(self):
        self.__queues_return = None                                           # Stores the response from the callback
        self.__pipes['ECU'].send(Message('GETQUEUES'))                        # Send message for incomming request
        self.__event['GETQUEUES'].wait()
        self.__event['GETQUEUES'].clear()
        return self.__queues_return['QUEUES']                                 # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def getqueues(self, p):                                                   # Callback function for IsConnected
        self.__queues_return = p                                               # Store the response returned for the caller to find
        self.__event['GETQUEUES'].set()

    @property
    def commands(self):
        self.__commands_return = None                                         # Stores the response from the callback
        self.__pipes['WORKER'].send(Message('GETCOMMANDS'))                   # Send message for incomming request
        self.__event['GETCOMMANDS'].wait()
        self.__event['GETCOMMANDS'].clear()
        return self.__commands_return['COMMANDS']                             # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def getcommands(self, p):                                                 # Callback function for IsConnected
        self.__commands_return = p                                             # Store the response returned for the caller to find
        self.__event['GETCOMMANDS'].set()

    @property
    def supportedCommands(self):
        self.__s_commands_return = None                                       # Stores the response from the callback
        self.__pipes['WORKER'].send(Message('SUPPORTED_COMMANDS'))            # Send message for incomming request
        self.__event['SUPPORTED_COMMANDS'].wait()
        self.__event['SUPPORTED_COMMANDS'].clear()
        return self.__s_commands_return['SUPPORTED_COMMANDS']                 # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def supported_commands(self, p):                                          # Callback function for IsConnected
        self.__s_commands_return = p                                           # Store the response returned for the caller to find
        self.__event['SUPPORTED_COMMANDS'].set()

    @property
    def status(self):
        s = {}
        self.__s_ecu_return = None                                            # Stores the response from the callback
        self.__s_data_return = None                                           # Stores the response from the callback
        self.__s_worker_return = None                                         # Stores the response from the callback
        self.__s_log_return = None                                            # Stores the response from the callback
        self.__s_gps_return = None                                            # Stores the response from the callback
        self.__pipes['WORKER'].send(Message('GETSTATUS'))                     # Send message for incomming request
        self.__event['GETSTATUS'].wait()
        self.__event['GETSTATUS'].clear()
        s['WORKER'] = self.__s_worker_return['STATUS']
        self.__pipes['ECU'].send(Message('GETSTATUS'))                        # Send message for incomming request
        self.__event['GETSTATUS'].wait()
        self.__event['GETSTATUS'].clear()
        s['ECU'] = self.__s_ecu_return['STATUS']
        self.__pipes['COLLECTOR'].send(Message('GETSTATUS'))                  # Send message for incomming request
        self.__event['GETSTATUS'].wait()
        self.__event['GETSTATUS'].clear()
        s['COLLECTOR'] = self.__s_data_return['STATUS']
        self.__pipes['LOG'].send(Message('GETSTATUS'))                        # Send message for incomming request
        self.__event['GETSTATUS'].wait()
        self.__event['GETSTATUS'].clear()
        s['LOG'] = self.__s_log_return['STATUS']
        self.__pipes['GPS'].send(Message('GETSTATUS'))                        # Send message for incomming request
        self.__event['GETSTATUS'].wait()
        self.__event['GETSTATUS'].clear()
        s['GPS'] = self.__s_gps_return['STATUS']
        return s                                                              # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def workerstatus(self, p):                                                # Callback function for IsConnected
        self.__s_worker_return = p                                             # Store the response returned for the caller to find
        self.__event['GETSTATUS'].set()

    # Callback function must be lower case of the message it is to respond to
    def ecustatus(self, p):                                                   # Callback function for IsConnected
        self.__s_ecu_return = p                                                # Store the response returned for the caller to find
        self.__event['GETSTATUS'].set()

    # Callback function must be lower case of the message it is to respond to
    def datastatus(self, p):                                                  # Callback function for IsConnected
        self.__s_data_return = p                                               # Store the response returned for the caller to find
        self.__event['GETSTATUS'].set()

    # Callback function must be lower case of the message it is to respond to
    def logstatus(self, p):                                                   # Callback function for IsConnected
        self.__s_log_return = p                                                # Store the response returned for the caller to find
        self.__event['GETSTATUS'].set()

    # Callback function must be lower case of the message it is to respond to
    def gpsstatus(self, p):                                                   # Callback function for IsConnected
        self.__s_gps_return = p                                                # Store the response returned for the caller to find
        self.__event['GETSTATUS'].set()

    def sum(self, name):
        self.__sum_return = None                                              # Stores the response from the callback
        self.__pipes['COLLECTOR'].send(Message('SUM', NAME = name))           # Send message for incomming request
        self.__event['SUM'].wait()
        self.__event['SUM'].clear()
        return self.__sum_return['SUM']                                       # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def getsum(self, p):                                                      # Callback function for IsConnected
        self.__sum_return = p                                                  # Store the response returned for the caller to find
        self.__event['SUM'].set()

    def avg(self, name):
        self.__avg_return = None                                              # Stores the response from the callback
        self.__pipes['COLLECTOR'].send(Message('AVG', NAME = name))           # Send message for incomming request
        self.__event['AVG'].wait()
        self.__event['AVG'].clear()
        return self.__avg_return['AVG']                                       # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def getavg(self, p):                                                      # Callback function for IsConnected
        self.__avg_return = p                                                  # Store the response returned for the caller to find
        self.__event['AVG'].set()

    def min(self, name):
        self.__min_return = None                                              # Stores the response from the callback
        self.__pipes['COLLECTOR'].send(Message('MIN', NAME = name))           # Send message for incomming request
        self.__event['MIN'].wait()
        self.__event['MIN'].clear()
        return self.__MIN_return['MIN']                                       # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def getmin(self, p):                                                      # Callback function for IsConnected
        self.__min_return = p                                                  # Store the response returned for the caller to find
        self.__event['MIN'].set()

    def max(self, name):
        self.__max_return = None                                              # Stores the response from the callback
        self.__pipes['COLLECTOR'].send(Message('MAX', NAME = name))           # Send message for incomming request
        self.__event['MAX'].wait()
        self.__event['MAX'].clear()
        return self.__max_return['MAX']                                       # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def getmax(self, p):                                                      # Callback function for IsConnected
        self.__max_return = p                                                  # Store the response returned for the caller to find
        self.__event['MAX'].set()

    def val(self, name):
        self.__val_return = None                                              # Stores the response from the callback
        self.__pipes['COLLECTOR'].send(Message('VAL', NAME = name))           # Send message for incomming request
        self.__event['VAL'].wait()
        self.__event['VAL'].clear()
        return self.__val_return['VAL']                                       # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def getval(self, p):                                                      # Callback function for IsConnected
        self.__val_return = p                                                  # Store the response returned for the caller to find
        self.__event['VAL'].set()

    def dataLine(self, name):
        self.__dataline_return = None                                         # Stores the response from the callback
        self.__pipes['COLLECTOR'].send(Message('DATALINE', NAME = name))      # Send message for incomming request
        self.__event['DATALINE'].wait()
        self.__event['DATALINE'].clear()
        return self.__dataline_return['LINE']                                 # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def data_line(self, p):                                                   # Callback function for IsConnected
        self.__dataline_return = p                                             # Store the response returned for the caller to find
        self.__event['DATALINE'].set()

    @property
    def gpsEnable(self):
        return self.__gpsEnabled

    @gpsEnable.setter
    def gpsEnable(self, v):
        self.__gpsEnabled = v
        if getBlockPath(
               config.get('Application', 'GPS Vendor ID'),
               config.get('Application', 'GPS Product ID')
           ) is None:
            logger.warning('GPS Device not found.  Disabling GPS.')
            self.__gpsEnabled = False

        if self.__gpsEnabled:
            #self.__pipes['GPS'].send(Message('RESUME'))
            self.__pipes['LOG'].send(Message('ADD_HEADINGS', HEADINGS = ['LATITUDE','LONGITUDE','ALTITUDE','GPS_SPD','HEADING']))
        else:
            self.__pipes['GPS'].send(Message('PAUSE'))
            self.__pipes['LOG'].send(Message('REMOVE_HEADINGS', HEADINGS = ['LATITUDE','LONGITUDE','ALTITUDE','GPS_SPD','HEADING']))

    @property
    def snapshot(self):
        self.__snapshot_return = None                                         # Stores the response from the callback
        self.__pipes['COLLECTOR'].send(Message('SNAPSHOT'))                   # Send message for incomming request
        self.__event['SNAPSHOT'].wait()
        self.__event['SNAPSHOT'].clear()
        return self.__snapshot_return['SNAPSHOT']                             # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def snap_shot(self, p):                                                   # Callback function for IsConnected
        self.__snapshot_return = p                                             # Store the response returned for the caller to find
        self.__event['SNAPSHOT'].set()

    @property
    def logName(self):
        self.__logname_return = None                                          # Stores the response from the callback
        self.__pipes['LOG'].send(Message('LOGNAME'))                          # Send message for incomming request
        self.__event['LOGNAME'].wait()
        self.__event['LOGNAME'].clear()
        return self.__logname_return['NAME']                                  # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def log_name(self, p):                                                    # Callback function for IsConnected
        self.__logname_return = p                                              # Store the response returned for the caller to find
        self.__event['LOGNAME'].set()

    @property
    def summary(self):
        self.__summary_return = None                                          # Stores the response from the callback
        self.__pipes['COLLECTOR'].send(Message('SUMMARY'))                    # Send message for incomming request
        self.__event['SUMMARY'].wait()
        self.__event['SUMMARY'].clear()
        return self.__summary_return['SUMMARY']                               # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def getsummary(self, p):                                                  # Callback function for IsConnected
        self.__summary_return = p                                              # Store the response returned for the caller to find
        self.__event['SUMMARY'].set()
