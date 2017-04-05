import os, logging #, _thread
from threading import Thread
from multiprocessing import Queue
from datetime import datetime
from time import sleep
from copy import copy
#from general import *

logger = logging.getLogger('root')

class Que(Thread):

  def __init__(self, name, frequency, que):
    super(Que,self).__init__()
    self.__lastPolled = None
    self.__commands = dict()
    self.running = False
    self.__frequency = frequency
    self.__que = que
    self.ready = False
    self.paused = True
    self.daemon=True
    self.name=name
    self.deleteAfterPoll = False
    logger.debug('Que ' + self.name + ' declared')


  def run(self):
    self.running = True
    self.__lastPolled = datetime.now()
    logger.info('Que ' + self.name + ' starting')
    while self.running:
      self.__lastPolled = datetime.now()
      if self.ready and not self.paused:
        for s in self.__commands:
          self.__que.put(s)
          if self.deleteAfterPoll:
            self.removeCommand(s)
            break
          if len(self.__commands)>0:
            sleep(1.0/self.__frequency/len(self.__commands))
          else:
            sleep(1.0/self.__frequency)
      else:
        sleep(0.5)
    logger.info('Que ' + self.name + ' stopped')

  def setFrequency(self, frequency):
    self.__frequency = frequency

  def addCommand(self, command, override):
    logger.info('Appending command ' + command + ' to que ' + self.name)
    self.__commands[command]=override
    self.ready = True

  def getCommands(self):
    l = []
    for c in self.__commands:
      l.append(d)
    return l

  def removeCommand(self,command):
    logger.debug('Removing sensor ' + command + ' from que ' + self.name)
    if command in self.__commands:
      del self.__commands[command]
      if len(self.__commands)==0: 
        self.ready=False
        logger.info('Que ' + self.name + ' not ready due to zero length')

  def status(self):
    #returns a dict of que status
    d = dict()
    d['Name']=self.name
    d['Frequency']=self.__frequency
    d['Running']=self.running
    d['Ready']=self.ready
    d['Paused']=self.paused
    d['Length']=len(self.__commands)
    return d
