import logging
logger = logging.getLogger(__name__)

import os, sys
from threading import Thread
from multiprocessing import Queue, Event
from datetime import datetime
from time import sleep
from general import *


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
        self.pauseEvent = Event()
        self.resumeEvent = Event()
        self.readyEvent = Event()
        self.daemon=True
        self.name=name
        self.deleteAfterPoll = False
        logger.debug('Que {} declared'.format(self.name))


    def run(self):
        self.running = True
        self.__lastPolled = datetime.now()
        logger.info('Que {} starting'.format(self.name))
        while self.running:
            try:
                self.__lastPolled = datetime.now()
                if not self.ready:
                    logger.debug('Not Ready on thread {}'.format(self.name))
                    self.readyEvent.wait()
                    self.readyEvent.clear()
                    logger.debug('Ready on thread {}'.format(self.name))
                if not self.paused:
                    for s in self.__commands:
                        logger.debug('Que {} adding command {} to output queue'.format(self.name, s))
                        self.__que.put(s)
                        if self.deleteAfterPoll:
                            self.removeCommand(s)
                            break
                        if len(self.__commands)>0:
                            sleep(1.0/self.__frequency/len(self.__commands))
                        else:
                            sleep(1.0/self.__frequency)
                else:
                    logger.debug('Pausing thread {}'.format(self.name))
                    self.pauseEvent.set()
                    self.resumeEvent.wait()
                    self.resumeEvent.clear()
                    logger.debug('Resuming thread {}'.format(self.name))
            except (KeyboardInterrupt, SystemExit):
                self.running = False
                continue
            except:
                logger.critical('Exception caught in Queue Thread {}:'.format(self.name), exc_info = True, stack_info = True)
                continue
        logger.info('Que {} stopped'.format(self.name))


    def setFrequency(self, frequency):
        self.__frequency = frequency

    def addCommand(self, command, override = False):
        logger.info('Appending command {} to que {}'.format(command, self.name))
        pausedState = self.paused
        if not self.paused:
            self.paused = True                         # Pause the que when making changes
            if self.ready:
                self.pauseEvent.wait()                      # Wait for pauseWait event to ensure dict will not be accessed
                self.pauseEvent.clear()
        self.__commands[command]=override
        if not self.ready:
            self.readyEvent.set()
        self.ready = True
        if not pausedState:
            self.paused=False                          # Resume que after update
        self.resumeEvent.set()

    def getCommands(self):
        l = []
        for c in self.__commands:
            l.append(c)
        return l

    def removeCommand(self, command):
        logger.debug('Removing sensor {} from que {}'.format(command, self.name))
        self.paused = True
        self.pauseEvent.wait()
        self.pauseEvent.clear()
        if command in self.__commands:
            del self.__commands[command]
            if len(self.__commands)==0:
                self.ready=False
                logger.info('Que {} not ready due to zero length'.format(self.name))
        self.paused = False
        self.resumeEvent.set()

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
