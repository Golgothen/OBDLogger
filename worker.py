from multiprocessing import Process, Queue, Pipe
from datetime import datetime
from time import sleep
from messages import Message
from pipewatcher import PipeWatcher

from general import *
import logging, os, obd #, _thread

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
                 logPipe,                        # Worker <-> Logger
                 port,
                 baud):

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
        self.__pipes['ECU'] = PipeWatcher(self, ecuPipe, 'WORKER.ECU')
        self.__pipes['APPLICATION'] = PipeWatcher(self, controlPipe, 'WORKER.APPLICATION')
        self.__pipes['DATA'] = PipeWatcher(self, dataPipe, 'WORKER.DATA')
        self.__pipes['LOG'] = PipeWatcher(self, logPipe, 'WORKER.LOG')
        self.__baud = baud
        self.__port = port
        self.__interface = obd.OBD(port, baud)
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
                            q = self.__interface.query(obd.commands[m])                                                    # todo: uncomment after testing
                            self.__pollCount+=1
                            if self.__firstPoll is None:
                                self.__firstPoll = datetime.now()
                            if not q.is_null():                                                                            # todo: uncomment after testing
                                logger.debug('{} - {}'.format(m, q.value))
                                self.__resultQue.put(Message(m, VALUE=q.value.magnitude))
                            #self.__resultQue.put(Message(m, VALUE = 0.0))                                                 # todo: delete after testing
                        self.__pollRate = self.__pollCount / (datetime.now() - self.__firstPoll).total_seconds()
                sleep(1.0 / self.__frequency)

            logger.info('Worker process stopping')
            return
        except (KeyboardInterrupt, SystemExit):
            self.__running = False
            return

    def commands(self, p = None):
        return Message('COMMANDS', COMMANDS = self.__commands)

    def supported_commands(self, p = None):
        return Message('SUPPORTED_COMMANDS', SUPPORTED_COMMANDS = self.__supported_commands)

    def connected(self, p = None):
        return Message('CONNECTED', STATUS = self.__isConnected())

    def pause(self, p = None):
        if not self.__paused:
            logger.debug('Pausing worker process')
            self.__paused = True
            self.__logPipe.send(Message("PAUSE"))

    def resume(self, p = None):
        if self.__paused:
            logger.debug('Resuming worker process')
            self.__paused = False
            self.__logPipe.send(Message("RESUME"))

    def status(self, p = None):
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
        return Message('STATUS', STATUS = d)

    def stop(self, p = None):
        logger.info('Stopping worker process')
        self.__running = False

    def __connect(self):
        self.__interface = obd.OBD(self.__port, self.__baud)
        logger.info('Worker connection status = {}'.format(self.__interface.status()))
        self.__supported_commands = []
        #if self.__interface.status() == 'Not Connected': sleep(1)
        if self.__interface.status() == 'Car Connected':
            for c in self.__interface.supported_commands:
                if c.mode == 1 and c.name[:4] != 'PIDS':
                    self.__supported_commands.append(c.name)
        # TODO - Delete after testing
        #self.__supported_commands.append('RPM')
        ##self.__supported_commands.append('SPEED')
        #self.__supported_commands.append('MAF')
        #self.__supported_commands.append('BAROMETRIC_PRESSURE')
        #self.__supported_commands.append('COOLANT_TEMP')
        #self.__supported_commands.append('INTAKE_PRESSURE')
        #self.__supported_commands.append('DISTANCE_SINCE_DTC_CLEAR')
        #self.__supported_commands.append('DISTANCE_W_MIL')
        #self.__supported_commands.append('WARMUPS_SINCE_DTC_CLEAR')
        #self.__supported_commands.append('ENGINE_LOAD')
        #self.__supported_commands.append('EGR_ERROR')
        #self.__supported_commands.append('COMMANDED_EGR')

    def __isConnected(self):
        connected = False    # TODO: delete after testing
        #connected = True
        #self.__resume()
        # TODO - uncomment after testing
        if self.__interface is not None:
            if self.__interface.status() == 'Car Connected':
                connected = True
                self.resume()
            else:
                self.pause()
                self.__interface.close()
        #self.__connected = True                             # TODO - Delete after testing
        if self.__connected != connected:
            #Connection status has changed
            logger.info('Connection status has chnged from {} to {}'.format(self.__connected, connected))
            self.__connected = connected
            self.__ecuPipe.send(Message('CONNECTION', STATUS = self.__connected))
        return self.__connected

