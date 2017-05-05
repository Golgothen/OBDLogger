from multiprocessing import Process, Queue, Pipe
from datetime import datetime
from time import sleep
from messages import Message
from pipewatcher import PipeWatcher
from configparser import ConfigParser

from general import *
import logging, os, obd, sys

logger = logging.getLogger('root')

config = loadConfig()
PIPE_TIMEOUT = config.getfloat('Application','Pipe Timeout')

class Worker(Process):

    def __init__(self,
                 workQue,
                 resultQue,
                 ecuPipe,                        # Worker <-> ECU
                 controlPipe,                    # Worker <-> Application
                 dataPipe,                       # Worker <-> Collector
                 logPipe):                       # Worker <-> Logger

        super(Worker,self).__init__()
        #self.daemon=False
        self.name = 'WORKER'
        self.__frequency = 50
        self.__running = False
        self.__paused = True
        self.__pollCount = 0.0
        self.__pollRate = 0.0
        self.__workQue = workQue                 # Message queue object
        self.__resultQue = resultQue
        self.__firstPoll = None
        self.__pid = None
        self.__pipes = {}
        self.__pipes['ECU'] = PipeWatcher(self, ecuPipe, 'ECU->WORKER')
        self.__pipes['APPLICATION'] = PipeWatcher(self, controlPipe, 'APP->WORKER')
        self.__pipes['DATA'] = PipeWatcher(self, dataPipe, 'COLLECTOR->WORKER')
        self.__pipes['LOG'] = PipeWatcher(self, logPipe, 'LOG->WORKER')
        self.__baud = config.getint('Application','OBD Baud')
        self.__port = getBlockPath(config.get('Application','OBD Vendor ID'),config.get('Application','OBD Product ID'))
        logger.info('ELM device found at /dev/{}'.format(self.__port))
        #self.__interface = obd.OBD('/dev/' + self.__port, self.__baud)
        self.__connected = False
        self.__commands = []
        self.__supported_commands = []
        self.__maxQueLength = 0
        for c in obd.commands[1]:
            if c.name[:4] != 'PIDS':
                self.__commands.append(c.name)
        self.__connect()
        logger.debug('Worker process initalised')

    def run(self):
        self.__running = True
        self.__pid = os.getpid()
        logger.info('Starting Worker process on PID {}'.format(self.__pid))
        # Start watcher threads for pipes
        for p in self.__pipes:
            self.__pipes[p].start()
        try:
            while self.__running:
                if not self.__isConnected():
                    self.__paused = True
                    self.__firstPoll = None
                    self.__connect()
                else:
                    if self.__firstPoll is None:
                        self.__firstPoll = datetime.now()
                    if not self.__paused and self.__running:
                        while self.__workQue.qsize() > 0:
                            if self.__workQue.qsize() > self.__maxQueLength:
                                self.__maxQueLength = self.__workQue.qsize()
                            m = self.__workQue.get()
                            if self.__isConnected():
                                #q = self.__interface.query(obd.commands[m])                                                    # todo: uncomment after testing
                                self.__pollCount+=1
                                if self.__firstPoll is None:
                                    self.__firstPoll = datetime.now()
                                #if not q.is_null():                                                                            # todo: uncomment after testing
                                #    logger.debug('{} - {}'.format(m, q.value))
                                #    self.__resultQue.put(Message(m, VALUE=q.value.magnitude))
                                self.__resultQue.put(Message(m, VALUE = 0.0))                                                 # todo: delete after testing
                        self.__pollRate = self.__pollCount / (datetime.now() - self.__firstPoll).total_seconds()
                sleep(1.0 / self.__frequency)
            logger.info('Worker process stopping')
            return
        except (KeyboardInterrupt, SystemExit):
            self.__running = False
            return
        except:
            logger.critical('Unhandled exception occured in Worker process: {}'.format(sys.exc_info))


    def getcommands(self, p = None):
        return Message('GETCOMMANDS', COMMANDS = self.__commands)

    def supported_commands(self, p = None):
        return Message('SUPPORTED_COMMANDS', SUPPORTED_COMMANDS = self.__supported_commands)

    def connected(self, p = None):
        return Message('CONNECTED', STATUS = self.__isConnected())

    def pause(self, p = None):
        if not self.__paused:
            logger.debug('Pausing worker process')
            self.__paused = True
            self.__pipes['LOG'].send(Message("PAUSE"))

    def resume(self, p = None):
        if self.__paused:
            logger.debug('Resuming worker process')
            self.__paused = False
            self.__pipes['LOG'].send(Message("RESUME"))

    def getstatus(self, p = None):
        #returns a dict of que status
        d = dict()
        d['Name'] = self.name
        d['Frequency'] = self.__frequency
        d['Running'] = self.__running
        d['Paused'] = self.__paused
        d['Connected'] = self.__isConnected()
        if self.__isConnected():                                            #todo: uncomment after testing
            d['Interface'] = self.__interface.status()
            d['Supported Commands'] = self.__supported_commands
        d['Que Length'] = self.__workQue.qsize()
        d['Max Que Length'] = self.__maxQueLength
        d['Poll Count'] = self.__pollCount
        d['Poll Rate'] = self.__pollRate
        d['Pid'] = self.__pid
        return Message('WORKERSTATUS', STATUS = d)

    def stop(self, p = None):
        logger.info('Stopping worker process')
        self.__running = False

    def __connect(self):
        #self.__interface = obd.OBD('/dev/' + self.__port, self.__baud)
        #logger.info('Worker connection status = {}'.format(self.__interface.status()))
        logger.info('Worker connection status = Fake OBD')
        self.__supported_commands = []
        #if self.__interface.status() == 'Not Connected': sleep(1)
        #if self.__interface.status() == 'Car Connected':
        #    for c in self.__interface.supported_commands:
        #        if c.mode == 1 and c.name[:4] != 'PIDS':
        #            self.__supported_commands.append(c.name)
        # TODO - Delete after testing
        self.__supported_commands.append('RPM')
        self.__supported_commands.append('SPEED')
        self.__supported_commands.append('MAF')
        self.__supported_commands.append('BAROMETRIC_PRESSURE')
        self.__supported_commands.append('COOLANT_TEMP')
        self.__supported_commands.append('INTAKE_PRESSURE')
        self.__supported_commands.append('DISTANCE_SINCE_DTC_CLEAR')
        self.__supported_commands.append('DISTANCE_W_MIL')
        self.__supported_commands.append('WARMUPS_SINCE_DTC_CLEAR')
        self.__supported_commands.append('ENGINE_LOAD')
        self.__supported_commands.append('EGR_ERROR')
        self.__supported_commands.append('COMMANDED_EGR')
        self.__supported_commands.append('FUEL_RAIL_PRESSURE_DIRECT')
        self.__supported_commands.append('CONTROL_MODULE_VOLTAGE')
        self.__supported_commands.append('AMBIANT_AIR_TEMP')
        self.__supported_commands.append('INTAKE_TEMP')

    def __isConnected(self):
        #connected = False    # TODO: uncomment after testing
        connected = True      # TODO: comment after testing
        self.resume()       # TODO: comment after testing
        # TODO - uncomment after testing
        #if self.__interface is not None:
        #    if self.__interface.status() == 'Car Connected':
        #        connected = True
        #        self.resume()
        #    else:
        #        self.pause()
        #self.__connected = True                             # TODO - Delete after testing
        if self.__connected != connected:
            #Connection status has changed
            logger.info('Connection status has chnged from {} to {}'.format(self.__connected, connected))
            self.__connected = connected
            self.__pipes['ECU'].send(Message('CONNECTION', STATUS = self.__connected))
        return self.__connected

