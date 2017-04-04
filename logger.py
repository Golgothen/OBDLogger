from multiprocessing import Process
from time import time, sleep
from datetime import datetime
import threading, gzip, shutil, os, logging
from messages import Message, PipeCont

logger = logging.getLogger('root')

class DataLogger(threading.Thread):

# No parameters needed.
# Creates a DataLogger object running on a seperate thread.
# Set the log frequency by .LogFrequency=
# Log location is set via .logPath
# Call save() to save and archive the log file.
# Call discard() to delete the log file.
# Stop the thread by calling stop()
# Pause logging by calling pause()
# Resume logging by calling resume()
# Cannot be restarted after calling stop()

  def __init__(self, 
               controlPipe, 
               dataPipe, 
               workerPipe):

    threading.Thread.__init__(self)
    self.__logName = None                 # File to log to
    self.__logFrequency = 1               # Time per second to write to the log file
    self.__logHeadings = []               # List of headings for the log file.
    self.__running = False                # Internal running flag
    self.__paused = True                  # Internal paused flag
    self.__logPath = './'                 # Path for logfile. Default to current directory
    self.deamon=True                      # Sets the process to daemon. Stops if the parent process stops
    self.name='Logger'                    # Sets the process name. Helps with debigging.
    self.__controlPipe = controlPipe      # Communication pipe with the controlling application
    self.__dataPipe = dataPipe            # Comminication pipe with the Data Collector process
    self.__workerPipe = workerPipe        # Comminication pipe with the Data Collector process
    self.__data = dict()                  # Data dictionary to use to write log diles
    self.__refreshRequired = True         # Flag to determine if the dictionary needs to be refreshed
    self.__refreshRequested = False       # Flag to determine if the refresh request has been sent
    self.__logFormat = '%Y%m%d%H%M'       # Log file name format
    self.__pauseLog = False               # Flag to pause logging
    self.__pid = None                     # Pricess ID of Logging process
    self.__tripTimeout = 900              # Time in seconds to continue logging to the same file or start a new one.
    self.__pausedAt = None                # Holds the time when logging was paused

    logger.debug('Logging process initalised')

  def run(self):
    self.__running=True
    self.__pid = os.getpid()
    logger.info('Logger process starting on ' + str(self.__pid))
    try:
      timer=time()
      while self.__running:
        if self.__logName is None:
          logger.debug('Logger name not set. Pausing')
          self.__pause()
        logger.debug('Running: '+str(self.__running)+', Paused: '+str(self.__paused)+', Required: '+str(self.__refreshRequired)+', Requested: '+str(self.__refreshRequested))
        self.__checkPipe()
        if not self.__paused:
          if self.__refreshRequired:
            if not self.__refreshRequested:
              logger.debug('Getting snapshot')
              self.__dataPipe.send(Message('SNAPSHOT'))
              self.__refreshRequested=True
            continue
          line=''
          logger.debug('Recording data')
          for l in self.__logHeadings:
            if l in self.__data:
              if self.__data[l] is not None:
                line+=str(self.__data[l])+','
              else:
                line+='-,'
                logger.debug(l + ' is none')
            else:
              logger.debug(l + ' is not in snapshot')
              line+='-,'
          with open(self.__logName + '.log','ab') as f:
            f.write(bytes(line[:len(line)-1]+'\n','UTF-8'))
          self.__refreshRequired = True
          self.__refreshRequested = False
        else:
          self.__pauseLog = True
          if self.__pausedAt is None:
            self.__pausedAt = datetime.now()        # Take note of the time when logging was paused
        sleeptime=(1.0/self.__logFrequency)-(time()-timer)
        if sleeptime<0:
          logger.warning('Logger sleep time reached zero. Concider reducing log frequency') 
          #self.logFrequency-=1
        else:
          sleep(sleeptime)
          timer=time()
      logger.info('Logging process stopped')
    except (KeyboardInterrupt, SystemExit):
      self.__running = False
      return 

  def __checkPipe(self):
    # Check controller pipe
    while self.__controlPipe.poll():
      m = self.__controlPipe.recv()
      logger.debug(str(m.message) + ' received on controller pipe')

      if m.message == 'STOP'      : self.__stop()
      if m.message == 'SAVE'      : self.__save()
      if m.message == 'DISCARD'   : self.__discard()
      if m.message == 'PAUSE'     : self.__pause()
      if m.message == 'RESUME'    : self.__resume()
      if m.message == 'RESTART'   : self.__restart()
      if m.message == 'LOGPATH'   : self.__logPath = m.params['PATH']
      if m.message == 'LOGNAME'   : self.__controlPipe.send(Message(m.message,NAME=self.__logName))
      if m.message == 'STATUS'    : self.__controlPipe.send(Message(m.message,STATUS=self.__status()))
      if m.message == 'FREQUENCY' : self.__logFrequency = m.params['FREQUENCY']
      if m.message == 'TIMEOUT'   : self.__tripTimeout = m.params['TIMEOUT']
      if m.message == 'HEADINGS'  : 
        self.__colHeadings(m.params['HEADINGS'])
        #self.__restart()

    while self.__workerPipe.poll():
      m = self.__workerPipe.recv()
      logger.debug(str(m.message) + ' received on worker pipe')

      if m.message == 'PAUSE'     : self.__pause()
      if m.message == 'RESUME'    : self.__resume()


    while self.__dataPipe.poll():
      m = self.__dataPipe.recv()
      logger.debug(str(m.message) + ' reveived on data pipe')

      if m.message == 'SNAPSHOT':
        self.__data = m.params['DATA']
        self.__refreshRequired = False

  def __setName(self):
    if self.__logHeadings == []:
      logger.warning('No column headings have been set.  No log file started.')
    else:
      self.__logName=(self.__logPath + datetime.now().strftime(self.__logFormat))
      logger.info('Logging started - output: ' + self.__logName + '.log')
      line=''
      for l in self.__logHeadings:
        line+=l+','
      with open(self.__logName + '.log','wb') as f:    # Clobber output file if it exists
        f.write(bytes(line[:len(line)-1]+'\n','UTF-8'))
      #self.__dataPipe.send(Message('RESET'))           # Reset data collector when starting a new trip

  def __colHeadings(self,headings):
    #Set the log headings
    self.__logHeadings = headings

  def __stop(self):
    #Stop logging.  Thread stops - This is final.  Cannot be restarted
    self.__running=False

  def __resume(self):
    #Resume Logging
    logger.info('Logging resumed')
    self.__paused = self.__pauseLog = False
    if self.__pausedAt is not None:
      if (datetime.now() - self.__pausedAt).total_seconds() > self.__tripTimeout:
        if self.__logName is not None:
          self.__save()
        self.__setName()
    #else:
    if self.__logName is None:
      self.__setName()
    self.__pausedAt = None

  def __pause(self):
    #Pause logging, thread keeps running
    logger.info('Logging paused')
    self.__paused=True
    if self.__pausedAt is None:
      self.__pausedAt = datetime.now()

  def __save(self):
    #Compress the logfile
    if not self.__paused:
      self.__pause()
    while not self.__pauseLog:
      sleep(0.01)             # wait for main process to set this flag to acknolege data has stopped being written
    try:
      with open(self.__logName + '.log', 'rb') as f:
        with gzip.open(self.__logName + '.gz', 'wb') as z:
          shutil.copyfileobj(f, z)
    except:
      logger.error('Error compressing log file ' + self.__logName)
      self.__logName = None
      return
    os.remove(self.__logName)
    self.logName = None

  def __discard(self):
    #Delete the logfile
    if self.__paused:
      self.__paused=True
    while not self.__pauseLog:
      sleep(0.01)             # wait for main process to set this flag to acknolege data has stopped being written
    try:
      os.remove(self.__logName)
    except:
      logger.warning('Could not delete log file ' + self.__logname)
    self.__logName=None

  def __status(self):
    d = dict()
    d['Running'] = self.__running
    d['Paused'] = self.__paused
    d['Log Name'] = self.__logName
    d['Frequency'] = self.__logFrequency
    d['Log Path'] = self.__logPath
    d['Headings'] = self.__logHeadings
    return d
