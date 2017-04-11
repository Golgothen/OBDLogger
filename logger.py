from multiprocessing import Process
from time import time, sleep
from datetime import datetime
import threading, gzip, shutil, os, logging
from messages import Message, PipeCont

logger = logging.getLogger('root')

class DataLogger(threading.Thread):

    def __init__(self,
                 controlPipe,
                 dataPipe,
                 workerPipe):

        threading.Thread.__init__(self)
        self.__logName = None                       # File to log to
        self.__logFrequency = 1                     # Time per second to write to the log file
        self.__logHeadings = []                     # List of headings for the log file.
        self.__running = False                      # Internal running flag
        self.__paused = True                        # Internal paused flag
        self.__logPath = './'                       # Path for logfile. Default to current directory
        self.deamon=True                            # Sets the process to daemon. Stops if the parent process stops
        self.name='Logger'                          # Sets the process name. Helps with debigging.
        self.__controlPipe = controlPipe            # Communication pipe with the controlling application
        self.__dataPipe = dataPipe                  # Comminication pipe with the Data Collector process
        self.__workerPipe = workerPipe              # Comminication pipe with the Data Collector process
        self.__data = dict()                        # Data dictionary to use to write log diles
        self.__refreshRequired = True               # Flag to determine if the dictionary needs to be refreshed
        self.__refreshRequested = False             # Flag to determine if the refresh request has been sent
        self.__logFormat = '%Y%m%d%H%M'             # Log file name format
        self.__pauseLog = False                     # Flag to pause logging
        self.__pid = None                           # Pricess ID of Logging process

        logger.debug('Logging process initalised')

    def run(self):
        self.__running=True
        self.__pid = os.getpid()
        logger.info('Starting Logger process on PID {}'.format(self.__pid))
        try:
            timer=time()
            while self.__running:
                self.__checkPipe()
                if self.__logName is None:
                    logger.debug('Logger name not set. Pausing')
                    self.__pause()
                logger.debug('Running: {}, Paused: {}, Required: {}, Requested: {}'.format(self.__running, self.__paused, self.__refreshRequired, self.__refreshRequested))
                if not self.__paused:
                    if self.__refreshRequired:
                        if not self.__refreshRequested:
                            logger.debug('Getting snapshot')
                            self.__dataPipe.send(Message('SNAPSHOT'))
                            self.__refreshRequested = True
                        continue
                    line=''
                    logger.debug('Recording data')
                    for l in self.__logHeadings:
                        if l == 'TIMESTAMP':
                            line += str(datetime.now()) + ','
                        else:
                            if l in self.__data:
                                if self.__data[l]['VAL'] is not None:
                                    line += str(self.__data[l]['VAL']) + ','
                                else:
                                    line += '-,'
                                    logger.debug('{} is none'.format(l))
                            else:
                                logger.debug('{} is not in snapshot'.format(l))
                                line += '-,'
                    with open(self.__logName + '.log','ab') as f:
                        f.write(bytes(line[:len(line)-1]+'\n','UTF-8'))
                    self.__refreshRequired = True
                    self.__refreshRequested = False
                sleeptime=(1.0 / self.__logFrequency) - (time() - timer)
                if sleeptime < 0:
                    logger.warning('Logger sleep time reached zero. Concider reducing log frequency')
                    #self.logFrequency-=1
                else:
                    sleep(sleeptime)
                    timer = time()
            logger.info('Logging process stopped')
        except (KeyboardInterrupt, SystemExit):
            self.__running = False
            return

    def __checkPipe(self):
        # Check controller pipe
        logger.debug('Checking Pipes')
        while self.__controlPipe.poll():
            m = self.__controlPipe.recv()
            logger.debug('Received {} on controller pipe'.format(m.message))

            if m.message == 'STOP'        : self.__stop()
            if m.message == 'SAVE'        : self.__save()
            if m.message == 'DISCARD'     : self.__discard()
            if m.message == 'PAUSE'       : self.__pause()
            if m.message == 'RESUME'      : self.__resume()
            if m.message == 'RESET'       : self.__reset()
            if m.message == 'LOGPATH'     : self.__logPath = m.params['PATH']
            if m.message == 'LOGNAME'     : self.__controlPipe.send(Message(m.message,NAME=self.__logName))
            if m.message == 'STATUS'      : self.__controlPipe.send(Message(m.message,STATUS=self.__status()))
            if m.message == 'FREQUENCY'   : self.__logFrequency = m.params['FREQUENCY']
            if m.message == 'HEADINGS'    : 
                self.__colHeadings(m.params['HEADINGS'])
                #self.__restart()

        while self.__workerPipe.poll():
            m = self.__workerPipe.recv()
            logger.debug('Received {} on worker pipe'.format(m.message))

            if m.message == 'PAUSE'       : self.__pause()
            if m.message == 'RESUME'      : self.__resume()


        while self.__dataPipe.poll():
            m = self.__dataPipe.recv()
            logger.debug('Reveived {} on data pipe'.format(m.message))

            if m.message == 'SNAPSHOT':
                self.__data = m.params['DATA']
                self.__refreshRequired = False

    def __setName(self):
        if self.__logHeadings == []:
            logger.warning('No column headings have been set.    No log file started.')
        else:
            self.__logName=(self.__logPath + datetime.now().strftime(self.__logFormat))
            logger.debug('Logging started - output: {}.log'.format(self.__logName))
            line=''
            for l in self.__logHeadings:
                line+=l+','
            with open(self.__logName + '.log','wb') as f:        # Clobber output file if it exists
                f.write(bytes(line[:len(line)-1]+'\n','UTF-8'))

    def __colHeadings(self,headings):
        #Set the log headings
        self.__logHeadings = headings

    def __stop(self):
        #Stop logging.    Thread stops - This is final.    Cannot be restarted
        self.__running=False

    def __resume(self):
        #Resume Logging
        logger.info('Logging resumed')
        self.__paused = self.__pauseLog = False
        if self.__logName is None:
            self.__setName()

    def __pause(self):
        #Pause logging, thread keeps running
        if not self.__paused:
            logger.info('Logging paused')
            self.__paused = True

    def __save(self):
        #Compress the logfile
        if not self.__paused:
            self.__pause()
        try:
            with open(self.__logName + '.log', 'rb') as f:
                with gzip.open(self.__logName + '.gz', 'wb') as z:
                    shutil.copyfileobj(f, z)
        except:
            logger.error('Error compressing log file {}'.format(self.__logName))
            self.__logName = None
            return
        os.remove(self.__logName + '.log')
        self.logName = None

    def __discard(self):
        #Delete the logfile
        if self.__paused:
            self.__paused = True
        try:
            os.remove(self.__logName + '.log')
        except:
            logger.warning('Could not delete log file {}'.format(self.__logname))
        self.__logName = None

    def __status(self):
        d = dict()
        d['Running'] = self.__running
        d['Paused'] = self.__paused
        d['Log Name'] = self.__logName
        d['Frequency'] = self.__logFrequency
        d['Log Path'] = self.__logPath
        d['Headings'] = self.__logHeadings
        return d
