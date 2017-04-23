from time import time
from datetime import datetime
from general import *

import logging

logger = logging.getLogger('root')

class KPI(object):

    def __init__(self,**kwargs):
        self.__parameters = dict()
        self.__func = None
        self.__format = '{:9,.2f}'
        self.__screen = None
        self.__log = None
        for k in kwargs:
            if k == 'FUNCTION':
                self.__func = kwargs[k]
            elif k == 'SCREEN':
                self.__screen = kwargs[k]
            elif k == 'FORMAT':
                self.__format = kwargs[k]
            elif k == 'LOG':
                self.__log = kwargs[k]
            else:
                self.__parameters[k] = kwargs[k]
        self.__min = None
        self.__max = None
        self.__sum = 0.0
        self.__avg = 0.0
        self.__count = 0
        self.__val = None
        self.__age = None

    @property
    def format(self):
        try:
            return self.__format.format(self.__val)
        except (ValueError, TypeError):
            return None

    @format.setter
    def format(self, v):
        self.__format = v

    @property
    def screen(self):
        return self.__screen

    @screen.setter
    def screen(self, v):
        self.__screen = v

    @property
    def log(self):
        if self.__log == 'MAX':
            return self.__format.format(self.max)
        if self.__log == 'MIN':
            return self.__format.format(self.min)
        if self.__log == 'SUM':
            return self.__format.format(self.sum)
        if self.__log == 'AVG':
            return self.__format.format(self.avg)
        return self.__format.format(self.val)

    @log.setter
    def log(self, v):
        self.__log = v

    @property # Getter
    def val(self):
        if self.__func is not None:
            v = self.__func(self.__parameters)
            if v is not None:
                self.val = v                                     # Trigger the setter
        if self.__val is not None:
            return self.__val                                    # __val is the instantaneous value.  It does not take time passed since the last sample into account.

    @val.setter
    def val(self, v):
        if v is not None:
            self.__val = v
            self.__count += 1
            if self.__max is None:
                self.__max = v
            else:
                if v > self.__max:
                    self.__max = v
            if self.__min is None:
                self.__min = v
            else:
                if v < self.__min:
                    self.__min = v
            if type(v) in [float,int]:                           # only number types
                if self.__age is not None:                       # only calculate time shared value if at least one sample has been taken before
                    self.__sum += v * (time() - self.__age)      # Cumulative sum of time calculated value for sums
                self.__avg += v                                  # Cumulative sum of instantaneous values for averaging
            self.__age = time()                                  # Note the current time

    @property
    def max(self):
        return self.__max

    @property
    def min(self):
        return self.__min

    @property
    def len(self):
        return self.__count

    @property
    def sum(self):
        return self.__sum

    @property
    def avg(self):
        if self.__count == 0: return 0
        else: return self.__avg / self.__count

# Contants used in calculations

config = loadConfig()

#FUEL_AIR_RATIO_IDEAL = 14.7
#FUEL_AIR_RATIO_MIN = 25.0                 #Fuel/Air Ratio x:1
#FUEL_AIR_RATIO_MAX = 50.0
#FUEL_DENSITY = 850.8                      #Diesel Fuel Density g/L
#TYRE_WIDTH = 195.0                        #Tyre Width in mm
#ASPECT_RATIO = 0.65                       #Tyre profile
#RIM_SIZE = 15.0                           #Rim size in inches

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
    if r is None: return None
    if r > 12.0 and r < 13.7:
        return '1st'
    if r > 6.2 and r < 7.4:
        return '2nd'
    if r > 3.8 and r < 4.2:
        return '3rd'
    if r > 2.70 and r < 3.1:
        return '4th'
    if r > 2.1 and r < 2.35:
        return '5th'
    return 'Neutal'

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
