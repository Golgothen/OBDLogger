import logging
logger = logging.getLogger(__name__)

from multiprocessing import Process, Event
from time import time, sleep
from datetime import datetime
from messages import Message, PipeCont
from pipewatcher import PipeWatcher
from configparser import ConfigParser
import threading, gzip, shutil, traceback, os

from general import *

class DataLogger(Process):

    def __init__(self,
                 controlPipe,
                 dataPipe,
                 workerPipe):

        super(DataLogger, self).__init__()
        #threading.Thread.__init__(self)
        self.__logName = None                       # File to log to
        self.__logFrequency = 1                     # Time per second to write to the log file
        self.__logHeadings = []                     # List of headings for the log file.
        self.__running = False                      # Internal running flag
        self.__paused = True                        # Internal paused flag
        self.__logPath = './'                       # Path for logfile. Default to current directory
        self.deamon=True                            # Sets the process to daemon. Stops if the parent process stops
        self.name='Logger'                          # Sets the process name. Helps with debigging.
        self.__pipes = {}
        self.__pipes['APPLICATION'] = PipeWatcher(self, controlPipe, 'APP->LOGGER')            # Communication pipe with the controlling application
        self.__pipes['DATA'] = PipeWatcher(self, dataPipe, 'COLLECTOR->LOGGER')                  # Comminication pipe with the Data Collector process
        self.__pipes['WORKER'] = PipeWatcher(self, workerPipe, 'WORKER->LOGGER')              # Comminication pipe with the Data Collector process
        self.__data = dict()                        # Data dictionary to use to write log diles
        self.__refreshRequired = True               # Flag to determine if the dictionary needs to be refreshed
        self.__refreshRequested = False             # Flag to determine if the refresh request has been sent
        self.__logFormat = '%Y%m%d%H%M'             # Log file name format
        self.__pauseLog = False                     # Flag to pause logging
        self.__pid = None                           # Pricess ID of Logging process
        self.__snapshot_ready = Event()

        logger.debug('Logging process initalised')

    def run(self):
        self.__running=True
        logger.info('Starting Logger process on PID {}'.format(self.pid))
        for p in self.__pipes:
            self.__pipes[p].start()
        timer=time()
        while self.__running:
            try:
                if not self.__paused:
                    if self.__logName is None:
                        logger.debug('Logger name not set. Pausing')
                        self.pause()
                    #logger.debug('Running: {}, Paused: {}, Required: {}, Requested: {}'.format(self.__running, self.__paused, self.__refreshRequired, self.__refreshRequested))
                    if self.__refreshRequired:
                        #logger.debug('Getting snapshot')
                        self.__pipes['DATA'].send(Message('SNAPSHOT'))
                        self.__snapshot_ready.wait()
                        self.__snapshot_ready.clear()
                    line=''
                    #logger.debug('Recording data')
                    for l in self.__logHeadings:
                        if l in self.__data:
                            line += str(self.__data[l]['LOG']).strip() + ','
                        else:
                            #logger.debug('{} is not in snapshot'.format(l))
                            line += '-,'
                    with open(self.__logName + '.log','ab') as f:
                        f.write(bytes(line[:len(line)-1]+'\n','UTF-8'))
                    self.__refreshRequired = True
                sleeptime=(1.0 / self.__logFrequency) - (time() - timer)
                if sleeptime < 0:
                    logger.warning('Logger sleep time reached zero. Concider reducing log frequency')
                    #self.logFrequency-=1
                else:
                    sleep(sleeptime)
                timer = time()
            except (KeyboardInterrupt, SystemExit):
                self.__running = False
                continue
            except :
                logger.critical('Unhandled exception occured in Logger process: ', exc_info = True, stack_info = True)
                continue
        logger.info('Logging process stopped')



    def stop(self, p = None):
        #Stop logging.    Thread stops - This is final.    Cannot be restarted
        self.__running=False

    def resume(self, p = None):
        #Resume Logging
        logger.info('Logging resumed')
        self.__paused = self.__pauseLog = False
        if self.__logName is None:
            self.__setName()

    def pause(self, p = None):
        #Pause logging, thread keeps running
        if not self.__paused:
            logger.info('Logging paused')
            self.__paused = True

    def frequency(self, p):
        self.__logFrequency = p['FREQUENCY']

    def logpath(self, p):
        self.__logPath = p['PATH']

    def logname(self, p):
        return Message('LOG_NAME', NAME = self.__logName)

    def snap_shot(self, p):
        self.__data = p['SNAPSHOT']
        self.__refreshRequired = False
        self.__snapshot_ready.set()

    def __setName(self):
        if self.__logHeadings == []:
            logger.warning('No column headings have been set.    No log file started.')
        else:
            self.__logName=(self.__logPath + datetime.now().strftime(self.__logFormat))
            logger.info('Logging started - output: {}.log'.format(self.__logName))
            line=''
            for l in self.__logHeadings:
                line+=l+','
            with open(self.__logName + '.log','wb') as f:        # Clobber output file if it exists
                f.write(bytes(line[:len(line)-1]+'\n','UTF-8'))

#    def headings(self, p):
#        #Set the log headings
#        self.__logHeadings = p['HEADINGS']

    def save(self, p = None):
        #Compress the logfile
        if not self.__paused:
            self.pause()
        if self.__logName is None:
            return
        try:
            with open(self.__logName + '.log', 'rb') as f:
                with gzip.open(self.__logName + '.log.gz', 'wb') as z:
                    shutil.copyfileobj(f, z)
            os.remove(self.__logName + '.log')
            self.__logName = None
        except:
            logger.error('Error compressing log file {}'.format(self.__logName), exc_info = True)
            self.__logName = None

    def discard(self, p = None):
        #Delete the logfile
        if self.__paused:
            self.__paused = True
        try:
            logger.debug('Discarding log file {}.log'.format(self.__logName))
            os.remove(self.__logName + '.log')
        except:
            logger.warning('Could not delete log file {}.log'.format(self.__logname), exc_info = True)
        self.__logName = None

    def getstatus(self, p = None):
        d = dict()
        d['Running'] = self.__running
        d['Paused'] = self.__paused
        d['Log Name'] = self.__logName
        d['Frequency'] = self.__logFrequency
        d['Log Path'] = self.__logPath
        d['Headings'] = self.__logHeadings
        return Message('LOGSTATUS', STATUS = d)

    def add_headings(self, p):
        insert = False
        if 'INSERT' in p:
            insert = p['INSERT']
        for a in range(len(p['HEADINGS'])):
            if p['HEADINGS'][a] not in self.__logHeadings:
                if insert:
                    self.__logHeadings.insert(a, p['HEADINGS'][a])
                else:
                    self.__logHeadings.append(p['HEADINGS'][a])
        logger.info('Log headings updated to {}'.format(self.__logHeadings))

    def remove_headings(self, p):
        for h in p['HEADINGS']:
            if h in self.__logHeadings:
                self.__logHeadings.remove(h)
        logger.info('Log headings updated to {}'.format(self.__logHeadings))

