from multiprocessing import Process, Queue, Pipe
from datetime import datetime
from time import sleep
from messages import Message
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
        self.__ecuPipe = ecuPipe
        self.__controlPipe = controlPipe
        self.__dataPipe = dataPipe
        self.__logPipe = logPipe
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
        self.__checkPipe()

    def run(self):
        self.__running = True
        self.__pid = os.getpid()
        logger.info('Starting Worker process on PID {}'.format(self.__pid))
        try:
            while self.__running:
                self.__checkPipe()
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

    def __checkPipe(self):
        # Check for commands comming from the ECU process
        while self.__ecuPipe.poll():
            m = self.__ecuPipe.recv()
            logger.info('Received {} on ECU pipe'.format(m.message))

            if m.message == 'STOP'                : self.__stop()
            if m.message == 'PAUSE'               : self.__pause()
            if m.message == 'RESUME'              : self.__resume()

        # Check for commands comming from the Application
        while self.__controlPipe.poll():
            m = self.__controlPipe.recv()
            logger.info('Received {} on Controller pipe'.format(m.message))

            if m.message == 'STOP'                : self.__stop()
            if m.message == 'PAUSE'               : self.__pause()
            if m.message == 'RESUME'              : self.__resume()
            if m.message == 'COMMANDS'            : self.__controlPipe.send(Message(m.message, COMMANDS = self.__commands))
            if m.message == 'SUPPORTED_COMMANDS'  : self.__controlPipe.send(Message(m.message, SUPPORTED_COMMANDS = self.__supported_commands))
            if m.message == 'CONNECTED'           : self.__controlPipe.send(Message(m.message, STATUS = self.__isConnected()))
            if m.message == 'STATUS'              : self.__controlPipe.send(Message(m.message, STATUS = self.__status()))

        while self.__dataPipe.poll():
            m = self.__dataPipe.recv()
            logger.info('Received {} on Collector pipe'.format(m.message))

            if m.message == 'SUPPORTED_COMMANDS'  : self.__dataPipe.send(Message(m.message,SUPPORTED_COMMANDS = self.__supported_commands))

    def __isConnected(self):
        connected = False    # TODO: delete after testing
        #connected = True
        #self.__resume()
        # TODO - uncomment after testing
        if self.__interface is not None:
            if self.__interface.status() == 'Car Connected':
                connected = True
                self.__resume()
            else:
                self.__pause()
                self.__interface.close()
        #self.__connected = True                             # TODO - Delete after testing
        if self.__connected != connected:
            #Connection status has changed
            logger.info('Connection status has chnged from {} to {}'.format(self.__connected, connected))
            self.__connected = connected
            self.__ecuPipe.send(Message('CONNECTION', STATUS = self.__connected))
        return self.__connected

    def __pause(self):
        if not self.__paused:
            logger.debug('Pausing worker process')
            self.__paused = True
            self.__logPipe.send(Message("PAUSE"))

    def __resume(self):
        if self.__paused:
            logger.debug('Resuming worker process')
            self.__paused = False
            self.__logPipe.send(Message("RESUME"))

    def __connect(self):
        self.__interface = obd.OBD(self.__port, self.__baud)
        logger.info('Worker connection status = {}'.format(self.__interface.status()))
        self.__supported_commands = []
        if self.__interface.status() == 'Not Connected': sleep(1)
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

    def __status(self):
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
        return d

    def __stop(self):
        logger.info('Stopping worker process')
        self.__running = False

