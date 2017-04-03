from multiprocessing import Process, Queue, Pipe
from datetime import datetime
from time import sleep
from messages import Message

import logging, os, obd #, _thread

logger = logging.getLogger('root')

PIPE_TIMEOUT = 3

class Worker(Process):

  def __init__(self, 
               workQue, 
               resultQue, 
               ecuPipe, 
               controlPipe, 
               dataPipe,
               port,
               baud):

    super(Worker,self).__init__()
    #self.daemon=False
    self.name='WORKER'
    self.__frequency = 50
    self.__running = False
    self.__paused = True
    self.__pollCount = 0.0
    self.__pollRate = 0.0
    self.__workQue = workQue       #Message queue object
    self.__resultQue = resultQue
    self.__firstPoll = None
    self.__pid = None
    self.__ecuPipe = ecuPipe
    self.__controlPipe = controlPipe
    self.__dataPipe = dataPipe
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

    logger.debug("Worker process initalised")
    self.__checkPipe()
    #get the interface from the ECU
    #if self.__interface is None:
    #  self.__ecuPipe.send(Message("INTERFACE"))

  def run(self):
    self.__running = True
    self.__pid = os.getpid()
    logger.info('Worker process running')
    try:
      while self.__running:
        self.__checkPipe()
        if not self.__isConnected():
          self.__paused = True
          self.__connect()
        else:
          if not self.__paused and self.__running:
            while self.__workQue.qsize() > 0:
              if self.__workQue.qsize() > self.__maxQueLength: self.__maxQueLength = self.__workQue.qsize() 
              m = self.__workQue.get()
              q=self.__interface.query(obd.commands[m])                           #todo: uncomment after testing
              self.__pollCount+=1
              if self.__firstPoll is None: self.__firstPoll = datetime.now()
              if not q.is_null():                                                 #todo: uncomment after testing
                self.__resultQue.put(Message(m, VALUE=q.value.magnitude))
            self.__pollRate = self.__pollCount / (datetime.now()-self.__firstPoll).total_seconds()
        sleep(1.0/self.__frequency)

      logger.info('Worker process stopping')
      return
    except (KeyboardInterrupt, SystemExit):
      self.__running = False
      return

  def __checkPipe(self):
    # Check for commands comming from the ECU process
    while self.__ecuPipe.poll():
      m = self.__ecuPipe.recv()
      logger.info("Received " + str(m.message) + " from ECU")
      if m.message == "STOP":         self.__stop()
      if m.message == "PAUSE":        self.__pause()
      if m.message == "RESUME":       self.__resume()

    # Check for commands comming from the Application
    while self.__controlPipe.poll():
      m = self.__controlPipe.recv()
      logger.info("Received " + str(m.message) + " from Controller")

      if m.message == "STOP"              : self.__stop()
      if m.message == "PAUSE"             : self.__pause()
      if m.message == "RESUME"            : self.__resume()
      if m.message == "COMMANDS"          : self.__controlPipe.send(Message(m.message, COMMANDS=self.__commands))
      if m.message == "SUPPORTED_COMMANDS": self.__controlPipe.send(Message(m.message,SUPPORTED_COMMANDS=self.__supported_commands))
      if m.message == "CONNECTED"         : self.__controlPipe.send(Message(m.message,STATUS=self.__isConnected()))
      if m.message == "STATUS"            : self.__controlPipe.send(Message(m.message,STATUS=self.__status()))

    while self.__dataPipe.poll():
      m = self.__dataPipe.recv()
      logger.info("Received " + str(m.message) + " from Collector")

      if m.message == "SUPPORTED_COMMANDS": self.__dataPipe.send(Message(m.message,SUPPORTED_COMMANDS=self.__supported_commands))

  def __isConnected(self):
    connected = False
    if self.__interface is not None:
      if self.__interface.status() == 'Car Connected':
        connected = True
    if self.__connected != connected:
      #Connection status has changed
      self.__connected = connected
      self.__ecuPipe.send(Message("CONNECTION", STATUS = self.__connected))
    return self.__connected

  def __pause(self):
    if not self.__paused:
      logger.info('Pausing worker process')
      self.__paused=True

  def __resume(self):
    if self.__paused:
      logger.info("Resuming worker process")
      self.__paused = False

  def __connect(self):
    self.__interface=obd.OBD(self.__port, self.__baud)
    logger.info("Worker connection status = " + self.__interface.status())
    self.__supported_commands = []
    if self.__interface.status() == 'Not Connected': sleep(1)
    if self.__interface.status() == 'Car Connected':
      for c in self.__interface.supported_commands:
        if c.mode == 1 and c.name[:4] != 'PIDS':
          self.__supported_commands.append(c.name)

  def __status(self):
    #returns a dict of que status
    d = dict()
    d['Name']=self.name
    d['Frequency']=self.__frequency
    d['Running']=self.__running
    d['Paused']=self.__paused
    d['Connected']=self.__isConnected()
    if self.__isConnected():                      #todo: uncomment after testing
      d['Interface']=self.__interface.status()
      d['Supported Commands']=self.__supported_commands
    d['Que Length']=self.__workQue.qsize()
    d['Max Que Length']=self.__maxQueLength
    d['Poll Count']=self.__pollCount
    d['Poll Rate']=self.__pollRate
    d['Pid'] = self.__pid
    return d

  def __stop(self):
    logger.debug("Stopping worker process")
    self.__running = False

