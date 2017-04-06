import os, _thread
from time import sleep
from worker import Worker
from que import Que
from multiprocessing import Process, Queue, Pipe
from messages import Message

PIPE_TIMEOUT = 3

import logging

logger = logging.getLogger('root')

class ECU(Process):

  def __init__(self, que, p, c, d):

    super(ECU,self).__init__()       # Initalise the new process
    self.__Que = dict()
    self.__workerQue = que           # Work que that all que threads submit their commands to
    self.__pid = None
    self.__workerPipe = p            # Communication pipe to the worker process
    self.__controlPipe = c           # Communication pipe to the controlling process
    self.__dataPipe = d              # Communication pipe to the collector process
    self.__paused = True
    self.__name = 'ECU'
    self.__running = False

  def run(self):
    self.__running = True
    self.__pid = os.getpid()
    logger.info('Starting ECU process on PID ' + str(self.__pid))
    try:    
      while self.__running:
        self.__checkPipe()
        for q in self.__Que:
          self.__Que[q].paused = self.__paused
        sleep(0.1)
      self.__shutdown()
    except (KeyboardInterrupt, SystemExit):
      self.__shutdown()

  def __checkPipe(self):
    # Check commands comming from the controlling process
    while self.__controlPipe.poll():
      m=self.__controlPipe.recv()
      logger.info('Received ' + str(m.message) + ' on controller pipe')

      if m.message == 'PAUSE'          : self.__pause()
      if m.message == 'RESUME'         : self.__resume()
      if m.message == 'STOP'           : self.__stop()
      if m.message == 'CONNECTED'      : self.__controlPipe.send(Message(m.message,CONNECTED = self.__isConnected()))
      if m.message == 'STATUS'         : self.__controlPipe.send(Message(m.message,STATUS = self.__status()))
      if m.message == 'ADDQUE'         : self.__addQue(m.params)
      if m.message == 'GETQUEUES'      : self.__controlPipe.send(Message(m.message,QUEUES = self.__getQueues()))
      if m.message == 'ADDCOMMAND'     : self.__addCommand(m.params)
      if m.message == 'SETFREQUENCY'   : self.__setFrequency(m.params)
      if m.message == 'DELETEAFTERPOLL': self.__deleteAfterPoll(m.params)
      if m.message == 'GETCOMMANDS'    : self.__controlPipe.send(Message(m.message,COMMANDS = self.__getQueCommands(m.params['QUE'])))

    # Check commands comming from the worker process
    while self.__workerPipe.poll():
      m=self.__workerPipe.recv()
      logger.info('Received ' + str(m.message) + ' on worker pipe')

      if m.message == 'CONNECTION':
        if m.params['STATUS']: 
          self.__resume()
        else: 
          self.__pause()

    # Check commands comming from the collector process
    while self.__dataPipe.poll():
      m=self.__dataPipe.recv()
      logger.info('Received ' + str(m.message) + ' on data pipe')

      if m.message == 'SUPPORTED_COMMANDS':    self.__dataPipe.send(          Message(m.message,SUPPORTED_COMMANDS = self.__supportedcommands))

  def __shutdown(self):
    logger.info('Stopping ECU process')
    self.__running = False
    for q in self.__Que:
      logger.info('Stopping Que ' + q)
      self.__Que[q].running = False
      logger.debug('Stop Wait Que ' + q)
      _thread.start_new_thread(self.__Que[q].join,())
    logger.info('ECU Stopped')
    self.__workerPipe.send(Message('STOP'))
    self.__dataPipe.send(Message('STOP'))

  def __addQue(self, p):
    #Adds a que to the ECU.
    if p['QUE'] in self.__Que: 
      logger.debug('Que ' + p['QUE'] +  ' already exists')
      return
    self.__Que[p['QUE']] = Que(p['QUE'], p['FREQUENCY'], self.__workerQue)
    if self.__running:
      logger.info('Starting Que ' + p['QUE'])
      self.__Que[p['QUE']].start()

  def __getQueues(self):
    #Returns a list of que names
    queues = []
    for q in self.__Que:
      queues.append(q)
    return queues

  def __getQueCommands(self, que):
    return self.__Que[que].getCommands()

  def __status(self):
    d = dict()
    d['PID'] = self.__pid
    d['Running'] = self.__running
    d['Paused'] = self.__paused
    for q in self.__Que:
      if self.__Que[q] is not None:
        d['Que: ' + q]  = self.__Que[q].status()
    return d

  def __addCommand(self, p):
    #Append a command to a given que
    if p['QUE'] in self.__Que:
      self.__Que[p['QUE']].addCommand(p['COMMAND'], p['OVERRIDE'])

  def __removeCommand(self,que, cmd):
    #Remove a command to a given que
    if que in self.__Que:
      self.__Que[que].removeCommand(cmd)

  def __setFrequency(self, p):
    logger.debug('Setting que ' + p['QUE'] + ' frequency to ' + str(p['FREQUENCY']))
    self.__Que[p['QUE']].setFrequency(p['FREQUENCY'])

  def __stop(self):
    self.__shutdown()

  def __pause(self):
    if not self.__paused:
      logger.info('Pausing ECU')
      self.__paused = True
      for q in self.__Que:
        if self.__Que[q].isAlive(): self.__Que[q].paused = True

  def __resume(self):
    logger.info('Resuming ECU')
    self.__dataPipe.send(Message('RESUME'))
    self.__paused = False
    for q in self.__Que:
      if self.__Que[q].isAlive(): self.__Que[q].paused = False

  def __deleteAfterPoll(self, p):
    self.__Que[p['QUE']].deleteAfterPoll = p['FLAG']
