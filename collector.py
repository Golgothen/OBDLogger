from multiprocessing import Process, Queue, Event
from messages import Message
from time import sleep
from pipewatcher import PipeWatcher
from configparser import ConfigParser

from kpi import *

from general import *

import logger #, os

logger = logging.getLogger('obdlogger').getChild(__name__)

config = loadConfig()
PIPE_TIMEOUT = config.getfloat('Application','Pipe Timeout')             # Time in seconds to wait for pipe command responses

class Collector(Process):

    def __init__(self,
                 ecuPipe,                          # Pipe to ECU process
                 controlPipe,                      # Pipe to controlling application
                 logPipe,                          # Pipe to Logger process
                 workerPipe,                       # Pipe to Worker process
                 que):                             # Result que

        super(Collector,self).__init__()
        self.__results = que
        self.__data = dict()
        self.__pipes = {}
        self.__pipes['ECU'] = PipeWatcher(self, ecuPipe, 'COLLECTOR->ECU')
        self.__pipes['APPLICATION'] = PipeWatcher(self, controlPipe, 'COLLECTOR->APP')
        self.__pipes['LOG'] = PipeWatcher(self, logPipe, 'COLLECTOR->LOG')
        self.__pipes['WORKER'] = PipeWatcher(self, workerPipe, 'COLLECTOR->WORKER')

        self.__paused = False
        self.__running = False
        self.__frequency = 100
        self.__ready = False
        self.__SCreq = False
        self.name = 'COLLECTOR'

        self.__reset_complete = Event()

    def run(self):
        # Main function for process.    Runs continully until instructed to stop.
        self.__running = True
        logger.info('Starting Collector process on PID {}'.format(str(self.pid)))
        for p in self.__pipes:
            self.__pipes[p].start()
        while self.__running:
            try:                                                                    # Running set to False by STOP command
                if self.__ready:                                                    # Ready set to True when data dictonary has been built
                    if not self.__paused:                                           # Paused set True/False by PAUSE/RESUME commands
                        while self.__results.qsize() > 0:                           # Loop while there are results in the que
                            m = self.__results.get()                                    # Pull result message from que
                            self.__data[m.message].val = m.params['VALUE']          # Update corresponding KPI with the result value
                    sleep(1.0/self.__frequency)                                     # brief sleep so we dont hog the CPU
                else:                                                               # Not ready?
                    if not self.__SCreq:                                            # Flag if the Supported Commands request has been sent
                        self.__SCreq = True                                         # Only send the above request once
                        self.reset()                                                # Empty data dictionary and request a list of supported commands
                        self.__reset_complete.wait()
                        self.__reset_complete.clear()
                sleep(1.0 / self.__frequency)                                       # Release CPU
            except (KeyboardInterrupt, SystemExit):                                 # Pick up interrups and system shutdown
                self.__running = False                                              # Set Running to false, causing the above loop to exit
                continue
            except:
                logger.critical('Unhandled exception occured in Collector process:',exc_info = True, stack_info = True)
        logger.info('Collector process stopped')                                    # Running has been set to False


    def snapshot(self, p = None):
        # Returns a dictionary of all KPI current values
        data = dict()
        for d in self.__data:
            data[d] = dict()
            for f in ['VAL','MIN','MAX','AVG','SUM','LOG']:
                data[d][f] = self.__data[d].format(f)
        return Message('SNAP_SHOT', SNAPSHOT = data)

    def sum(self, p):
        return Message('GETSUM', SUM = 0.0 if p['NAME'] not in self.__data else self.__data[p['NAME']].sum)

    def avg(self, p):
        return Message('GETAVG', AVG = 0.0 if p['NAME'] not in self.__data else self.__data[p['NAME']].avg)

    def min(self, p):
        return Message('GETMIN', MIN = None if p['NAME'] not in self.__data else self.__data[p['NAME']].min)

    def max(self, p):
        return Message('GETMAX', MAX = None if p['NAME'] not in self.__data else self.__data[p['NAME']].max)

    def val(self, p):
        if p['NAME'] in self.__data:
            return Message('GETVAL', VAL = None if p['NAME'] not in self.__data else self.__data[p['NAME']].val)

    def reset(self, p = None):
        self.__ready = False
        self.__data = dict()
        self.__pipes['WORKER'].send(Message('SUPPORTED_COMMANDS'))

    def supported_commands(self, p):
        self.__SCreq = False
        if p['SUPPORTED_COMMANDS'] == []:
            self.__reset_complete.set()
            return
        for f in p['SUPPORTED_COMMANDS']:
            self.__data[f] = KPI()

        # now add calculates data fields

        self.__data['TIMESTAMP'] = KPI(FUNCTION = timeStamp,
                                       FMT_ALL = FMT(TYPE = 'd',
                                                     PRECISION = '%Y-%m-%d %H:%M:%S')
                                      )

        if 'ENGINE_LOAD' in self.__data:

            self.__data['FAM'] =             KPI(FUNCTION = FAM,
                                                 ENGINE_LOAD = self.__data['ENGINE_LOAD']
                                                )

        if 'MAF' in self.__data and \
           'FAM' in self.__data:

                self.__data['LPS'] =         KPI(FUNCTION = LPS,
                                                 MAF = self.__data['MAF'],
                                                 FAM = self.__data['FAM']
                                                )
                self.__data['LPH'] =         KPI(FUNCTION = LPH,
                                                 LPS = self.__data['LPS'],
                                                 FMT_ALL = FMT(PRECISION = 3)
                                                )

        if 'SPEED' in self.__data:
            self.__data['SPEED'].setFormat('ALL', LENGTH = 4, PRECISION = 0)
            self.__data['SPEED'].setFormat('AVG', LENGTH = 9, PRECISION = 2)

            self.__data['DISTANCE'] =        KPI(FUNCTION = distance,
                                                 SPEED = self.__data['SPEED']
                                                )

            if 'RPM' in self.__data:
                self.__data['DRIVE_RATIO'] = KPI(FUNCTION = driveRatio,
                                                 SPEED = self.__data['SPEED'],
                                                 RPM = self.__data['RPM']
                                                )
                self.__data['GEAR'] =        KPI(FUNCTION = gear,
                                                 DRIVE_RATIO = self.__data['DRIVE_RATIO'],
                                                 FMT_ALL = FMT(TYPE = 's',
                                                               ALIGNMENT = '>'
                                                              )
                                                )
                self.__data['IDLE_TIME'] =   KPI(FUNCTION = idleTime,
                                                 SPEED = self.__data['SPEED'],
                                                 RPM = self.__data['RPM'],
                                                 FMT_ALL = FMT(TYPE = 't')
                                                )

            if 'LPH' in self.__data:
                self.__data['LP100K'] =      KPI(FUNCTION = LP100K,
                                                 SPEED = self.__data['SPEED'],
                                                 LPH = self.__data['LPH'],
                                                 FMT_ALL = FMT(PRECISION = 3)
                                                )

        if 'RPM' in self.__data:
            self.__data['DURATION'] =        KPI(FUNCTION = duration,
                                                 RPM = self.__data['RPM'],
                                                 FMT_ALL = FMT(TYPE = 't')
                                                )

        if 'BAROMETRIC_PRESSURE' in self.__data and \
           'INTAKE_PRESSURE' in self.__data:

            self.__data['BOOST_PRESSURE'] =  KPI(FUNCTION = boost,
                                                 BAROMETRIC_PRESSURE = self.__data['BAROMETRIC_PRESSURE'],
                                                 INTAKE_PRESSURE=self.__data['INTAKE_PRESSURE'])

        if 'DISTANCE_SINCE_DTC_CLEAR' in self.__data:

            self.__data['OBD_DISTANCE'] =    KPI(FUNCTION = OBDdistance,
                                                 DISTANCE_SINCE_DTC_CLEAR = self.__data['DISTANCE_SINCE_DTC_CLEAR'],
                                                 FMT_ALL = FMT(PRECISION = 0)
                                                )

        self.__data['ALTITUDE'] = KPI(FMT_ALL = FMT(LENGTH = 5, COMMAS = False, PRECISION = 0))
        self.__data['LATITUDE'] = KPI(FMT_ALL = FMT(LENGTH = 19, TYPE = 'lat'))
        self.__data['LATITUDE'].setFormat('LOG', TYPE = 'f', LENGTH = 9, PRECISION = 5)
        self.__data['LONGITUDE'] = KPI(FMT_ALL = FMT(LENGTH = 19, TYPE = 'lon'))
        self.__data['LONGITUDE'].setFormat('LOG', TYPE = 'f', LENGTH = 9, PRECISION = 5)
        self.__data['GPS_SPD'] = KPI(FMT_ALL = FMT(LENGTH=5, PRECISION = 1))
        self.__data['HEADING'] = KPI(FMT_ALL = FMT())


        # Alter a few data fields for logging
        if 'DISTANCE' in self.__data:
            self.__data['DISTANCE'].log = 'SUM'

        # Set custom formats. Default format is {:9,.2f}
        for d in self.__data:
            if d in ['RPM','COOLANT_TEMP','FUEL_RAIL_PRESSURE_DIRECT','WARMUPS_SINCE_DTC_CLEAR','DISTANCE_W_MIL']:
                self.__data[d].setFormat('ALL', PRECISION = 0)
            if d in ['CONTROL_MODULE_VOLTAGE']:
                self.__data[d].setFormat('ALL', LENGTH = 5, PRECISION = 2)
            self.__data[d].setFormat('LOG', COMMAS = False)

        self.__ready = True
        self.__dirty = False
        logger.info('Dictionary build complete. {} KPIs added'.format(len(self.__data)))
        self.__reset_complete.set()

    def pause(self):
        if not self.__paused:
            logger.info('Pausing Collector process')
            self.__dirty = self.__paused = True
            for d in self.__data:
                self.__data[d].paused = True

    def resume(self):
        if self.__paused:
            logger.info('Resuming Collector process')
            self.__paused = False
            if self.__dirty:
                logger.warning('Collector resumed without reset - Data set may have changed')
            for d in self.__data:
                self.__data[d].paused = False

    def stop(self):
        if self.__running:
            logger.debug('Stopping Collector process')
            self.__running = False

    def getstatus(self, p = None):
        d = dict()
        d['Name'] = self.name
        #d['Running'] = self.__running
        d['Paused'] = self.__paused
        d['PID'] = self.pid
        d['Count'] = len(self.__data)
        d['Length'] = dict()
        for k in self.__data:
            d['Length'][k] = self.__data[k].len
        return Message('DATASTATUS', STATUS = d)

    def summary(self, p = None):
        d=dict()
        d['DATE'] = datetime.now() #self.__data['TIMESTAMP'].min
        d['AVG_LP100K'] = self.__data['LP100K'].avg
        d['DISTANCE'] = self.__data['DISTANCE'].sum
        d['AVG_SPEED'] = self.__data['SPEED'].avg
        d['FUEL'] = self.__data['LPS'].sum
        d['AVG_LOAD'] = self.__data['ENGINE_LOAD'].avg
        d['DURATION'] = self.__data['DURATION'].sum
        d['IDLE_TIME'] = self.__data['IDLE_TIME'].sum
        return Message('GETSUMMARY', SUMMARY = d)

    def dataline(self, p):
        temp = config.get('Data Layout',p['NAME'])
        for d in self.__data:
            for f in ['VAL', 'MIN', 'MAX', 'SUM', 'AVG', 'LOG']:
                if '{}.{}'.format(d,f) in temp:
                    temp=temp.replace('{}.{}'.format(d,f),
                                      '{}'.format(self.__data[d].format(f)))
        temp=temp.replace('*',' ')
        return Message('DATA_LINE', LINE = temp)
