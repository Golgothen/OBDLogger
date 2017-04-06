from multiprocessing import Queue #, Manager
#from threading import Thread
from ecu import ECU
from worker import Worker
from collector import Collector
from que import Que	
from logger import DataLogger
from messages import Message, PipeCont
from time import sleep

import sys, logging

logger = logging.getLogger('root')

PIPE_TIMEOUT = 3

class Monitor():

  def __init__(self, port, baud):
    #super(Monitor,self).__init__()
    ecuWorkerPipe = PipeCont()        # ECU <-> Worker
    ecuDataPipe = PipeCont()          # ECU <-> Collector
    ecuControlPipe = PipeCont()       # ECU <-> Application
    workerDataPipe = PipeCont()       # Worker <-> Collector
    workerControlPipe = PipeCont()    # Worker <-> Application
    collectorControlPipe = PipeCont() # Collector <-> Application
    loggerControlPipe = PipeCont()    # Logger <-> Application
    loggerDataPipe = PipeCont()       # Logger <-> Collector
    loggerWorkerPipe = PipeCont()     # Logger <-> Worker

    workQue = Queue()
    resultQue = Queue()
    self.__ecuComm = ecuControlPipe.s
    self.__workerComm = workerControlPipe.s
    self.__dataComm = collectorControlPipe.s
    self.__logComm = loggerControlPipe.s

    self.__ecu = ECU(workQue,
                     ecuWorkerPipe.s,                    # ECU <-> Worker
                     ecuControlPipe.r,                   # ECU <-> Application
                     ecuDataPipe.s)                      # ECU <-> Collector

    self.__worker = Worker(workQue,
                           resultQue,
                           ecuWorkerPipe.r,              # Worker <-> ECU
                           workerControlPipe.r,          # Worker <-> Application
                           workerDataPipe.s,             # Worker <-> Collector
                           loggerWorkerPipe.s,           # Worker <-> Logger
                           port,
                           baud)

    self.__collector = Collector(ecuDataPipe.r,          # Collector <-> ECU
                                 collectorControlPipe.r, # Collector <-> Application
                                 loggerDataPipe.r,       # Collector <-> Logger
                                 workerDataPipe.r,       # Collector <-> Worker
                                 resultQue)

    self.__logger = DataLogger(loggerControlPipe.r,      # Logger <-> Application
                               loggerDataPipe.s,         # Logger <-> Collector
                               loggerWorkerPipe.r)       # Logger <-> Worker

    self.__ecu.start()
    self.__worker.start()
    self.__collector.start()
    self.__logger.start()

  def __checkWorkerPipe(self, message, timeout):
    # Check Worker pipe
    while self.__workerComm.poll(timeout):
      m = self.__workerComm.recv()
      logger.info(m.message + ' received on Worker pipe')
      if m.message == message: 
        return m.params
      else:
        logger.info('Discarding out of sync message ' + m.message + '. Expected ' + message)
    return None

  def __checkDataPipe(self, message, timeout):
    # Check Collector pipe
    while self.__dataComm.poll(timeout):
      m = self.__dataComm.recv()
      logger.info(m.message + ' received on Collector pipe')
      if m.message == message: 
        return m.params
      else:
        logger.info('Discarding out of sync message ' + m.message)
    return None

  def __checkECUPipe(self, message, timeout):
    # Check ECU pipe
    while self.__ecuComm.poll(timeout):
      m = self.__ecuComm.recv()
      logger.debug(m.message + ' received on ECU pipe')
      if m.message == message:
        return m.params
      else:
        logger.info('Discarding out of sync message ' + m.message)
    return None

  def __checkLoggerPipe(self, message, timeout):
    # Check Logger pipe
    while self.__logComm.poll(timeout):
      m = self.__logComm.recv()
      logger.debug(m.message + ' received on Logger pipe')
      if m.message == message:
        return m.params
      else:
        logger.info('Discarding out of sync message ' + m.message)
    return None

  def isConnected(self):
    self.__workerComm.send(Message('CONNECTED'))
    r = self.__checkWorkerPipe('CONNECTED',PIPE_TIMEOUT)
    if r is not None:
      return r['STATUS']
    else:
      logger.warning('Worker Timeout requesting connection status')
      return False

  def addQue(self, que, frequency):
    self.__ecuComm.send(Message('ADDQUE',QUE = que, FREQUENCY = frequency))
    logger.debug('Add Que ' + str(que) + ' message sent')

  def getQueues(self):
    self.__ecuComm.send(Message('GETQUEUES'))
    r = self.__checkECUPipe('GETQUEUES',PIPE_TIMEOUT)
    if r is not None:
      return r['QUEUES']
    else:
      logger.warning('ECU Timeout requesting Que List')

  def getQueCommands(self, que):
    self.__ecuComm.send(Message('GETCOMMANDS', QUE = que))
    r = self.__checkECUPipe('GETCOMMANDS',PIPE_TIMEOUT)
    if r is not None:
      return r['COMMANDS']
    else:
      logger.warning('ECU timeout requesting que commands')

  def getInterface(self):
    self.__ecuComm.send(Message('INTERFACE'))
    r = self.__checkECUPipe('INTERFACE',PIPE_TIMEOUT)
    if r is not None:
      return r['INTERFACE']
    else:
      logger.warning('ECU Timeout requesting interface')

  def addCommand(self, que, command, override=False):
    self.__ecuComm.send(Message('ADDCOMMAND',QUE=que, COMMAND=command, OVERRIDE=override))
    logger.debug('Add Command ' + str(command) + ' on que ' + str(que) + ' sent')
  
  def setQueFrequency(self, que, frequency):
    self.__ecuComm.send(Message('SETFREQUENCY',QUE=que, FREQUENCY=frequency))
    logger.debug('Set frequency on que ' + str(que) + ' sent')

  def deleteAfterPoll(self, que, flag):
    self.__ecuComm.send(Message('DELETEAFTERPOLL',QUE=que, FLAG=flag))
    logger.debug('Delete after poll on que ' + str(que) + ' sent')

  def commands(self):
    self.__workerComm.send(Message('COMMANDS'))
    r = self.__checkWorkerPipe('COMMANDS',PIPE_TIMEOUT)
    if r is not None:
      return r['COMMANDS']
    else:
      logger.warning('ECU Timeout requesting commands')

  def supportedcommands(self):
    self.__workerComm.send(Message('SUPPORTED_COMMANDS'))
    r = self.__checkWorkerPipe('SUPPORTED_COMMANDS',PIPE_TIMEOUT)
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

    r = self.__checkWorkerPipe('STATUS',PIPE_TIMEOUT)
    if r is not None:
      d['Worker Status'] = r['STATUS']
    else:
      logger.warning('Worker Timeout requesting status')

    r = self.__checkECUPipe('STATUS',PIPE_TIMEOUT)
    if r is not None:
      d['ECU Status'] = r['STATUS']
    else:
      logger.warning('ECU Timeout requesting status')

    r = self.__checkLoggerPipe('STATUS',PIPE_TIMEOUT)
    if r is not None:
      d['Logger Status'] = r['STATUS']
    else:
      logger.warning('Logger Timeout requesting status')

    r = self.__checkDataPipe('STATUS',PIPE_TIMEOUT)
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
    self.__logComm.send(Message('RESUME'))

  def sum(self, name, offset = 0, length = 0):
    self.__dataComm.send(Message('SUM',NAME = name, OFFSET = offset, LENGTH = length))
    r = self.__checkDataPipe('SUM',PIPE_TIMEOUT)
    if r is not None:
      return r['SUM']

  def avg(self, name, offset = 0, length = 0):
    self.__dataComm.send(Message('AVG',NAME = name, OFFSET = offset, LENGTH = length))
    r = self.__checkDataPipe('AVG',PIPE_TIMEOUT)
    if r is not None:
      return r['AVG']

  def min(self, name):
    self.__dataComm.send(Message('MIN', NAME = name))
    r = self.__checkDataPipe('MIN',PIPE_TIMEOUT)
    if r is not None:
      return r['MIN']

  def max(self, name):
    self.__dataComm.send(Message('MAX',NAME = name))
    r = self.__checkDataPipe('MAX',PIPE_TIMEOUT)
    if r is not None:
      return r['MAX']

  @property
  def snapshot(self):
    self.__dataComm.send(Message('SNAPSHOT'))
    r = self.__checkDataPipe('SNAPSHOT',PIPE_TIMEOUT)
    if r is not None:
      return r['SNAPSHOT']

  def reset(self):
    self.__dataComm.send(Message('RESET'))

  def save(self):
    self.__logComm.send(Message('SAVE'))

  def discard(self):
    self.__logComm.send(Message('DISCARD'))

#  def restart(self):
#    self.__logComm.send(Message('RESTART'))

  def logPath(self, path):
    self.__logComm.send(Message('LOGPATH',PATH = path))

  def logFrequency(self, frequency):
    self.__logComm.send(Message('FREQUENCY', FREQUENCY = frequency))

  def logName(self):
    self.__logComm.send(Message('LOGNAME'))
    r = self.__checkLoggerPipe('LOGNAME',PIPE_TIMEOUT)
    if r is not None:
      return r['NAME']

  def logHeadings(self, headings):
    self.__logComm.send(Message('HEADINGS',HEADINGS = headings))

  def tripTimeout(self, timeout):
    self.__logComm.send(Message('TIMEOUT',TIMEOUT = timeout))

  @property
  def summary(self):
    self.__dataComm.send(Message('SUMMARY'))
    r = self.__checkDataPipe('SUMMARY',PIPE_TIMEOUT)
    if r is not None:
      return r['SUMMARY']

