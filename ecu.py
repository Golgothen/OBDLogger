import os, _thread
from time import sleep
from worker import Worker
from que import Que
from multiprocessing import Process, Queue, Pipe
from messages import Message
from pipewatcher import PipeWatcher

from general import *

config = loadConfig()
PIPE_TIMEOUT = config.getfloat('Application','Pipe Timeout')

import logging

logger = logging.getLogger('root')

class ECU(Process):

    def __init__(self, que, workerPipe, controlPipe, dataPipe):

        super(ECU,self).__init__()                     # Initalise the new process
        self.__Que = dict()
        self.__workerQue = que                         # Work que that all que threads submit their commands to
        self.__pid = None
        self.__pipes = {}
        self.__pipes['WORKER'] = PipeWatcher(self, workerPipe, 'ECU.WORKER')                          # Communication pipe to the worker process
        self.__pipes['APPLICATION'] = PipeWatcher(self, controlPipe, 'ECU.APPLICATION')                         # Communication pipe to the controlling process
        self.__pipes['DATA'] = PipeWatcher(self, dataPipe, 'ECU.DATA')                            # Communication pipe to the collector process
        self.__paused = True
        self.__name = 'ECU'
        self.__running = False

    def run(self):
        self.__running = True
        self.__pid = os.getpid()
        logger.info('Starting ECU process on PID {}'.format(self.__pid))
        for p in self.__pipes:
            self.__pipes[p].start()
        try:
            while self.__running:
                for q in self.__Que:
                    self.__Que[q].paused = self.__paused
                sleep(0.1)
            self.__shutdown()
        except (KeyboardInterrupt, SystemExit):
            self.__shutdown()

    def supported_commands(self, p = None):
        return Message('SUPPORTED_COMMANDS', SUPPORTED_COMMANDS = self.__supportedcommands)

    def connection(self, p):
        if p['STATUS']:
            self.resume()
        else:
            self.pause()

    def __shutdown(self):
        logger.info('Stopping ECU process')
        self.__running = False
        for q in self.__Que:
            logger.info('Stopping Que {}'.format(q))
            self.__Que[q].running = False
            logger.debug('Stop Wait Que {}'.format(q))
            _thread.start_new_thread(self.__Que[q].join,())
        logger.info('ECU Stopped')
        self.__pipes['WORKER'].send(Message('STOP'))
        self.__pipes['DATA'].send(Message('STOP'))

    def addque(self, p):
        #Adds a que to the ECU.
        if p['QUE'] in self.__Que:
            logger.debug('Que {} already exists'.format(p['QUE']))
            return
        self.__Que[p['QUE']] = Que(p['QUE'], p['FREQUENCY'], self.__workerQue)
        if self.__running:
            logger.info('Starting Que {}'.format(p['QUE']))
            self.__Que[p['QUE']].start()

    def getqueues(self, p = None):
        #Returns a list of que names
        queues = []
        for q in self.__Que:
            queues.append(q)
        return Message('GETQUEUES', QUEUES = queues)

    def getcommands(self, p):
        return Message('GETCOMMANDS', COMMANDS = self.__Que[p['QUE']].getCommands())

    def status(self, p = None):
        d = dict()
        d['PID'] = self.__pid
        d['Running'] = self.__running
        d['Paused'] = self.__paused
        for q in self.__Que:
            if self.__Que[q] is not None:
                d['Que: ' + q] = self.__Que[q].status()
        return Message('STATUS', STATUS = d)

    def addcommand(self, p):
        #Append a command to a given que
        if p['QUE'] in self.__Que:
            self.__Que[p['QUE']].addCommand(p['COMMAND'], p['OVERRIDE'])

    def removecommand(self, p):
        #Remove a command to a given que
        if que in self.__Que:
            self.__Que[p['QUE']].removeCommand(p['COMMAND'])

    def setfrequency(self, p):
        logger.debug('Setting que {} frequency to {}'.format(p['QUE'], p['FREQUENCY']))
        self.__Que[p['QUE']].setFrequency(p['FREQUENCY'])

    def stop(self, p = None):
        self.__shutdown()

    def pause(self, p = None):
        if not self.__paused:
            logger.info('Pausing ECU')
            self.__paused = True
            for q in self.__Que:
                if self.__Que[q].isAlive(): self.__Que[q].paused = True

    def resume(self, p = None):
        logger.info('Resuming ECU')
        self.__pipes['DATA'].send(Message('RESUME'))
        self.__paused = False
        for q in self.__Que:
            if self.__Que[q].isAlive(): self.__Que[q].paused = False

    def deleteafterpoll(self, p):
        self.__Que[p['QUE']].deleteAfterPoll = p['FLAG']
