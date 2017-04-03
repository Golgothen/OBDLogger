############################################################################################
#                                                                                          #
#                                                                                          #
#  Collector class:                                                                        #
#                                                                                          #
#  Collects OBD query results from the results que and stores them in the KPI dictionary.  #
#                                                                                          #
#  Update History:                                                                         #
#                                                                                          #
#  2/4/2017 - Completed multi-process support.                                             #
#                                                                                          #
#                                                                                          #
############################################################################################

from multiprocessing import Process, Queue
from messages import Message
from kpi import *
from time import sleep

import os, logger

logger = logging.getLogger('root')

PIPE_TIMEOUT = 3                             # Time in seconds to wait for pipe command responses

class Collector(Process):

  def __init__(self,
               ecuPipe,      # Pipe to ECU process
               controlPipe,  # Pipe to controlling application
               logPipe,      # Pipe to Logger process
               workerPipe,   # Pipe to Worker process
               que):         # Result que

    super(Collector,self).__init__()
    self.__results = que
    self.__data = dict()
    self.__ecuPipe = ecuPipe
    self.__controlPipe = controlPipe
    self.__loggerPipe = logPipe
    self.__workerPipe = workerPipe
    #self.__dirty = False
    self.__pid = None
    self.__paused = False
    self.__running = False
    self.__frequency = 100
    self.__ready = False
    self.__SCreq = False
    self.name = 'COLLECTOR'

  def run(self):
    # Main function for process.  Runs continully until instructed to stop.
    self.__running = True
    self.__pid = os.getpid()
    try:
      while self.__running:                                   # Running set to False by STOP command
        self.__checkPipe()                                    # Check all pipes for commands
        if self.__ready:                                      # Ready set to True when data dictonary has been built
          if not self.__paused:                               # Paused set True/False by PAUSE/RESUME commands
            while self.__results.qsize() > 0:                 # Loop while there are results in the que
              m = self.__results.get()                        # Pull result message from que
              self.__data[m.message].val=m.params['VALUE']    # Update corresponding KPI with the result value
            self.__checkPipe()                                # Check pipes for commands after the que has been cleared
          sleep(1.0/self.__frequency)                         # brief sleep so we dont hog the CPU
        else:                                                 # Not ready?
          if not self.__SCreq:                                # Flag if the Supported Commands request has been sent
            self.__reset()                                    # Empty data dictionary and request a list of supported commands
            self.__SCreq=True                                 # Only send the above request once
        sleep(1.0/self.__frequency)                           # Release CPU
      logger.info('Collector process stopped')                # Running has been set to False
    except (KeyboardInterrupt, SystemExit):                   # Pick up interrups and system shutdown
      self.__running = False                                  # Set Running to false, causing the above loop to exit

  def __checkPipe(self):
    # Check all pipes to other processes for commands/requests
    while self.__ecuPipe.poll():                              # Loop through all messages on the ECU pipe
      m = self.__ecuPipe.recv()                               # Grab the first message in the pipe
      logger.info('Received ' + str(m.message) + ' on ECU pipe')

      if m.message == 'PAUSE'   : self.__pause()              
      if m.message == 'RESUME'  : self.__resume()
      if m.message == 'STOP'    : self.__stop()
      if m.message == 'RESET'   : self.__reset()

    while self.__controlPipe.poll():                          # Loop through all messages on the Application pipe
      m = self.__controlPipe.recv()
      logger.debug('Received ' + str(m.message) + ' on controller pipe')

      if m.message == 'RESET'   : self.__reset()
      if m.message == 'SNAPSHOT': self.__controlPipe.send(Message(m.message,SNAPSHOT=self.__snapshot()))
      if m.message == 'SUMMARY' : self.__controlPipe.send(Message(m.message,SUMMARY=self.__summary()))
      if m.message == 'SUM'     : self.__controlPipe.send(Message(m.message,SUM=self.__sum(m.params)))
      if m.message == 'AVG'     : self.__controlPipe.send(Message(m.message,AVG=self.__avg(m.params)))      
      if m.message == 'MIN'     : self.__controlPipe.send(Message(m.message,MIN=self.__min(m.params)))
      if m.message == 'MAX'     : self.__controlPipe.send(Message(m.message,MAX=self.__max(m.params)))
      if m.message == 'STATUS'  : self.__controlPipe.send(Message(m.message,STATUS=self.__status()))

    while self.__loggerPipe.poll():                          # Loop through all messages on the Logger pipe
      m = self.__loggerPipe.recv()
      logger.debug('Received ' + str(m.message) + ' on logger pipe')

      if m.message == 'SNAPSHOT':   self.__loggerPipe.send(Message(m.message,DATA=self.__snapshot()))

    while self.__workerPipe.poll():                          # Loop through all messages on the Worker pipe
      m = self.__workerPipe.recv()
      logger.debug('Received ' + str(m.message) + ' on Worker pipe')

      if m.message == 'SUPPORTED_COMMANDS': self.__buildDict(m.params['SUPPORTED_COMMANDS']) 

  def __snapshot(self):
    # Returns a dictionary of all KPI current values
    data = dict()
    for d in self.__data:
      data[d] = self.__data[d].val
    return data

  def __sum(self, m):
    # 
    return self.__data[m['NAME']].sum(m['OFFSET'], m['LENGTH'])

  def __avg(self, m):
    return self.__data[m['NAME']].sum(m['OFFSET'], m['LENGTH'])

  def __min(self, m):
    return self.__data[m['NAME']].min

  def __max(self, m):
    return self.__data[m['NAME']].max

  def __reset(self):
    self.__ready = False
    self.__data = dict()
    self.__workerPipe.send(Message('SUPPORTED_COMMANDS'))

  def __buildDict(self, supportedcommands):
    self.__SCreq=False
    if supportedcommands == []:
      return
    for f in supportedcommands:
      self.__data[f] = KPI()
    # now add calculates data fields
    self.__data['TIMESTAMP'] = KPI(FUNCTION=timeStamp)
    if 'MAF' in self.__data: 
      self.__data['MAF'].timeSensitive = True
      if 'ENGINE_LOAD' in self.__data:
        self.__data['LPS'] = KPI(FUNCTION=LPS, MAF=self.__data['MAF'], ENGINE_LOAD=self.__data['ENGINE_LOAD'])
        self.__data['LPH'] = KPI(FUNCTION=LPH, LPS=self.__data['LPS'])
    if 'SPEED' in self.__data:
      self.__data['DISTANCE'] = KPI(FUNCTION=distance,SPEED=self.__data['SPEED'])
      self.__data['DISTANCE'].timeSensitive=True
      if 'RPM' in self.__data:
        self.__data['DRIVE_RATIO'] = KPI(FUNCTION=driveRatio, SPEED=self.__data['SPEED'], RPM=self.__data['RPM'])
        self.__data['GEAR'] = KPI(FUNCTION=gear,DRIVE_RATIO=self.__data['DRIVE_RATIO'])
        self.__data['IDLE_TIME'] = KPI(FUNCTION=idleTime, SPEED=self.__data['SPEED'], RPM = self.__data['RPM'])
        self.__data['IDLE_TIME'].timeSensitive = True
      if 'LPH' in self.__data:
        self.__data['LP100K'] = KPI(FUNCTION=LP100K, SPEED=self.__data['SPEED'], LPH=self.__data['LPH'])
    if 'RPM' in self.__data:
      self.__data['DURATION'] = KPI(FUNCTION=duration, RPM = self.__data['RPM'])
      self.__data['DURATION'].timeSensitive = True
    if 'BAROMETRIC_PRESSURE' in self.__data and 'INTAKE_PRESSURE' in self.__data:
      self.__data['BOOST_PRESSURE'] = KPI(FUNCTION=boost, BAROMETRIC_PRESSURE=self.__data['BAROMETRIC_PRESSURE'], INTAKE_PRESSURE=self.__data['INTAKE_PRESSURE'])
    if 'DISTANCE_SINCE_DTC_CLEAR' in self.__data:
      self.__data['OBD_DISTANCE'] = KPI(FUNCTION=OBDdistance, DISTANCE_SINCE_DTC_CLEAR=self.__data['DISTANCE_SINCE_DTC_CLEAR'])
    logger.debug(str(self.__data))
    self.__ready=True
    self.__dirty=False
    logger.info('Dictionary build complete')

  def __pause(self):
    if not self.__paused:
      logger.info('Pausing Collector process')
      self.__dirty = self.__paused = True
      
  def __resume(self):
    if self.__paused:
      logger.info('Resuming Collector process')
      self.__paused = False
      if self.__dirty:
        logger.warning('Collector resumed without reset - Data set may have changed')

  def __stop(self):
    if self.__running:
      logger.debug('Stopping Collector process')
      self.__running = False

  def __status(self):
    d = dict()
    d['Name'] = self.name
    d['Running'] = self.__running
    d['Paused'] = self.__paused
    d['PID'] = self.__pid
    d['Count'] = len(self.__data)
    d['Length'] = dict()
    for k in self.__data:
      d['Length'][k] = self.__data[k].len
    return d

  def __summary(self):
    d=dict()
    for k in self.__data:
      if self.__data[k].val is None:
        continue
      else:
        d[k] = dict()
        d[k]['VAL'] = self.__data[k].val
        d[k]['MIN'] = self.__data[k].min
        d[k]['MAX'] = self.__data[k].max
        if k not in ('TIMESTAMP','GEAR'):
          d[k]['AVG'] = self.__data[k].avg()
          d[k]['SUM'] = self.__data[k].sum()
    return d

