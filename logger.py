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

  def __init__(self, controlPipe, dataPipe):
    threading.Thread.__init__(self)
    self.__logName = None                 # File to log to
    self.__logFrequency = 1               # Time per second to write to the log file
    self.__logHeadings = []             # List of headings for the log file.
    self.__running = False              # Internal running flag
    self.__pause = True                # Internal paused flag
    self.__logPath = './'                 # Path for logfile. Default to current directory
    self.deamon=True                    # Sets the process to daemon. Stops if the parent process stops
    self.name='Logger'                  # Sets the process name. Helps with debigging.
    self.__controlPipe = controlPipe
    self.__dataPipe = dataPipe
    self.__data = dict()
    self.__refreshRequired = False
    self.__refreshRequested = False
    self.__logFormat = "%Y%m%d%H%M"
    self.__pauseLog = False
    self.__pid = None
    logger.debug('Logging process initalised')

  def run(self):
    self.__running=True
    self.__pid = os.getpid()
    logger.info("Logger process starting on " + str(self.__pid))
    try:
      if self.__logName is None:
        self.__pause = True
      timer=time()
      while self.__running:
        logger.debug('Running: '+str(self.__running)+', Paused: '+str(self.__pause)+', Required: '+str(self.__refreshRequired)+', Requested: '+str(self.__refreshRequested))
        self.__checkPipe()
        if not self.__pause:
          if self.__refreshRequired:
            if not self.__refreshRequested:
              logger.debug("Getting snapshot")
              self.__dataPipe.send(Message("SNAPSHOT"))
              self.__refreshRequested=True
            continue
          line=""
          logger.debug("Recording data")
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
          with open(self.__logName,"ab") as f:
            f.write(bytes(line[:len(line)-1]+'\n','UTF-8'))
          self.__refreshRequired = True
          self.__refreshRequested = False
        else:
          self.__pauseLog = True
        sleeptime=(1.0/self.__logFrequency)-(time()-timer)
        if sleeptime<0:
          logger.warning('Logger sleep time reached zero. Concider reducing log frequency') 
          #self.logFrequency-=1
        else:
          sleep(sleeptime)
          timer=time()
      logger.info("Logging process stopped")
    except (KeyboardInterrupt, SystemExit):
      self.__running = False
      return 

  def __checkPipe(self):
    # Check controller pipe
    #logger.info("Checking pipes")
    while self.__controlPipe.poll():
      m = self.__controlPipe.recv()
      logger.info(str(m.message) + " received on controller pipe")

      if m.message == "STOP"      : self.__stop()
      if m.message == "SAVE"      : self.__save()
      if m.message == "DISCARD"   : self.__discard()
      if m.message == "PAUSE"     : self.__pause()
      if m.message == "RESUME"    : self.__resume()
      if m.message == "RESTART"   : self.__restart()
      if m.message == "LOGPATH"   : self.__logPath = m.params["PATH"]
      if m.message == "LOGNAME"   : self.__controlPipe.send(Message(m.message,NAME=self.__logName))
      if m.message == "STATUS"    : self.__controlPipe.send(Message(m.message,STATUS=self.__status()))
      if m.message == "FREQUENCY" : self.__logFrequency = m.params["FREQUENCY"]
      if m.message == "HEADINGS"  : 
        self.__logHeadings = m.params["HEADINGS"]
        #self.__restart()

    while self.__dataPipe.poll():
      m = self.__dataPipe.recv()
      logger.debug(str(m.message) + " reveived on data pipe")

      if m.message == "SNAPSHOT":
        self.__data = m.params['DATA']
        self.__refreshRequired = False

  def __restart(self):
    self.__logName=(self.__logPath + datetime.now().strftime(self.__logFormat)+".log")
    logger.info('Logging started - output: ' + self.__logName)
    line=''
    for l in self.__logHeadings:
      line+=l+','
    try:
      f = open(self.__logName,"ab")
      f.write(line[:len(line)-1]+'\n')
      f.close()
      #self.__pause=False
    except:
      logger.error('Error writing to log file ' + self.__logName)
      self.logName = None
      return

  def __logHeadings(self,headings):
    #Set the log headings
    #Causes a log file restart if already logging
    self.__logHeadings = headings

  def __stop(self):
    #Stop logging.  Thread stops - This is final.  Cannot be restarted
    self.__running=False

  def __resume(self):
    #Resume Logging
    logger.info('Logging resumed')
    self.__pause = self.__pauseLog = False
    if self.__logName is None: self.__restart()
    

  def __pause(self):
    #Pause logging, thread keeps running
    logger.info('Logging paused')
    self.__pause=True

  def __save(self):
    #Compress the logfile
    if not self.__paused:
      self.__paused=True
    while not self.__pauseLog:
      sleep(0.01)             # wait for main process to set this flag to acknolege data has stopped being written
    try:
      f=open(self.__logName, 'rb')
      z=gzip.open(self.__logName + '.gz', 'wb')
      shutil.copyfileobj(f, z)
      f.close()
      z.close()
    except:
      logger.error('Error compressing log file ' + self.__logName)
      self.__logName = None
      return
    os.remove(self.__logName)
    self.logName = None

  def __discard(self):
    #Delete the logfile
    if self.__pause:
      self.__pause=True
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
    d['Paused'] = self.__pause
    d['Log Name'] = self.__logName
    d['Frequency'] = self.__logFrequency
    d['Log Path'] = self.__logPath
    return d
