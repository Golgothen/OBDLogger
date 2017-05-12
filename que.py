import os, logging, sys
from threading import Thread
from multiprocessing import Queue
from datetime import datetime
from time import sleep
#from copy import copy
#from general import *

logger = logging.getLogger('root').getChild(__name__)

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
        self.pauseReady = False
        self.daemon=True
        self.name=name
        self.deleteAfterPoll = False
        logger.debug('Que {} declared'.format(self.name))


    def run(self):
        self.running = True
        self.__lastPolled = datetime.now()
        logger.info('Que {} starting'.format(self.name))
        try:
            while self.running:
                self.__lastPolled = datetime.now()
                if self.ready and not self.paused:
                    self.pauseReady = False
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
                    if self.paused:
                        self.pauseReady = True
                    sleep(0.5)
            logger.info('Que {} stopped'.format(self.name))
        except (KeyboarInterrupt, SystemExit):
            self.running = False
        except:
            logger.critical('Unhandled exception occured in Queue Thread {}: {}'.format(self.name, sys.exc_info))


    def setFrequency(self, frequency):
        self.__frequency = frequency

    def addCommand(self, command, override):
        logger.info('Appending command {} to que {}'.format(command, self.name))
        self.paused = True                         # Pause the que when making changes
        while not self.pauseReady:                 # Wait for pause ready flag to ensure dict will not be accessed
            sleep(0.01)
        self.__commands[command]=override
        self.ready = True
        self.paused=False                          # Resume que after update

    def getCommands(self):
        l = []
        for c in self.__commands:
            l.append(c)
        return l

    def removeCommand(self, command):
        logger.debug('Removing sensor {} from que {}'.format(command, self.name))
        if command in self.__commands:
            del self.__commands[command]
            if len(self.__commands)==0:
                self.ready=False
                logger.info('Que {} not ready due to zero length'.format(self.name))

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
