from time import time
from datetime import datetime
import math
from fmt import FMT
from general import *

#import logging

#logger = logging.getLogger('obdlogger').getChild(__name__)

config = loadConfig()

class KPI(object):

    def __init__(self,**kwargs):
        self.__parameters = dict()
        self.__func = None
        self.__screen = None
        self.__log = 'VAL'
        self.formats = dict()
        self.__values = dict()
        self.__history = dict()
        self.__values['VAL'] = None
        self.__values['MIN'] = None
        self.__values['MAX'] = None
        self.__values['SUM'] = 0
        self.__values['AVG'] = 0
        self.__history['VAL'] = []
        self.__history['SUM'] = []
        self.__history['AVG'] = []
        self.__paused = False

        for k in kwargs:
            if k == 'FUNCTION':
                self.__func = kwargs[k]
            #elif k == 'SCREEN':
            #    self.__screen = kwargs[k]
            elif k == 'LOG':
                self.__log = kwargs[k]
            elif k[:4] == 'FMT_':
                if k[4:] == 'ALL':
                    for f in ['VAL','MIN','MAX','AVG','SUM','LOG']:
                        self.formats[f] = kwargs[k].clone()
                else:
                    self.formats[k[4:]] = kwargs[k]
            else:
                self.__parameters[k] = kwargs[k]

        for f in self.__values:
            if f not in self.formats:
                self.formats[f] = FMT()
        if 'LOG' not in self.formats:
            self.formats['LOG'] = FMT()

        self.__count = 0
        self.__avgsum = 0
        self.__age = None

#    @property
#    def screen(self):
#        return self.__screen

#    @screen.setter
#    def screen(self, v):
#        self.__screen = v

    @property
    def paused(self):
        return self.__paused

    @paused.setter
    def paused(self, v):
        self.__paused = v

    @property
    def log(self):
        return self.formats['LOG'](self.__values[self.__log])

    @log.setter
    def log(self, v):
        self.__log = v

    @property # Getter
    def val(self):
        if self.__func is not None:
            self.val = self.__func(self.__parameters)            # Trigger the setter
        return self.__values['VAL']                              # self.__values['VAL'] is the instantaneous value.  It does not take time passed since the last sample into account.

    @val.setter
    def val(self, v):
        self.__values['VAL'] = v
        if v is not None:
            if type(v) in [float, int]:
                if not math.isnan(v):
                    self.__count += 1
                    self.__history['VAL'].append( (time(), v) )
                    if self.__values['MAX'] is None:
                        self.__values['MAX'] = v
                    else:
                        if v > self.__values['MAX']:
                            self.__values['MAX'] = v
                    if self.__values['MIN'] is None:
                        self.__values['MIN'] = v
                    else:
                        if v < self.__values['MIN']:
                            self.__values['MIN'] = v
                    if self.__age is not None:                                  # only calculate time shared value if at least one sample has been taken before
                        self.__values['SUM'] += (v * (time() - self.__age))     # Cumulative sum of time calculated value for sums
                    self.__avgsum += v                                          # Cumulative sum of instantaneous values for averaging
                    self.__values['AVG'] = self.__avgsum / self.__count
                    self.__history['AVG'].append((time(),self.__values['AVG']))
            if self.__paused:
                self.__age = None
            else:
                self.__age = time()                                             # Note the current time

    @property
    def max(self):
        return self.__values['MAX']

    @property
    def min(self):
        return self.__values['MIN']

    @property
    def len(self):
        return self.__count

    @property
    def sum(self):
        return self.__values['SUM']

    @property
    def avg(self):
        return self.__values['AVG']

    def format(self, f):
        if f == 'LOG':
            return self.formats['LOG'](self.__values[self.__log])
        else:
            self.__values['VAL'] = self.val
            return self.formats[f](self.__values[f])

    def setFormat(self, f, **kwargs):
        if f == 'ALL':
            for field in ['VAL','MIN','MAX','AVG','SUM','LOG']:
                for k in kwargs:
                    setattr(self.formats[field], k.lower(), kwargs[k])
        else:
            if f in self.formats:
                for k in kwargs:
                    setattr(self.formats[f], k.lower(), kwargs[k])
            else:
                raise KeyError('Field {} not found in __values[]. Must be VAL, MIN, MAX, AVG, SUM or LOG.'.format(f))

    def movingAverage(self, field, length, offset = 0, formatted = True):
        filterlist = [x for x in self.__history[field] if x[0] > (time() - offset - length) and x[0] < (time() - offset)]
        templist = [x[1] for x in filterlist]
        if len(templist) > 0:
            if formatted:
                return self.formats[field].fmtstr.format(sum(templist) / len(templist))
            else:
                return sum(templist) / len(templist)
        else:
            if formatted:
                return self.formats[field].fmtdtr.format(0)
            else:
                return 0

