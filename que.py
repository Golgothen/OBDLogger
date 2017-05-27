import logging
logger = logging.getLogger(__name__)

import os, sys
from threading import Thread
from multiprocessing import Queue, Event
from datetime import datetime
from time import sleep, time
from general import *


class Que(Thread):

    def __init__(self, name, frequency, que):
        super(Que,self).__init__()
        self.__commands = dict()
        self.running = False
        self.__frequency = frequency
        self.__que = que
        self.__ready = False
        self.__paused = True
        self.pauseEvent = Event()
        self.resumeEvent = Event()
        self.__readyEvent = Event()
        self.daemon=True
        self.name=name
        self.deleteAfterPoll = False
        logger.debug('Que {} declared'.format(self.name))


    def run(self):
        self.running = True
        logger.info('Que {} starting'.format(self.name))
        while self.running:
            try:
                if not self.__ready:
                    logger.debug('Not Ready on thread {}'.format(self.name))
                    self.__readyEvent.wait()
                    self.__readyEvent.clear()
                    logger.debug('Ready on thread {}'.format(self.name))
                logger.debug('Que {} paused state = {}'.format(self.name, self.__paused))
                if not self.__paused:
                    for s in self.__commands:
                        lastPolled = time()
                        logger.debug('Que {} adding command {} to output queue'.format(self.name, s))
                        self.__que.put(s)
                        if self.deleteAfterPoll:
                            self.removeCommand(s)
                            break
                        time_elapsed = time() - lastPolled
                        sleeptime = (1.0 / self.__frequency / len(self.__commands)) - time_elapsed
                        sleep(sleeptime)
                else:
                    logger.debug('Pausing thread {}'.format(self.name))
                    self.pauseEvent.set()
                    self.resumeEvent.wait()
                    self.resumeEvent.clear()
                    logger.debug('Resuming thread {}'.format(self.name))
            except (KeyboardInterrupt, SystemExit):
                self.running = False
                continue
            except (RuntimeError):
                continue
            except:
                logger.critical('Exception caught in Queue Thread {}:'.format(self.name), exc_info = True, stack_info = True)
                continue
        logger.info('Que {} stopped'.format(self.name))


    def setFrequency(self, frequency):
        self.__frequency = frequency

    def addCommand(self, command, override = False):
        logger.info('Appending command {} to que {}'.format(command, self.name))
        pausedState = self.__paused
        if not self.__paused:
            self.__paused = True                         # Pause the que when making changes
            if self.__ready:
                logger.debug('Waiting for main loop to stop on que {}'.format(self.name))
                self.pauseEvent.wait()                      # Wait for pauseWait event to ensure dict will not be accessed
                self.pauseEvent.clear()
        logger.debug('Main loop stopped on que {}'.format(self.name))
        self.__commands[command]=override
        if not self.__ready:
            self.__readyEvent.set()
        self.__ready = True
        if not pausedState:
            self.__paused=False                          # Resume que after update
        self.resumeEvent.set()
        logger.debug('Resuming main loop on que {}'.format(self.name))

    def getCommands(self):
        l = []
        for c in self.__commands:
            l.append(c)
        return l

    def removeCommand(self, command):
        logger.debug('Removing sensor {} from que {}'.format(command, self.name))
        pausedState = self.__paused
        if not self.__paused:
            self.__paused = True
            if self.__ready:
                logger.debug('Waiting for main loop to stop on que {}'.format(self.name))
                self.pauseEvent.wait()
                self.pauseEvent.clear()
        logger.debug('Main loop stopped on que {}'.format(self.name))
        if command in self.__commands:
            del self.__commands[command]
            if len(self.__commands)==0:
                self.__ready=False
                logger.info('Que {} not ready due to zero length'.format(self.name))
        if not pausedState:
            self.__paused = False
        self.resumeEvent.set()
        logger.debug('Resuming main loop on que {}'.format(self.name))

    def status(self):
        #returns a dict of que status
        d = dict()
        d['Name']=self.name
        d['Frequency']=self.__frequency
        d['Running']=self.running
        d['Ready']=self.__ready
        d['Paused']=self.__paused
        d['Length']=len(self.__commands)
        return d

    def pause(self):
        self.__paused = True

    def resume(self):
        self.__paused = False
        self.resumeEvent.set()
