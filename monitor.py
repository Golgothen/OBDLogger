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
from pipewatcher import PipeWatcher
from configparser import ConfigParser

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

        self.__pipes = {}
        self.__pipes['ECU'] = PipeWatcher(self, ecuControlPipe.s, 'APPLICATION.ECU')
        self.__pipes['WORKER'] = PipeWatcher(self, workerControlPipe.s, 'APPLICATION.WORKER')
        self.__pipes['DATA'] = PipeWatcher(self, collectorControlPipe.s, 'APPLICATION.DATA')
        self.__pipes['LOG'] = PipeWatcher(self, loggerControlPipe.s, 'APPLICATION.LOG')
        self.__pipes['GPS'] = PipeWatcher(self, gpsControlPipe.s, 'APPLICATION.GPS')

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
        self.__collector.start()
        self.__worker.start()
        self.__logger.start()
        self.__gps.start()
        for p in self.__pipes:
            self.__pipes[p].start()

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
        self.__pipes['LOG'].send(Message('STOP'))
        self.__pipes['GPS'].send(Message('STOP'))

    def pause(self):
        self.__pipes['ECU'].send(Message('PAUSE'))
        self.__pipes['ECU'].send(Message('PAUSE'))
        if self.__gpsEnabled:
            self.__pipes['GPS'].send(Message('PAUSE'))

    def resume(self):
        self.__pipes['ECU'].send(Message('RESUME'))
        self.__pipes['LOG'].send(Message('RESUME'))
        if self.__gpsEnabled:
            self.__pipes['GPS'].send(Message('RESUME'))

    def reset(self):
        self.__pipes['DATA'].send(Message('RESET'))

    def save(self):
        self.__pipes['LOG'].send(Message('SAVE'))

    def discard(self):
        self.__pipes['LOG'].send(Message('DISCARD'))

    def logPath(self, path):
        self.__pipes['LOG'].send(Message('LOGPATH',PATH = path))

    def logFrequency(self, frequency):
        self.__pipes['LOG'].send(Message('FREQUENCY', FREQUENCY = frequency))

    def logHeadings(self, headings):
        self.__pipes['LOG'].send(Message('HEADINGS', HEADINGS = headings))

    @property
    def isConnected(self):
        self.__connected_return = None                                        # Stores the response from the callback
        self.__pipes['WORKER'].send(Message('CONNECTED'))                     # Send message for incomming request
        while self.__connected_return is None:                                #
            sleep(0.001)                                                      # Wait here until the callback puts a response in *_return
        return self.__connected_return['STATUS']                              # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def connected(self, p):                                                   # Callback function for IsConnected
       self.__connected_return = p                                            # Store the response returned for the caller to find

    @property
    def queues(self):
        self.__queues_return = None                                           # Stores the response from the callback
        self.__pipes['ECU'].send(Message('GETQUEUES'))                        # Send message for incomming request
        while self.__queues_return is None:                                   #
            sleep(0.001)                                                      # Wait here until the callback puts a response in *_return
        return self.__queues_return['QUEUES']                                 # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def getqueues(self, p):                                                   # Callback function for IsConnected
       self.__queues_return = p                                               # Store the response returned for the caller to find

    @property
    def commands(self):
        self.__commands_return = None                                         # Stores the response from the callback
        self.__pipes['WORKER'].send(Message('GETCOMMANDS'))                   # Send message for incomming request
        while self.__commands_return is None:                                 #
            sleep(0.001)                                                      # Wait here until the callback puts a response in *_return
        return self.__commands_return['COMMANDS']                             # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def getcommands(self, p):                                                 # Callback function for IsConnected
       self.__commands_return = p                                             # Store the response returned for the caller to find

    @property
    def supportedCommands(self):
        self.__s_commands_return = None                                       # Stores the response from the callback
        self.__pipes['WORKER'].send(Message('SUPPORTED_COMMANDS'))            # Send message for incomming request
        while self.__s_commands_return is None:                               #
            sleep(0.001)                                                      # Wait here until the callback puts a response in *_return
        return self.__s_commands_return['SUPPORTED_COMMANDS']                 # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def supported_commands(self, p):                                          # Callback function for IsConnected
       self.__s_commands_return = p                                           # Store the response returned for the caller to find

    @property
    def status(self):
        s = {}
        self.__s_ecu_return = None                                            # Stores the response from the callback
        self.__s_data_return = None                                           # Stores the response from the callback
        self.__s_worker_return = None                                         # Stores the response from the callback
        self.__s_log_return = None                                            # Stores the response from the callback
        self.__pipes['WORKER'].send(Message('GETSTATUS'))                     # Send message for incomming request
        self.__pipes['ECU'].send(Message('GETSTATUS'))                        # Send message for incomming request
        self.__pipes['DATA'].send(Message('GETSTATUS'))                       # Send message for incomming request
        self.__pipes['LOG'].send(Message('GETSTATUS'))                        # Send message for incomming request
        while self.__s_ecu_return is None:                                    #
            sleep(0.001)                                                      # Wait here until the callback puts a response in *_return
        s['ECU'] = self.__s_ecu_return['STATUS']
        while self.__s_data_return is None:                                   #
            sleep(0.001)                                                      # Wait here until the callback puts a response in *_return
        s['DATA'] = self.__s_data_returnn['STATUS']
        while self.__s_worker_return is None:                                 #
            sleep(0.001)                                                      # Wait here until the callback puts a response in *_return
        s['WORKER'] = self.__s_ecu_returnn['STATUS']
        while self.__s_log_return is None:                                    #
            sleep(0.001)                                                      # Wait here until the callback puts a response in *_return
        s['LOG'] = self.__s_ecu_returnn['STATUS']
        return s                                                              # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def workerstatus(self, p):                                                # Callback function for IsConnected
       self.__s_worker_return = p                                             # Store the response returned for the caller to find

    # Callback function must be lower case of the message it is to respond to
    def ecustatus(self, p):                                                   # Callback function for IsConnected
       self.__s_ecu_return = p                                                # Store the response returned for the caller to find

    # Callback function must be lower case of the message it is to respond to
    def datastatus(self, p):                                                  # Callback function for IsConnected
       self.__s_data_return = p                                               # Store the response returned for the caller to find

    # Callback function must be lower case of the message it is to respond to
    def logstatus(self, p):                                                   # Callback function for IsConnected
       self.__s_log_return = p                                                # Store the response returned for the caller to find

    def sum(self, name):
        self.__sum_return = None                                              # Stores the response from the callback
        self.__pipes['DATA'].send(Message('SUM', NAME = name))                # Send message for incomming request
        while self.__sum_return is None:                                      #
            sleep(0.001)                                                      # Wait here until the callback puts a response in *_return
        return self.__sum_return['SUM']                                       # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def getsum(self, p):                                                      # Callback function for IsConnected
       self.__sum_return = p                                                  # Store the response returned for the caller to find

    def avg(self, name):
        self.__avg_return = None                                              # Stores the response from the callback
        self.__pipes['DATA'].send(Message('AVG', NAME = name))                # Send message for incomming request
        while self.__avg_return is None:                                      #
            sleep(0.001)                                                      # Wait here until the callback puts a response in *_return
        return self.__avg_return['AVG']                                       # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def getavg(self, p):                                                      # Callback function for IsConnected
       self.__avg_return = p                                                  # Store the response returned for the caller to find

    def min(self, name):
        self.__min_return = None                                              # Stores the response from the callback
        self.__pipes['DATA'].send(Message('MIN', NAME = name))                # Send message for incomming request
        while self.__MIN_return is None:                                      #
            sleep(0.001)                                                      # Wait here until the callback puts a response in *_return
        return self.__MIN_return['MIN']                                       # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def getmin(self, p):                                                      # Callback function for IsConnected
       self.__min_return = p                                                  # Store the response returned for the caller to find

    def max(self, name):
        self.__max_return = None                                              # Stores the response from the callback
        self.__pipes['DATA'].send(Message('MAX', NAME = name))                # Send message for incomming request
        while self.__max_return is None:                                      #
            sleep(0.001)                                                      # Wait here until the callback puts a response in *_return
        return self.__max_return['MAX']                                       # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def getmax(self, p):                                                      # Callback function for IsConnected
       self.__max_return = p                                                  # Store the response returned for the caller to find

    def val(self, name):
        self.__val_return = None                                              # Stores the response from the callback
        self.__pipes['DATA'].send(Message('VAL', NAME = name))                # Send message for incomming request
        while self.__val_return is None:                                      #
            sleep(0.001)                                                      # Wait here until the callback puts a response in *_return
        return self.__val_return['VAL']                                       # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def getval(self, p):                                                      # Callback function for IsConnected
       self.__val_return = p                                                  # Store the response returned for the caller to find

    def dataLine(self, name):
        self.__dataline_return = None                                         # Stores the response from the callback
        self.__pipes['DATA'].send(Message('DATALINE', NAME = name))           # Send message for incomming request
        while self.__dataline_return is None:                                 #
            sleep(0.001)                                                      # Wait here until the callback puts a response in *_return
        return self.__dataline_return['LINE']                                 # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def data_line(self, p):                                                   # Callback function for IsConnected
       self.__dataline_return = p                                             # Store the response returned for the caller to find

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
        self.__snapshot_return = None                                         # Stores the response from the callback
        self.__pipes['DATA'].send(Message('SNAPSHOT'))                        # Send message for incomming request
        while self.__snapshot_return is None:                                 #
            sleep(0.001)                                                      # Wait here until the callback puts a response in *_return
        return self.__snapshot_return['SNAPSHOT']                             # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def snap_shot(self, p):                                                   # Callback function for IsConnected
       self.__snapshot_return = p                                             # Store the response returned for the caller to find

    @property
    def logName(self):
        self.__logname_return = None                                          # Stores the response from the callback
        self.__pipes['LOG'].send(Message('LOGNAME'))                          # Send message for incomming request
        while self.__logname_return is None:                                  #
            sleep(0.001)                                                      # Wait here until the callback puts a response in *_return
        return self.__logname_return['NAME']                                  # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def log_name(self, p):                                                    # Callback function for IsConnected
       self.__logname_return = p                                              # Store the response returned for the caller to find

    @property
    def summary(self):
        self.__summary_return = None                                          # Stores the response from the callback
        self.__pipes['DATA'].send(Message('SUMMARY'))                         # Send message for incomming request
        while self.__summary_return is None:                                  #
            sleep(0.001)                                                      # Wait here until the callback puts a response in *_return
        return self.__summary_return['SUMMARY']                               # Return the response from the callback to the caller

    # Callback function must be lower case of the message it is to respond to
    def getsummary(self, p):                                                  # Callback function for IsConnected
       self.__summary_return = p                                              # Store the response returned for the caller to find