PI = 3.14159

###

# Calculation Functions

###

def driveRatio(p):
    #Final Drive Ratio
    #Final drive gear ration depends on tyre profile.
    #Needs to be attached to Speed and RPM sensors
    if 'SPEED' not in p or 'RPM' not in p: return None
    s = p['SPEED'].val
    r = p['RPM'].val
    if s is None or r is None: return None
    if s == 0: return None                          #Avoid Divide by Zero
    sideWall = config.getfloat('Vehicle', 'Tyre Width') * \
               (config.getfloat('Vehicle', 'Aspect Ratio')/100)            # Tyre sidewall height in mm
    wheelDiameter = sideWall + \
                    (config.getfloat('Vehicle', 'Rim Size') * 25.4)    # Wheel diameter in mm
    wheelCirc = wheelDiameter * PI / 1000.0         # Wheel circumfrance in m
    wheel_rpm = s*1000.0 / 60 / wheelCirc           # Wheel RPM
    return r / wheel_rpm                            # ratio Engine RPM : Wheel RPM

def LPH(p):
    if 'LPS' not in p: return None
    l = p['LPS'].val
    if l is None: return None
    return l * 3600

def FAM(p):
    if 'ENGINE_LOAD' not in p: return None
    e = p['ENGINE_LOAD'].val
    if e is None: return None
    if e == 0.0: return 0.0
    return config.getfloat('Vehicle', 'Fuel Air Ratio Max') - (\
           ( config.getfloat('Vehicle', 'Fuel Air Ratio Max') - \
             config.getfloat('Vehicle', 'Fuel Air Ratio Min')) * (e / 100.0))

def LPS(p):
    if 'MAF' not in p or 'FAM' not in p: return None
    m = p['MAF'].val
    f = p['FAM'].val
    if m is None or f is None: return None
    if f == 0: return 0.0
    if m == 0: return None
    return m / f / config.getfloat('Vehicle', 'Fuel Density')

def LP100K(p):
    #Fuel Consumption in L/100K
    #Depends on Air/Fuel Mixture.    Diesel is documented at 14.7:1
    #Needs to be attaqched to Speed and MAF sensors
    if 'LPH' not in p or 'SPEED' not in p: return None
    l = p['LPH'].val
    s = p['SPEED'].val
    if l is None or s is None: return None
    if s == 0: return 0
    return 100.0 / s * l

def boost(p):
    #Boost Pressure in PSI
    #Simple calculation of MAP (Manifold Absolute Pressure) and Barometric Pressure
    #Needs to be attached to Intake Pressure and Barometric Pressure
    if 'INTAKE_PRESSURE' not in p or 'BAROMETRIC_PRESSURE' not in p: return None
    i = p['INTAKE_PRESSURE'].val
    b = p['BAROMETRIC_PRESSURE'].val
    if i is None or b is None: return None
    v = (i - b) / 6.89475728
    if v<0: return 0
    return v

def distance(p):
    if 'SPEED' not in p: return None
    d = p['SPEED'].val
    if d is None: return None
    return d / 3600

def OBDdistance(p):
    if 'DISTANCE_SINCE_DTC_CLEAR' not in p: return None
    d = p['DISTANCE_SINCE_DTC_CLEAR'].val
    if d is None: return None
    return d - p['DISTANCE_SINCE_DTC_CLEAR'].min

def gear(p):
    if 'DRIVE_RATIO' not in p: return None
    r = p['DRIVE_RATIO'].val
    if r is None: return config.get('Transmission','Gear Neutral Label')
    for i in range(config.getint('Vehicle','Transmission Speeds')):
        if r > config.getfloat('Transmission','Gear {} Lower'.format(i+1)) and \
           r < config.getfloat('Transmission','Gear {} Upper'.format(i+1)):
            return config.get('Transmission','Gear {} Label'.format(i+1))
    return config.get('Transmission','Gear Neutral Label')

def duration(p):
    if 'RPM' not in p: return None
    r = p['RPM'].val
    if r is None: return None
    if r == 0: return 0
    return 1

def idleTime(p):
    if 'SPEED' not in p and 'RPM' not in p: return None
    s = p['SPEED'].val
    r = p['RPM'].val
    if s is None or r is None: return None
    if s == 0:
        if r > 0 and r < 1000:
            return 1
    return 0

def timeStamp(p):
    return datetime.now()
