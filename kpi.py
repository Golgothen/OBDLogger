from time import time
from datetime import datetime

import logging

logger = logging.getLogger('root')

class KPI(object):

  def __init__(self,**kwargs):
    self._parameters = dict()
    self._func = None
    for k in kwargs:
      if k == 'FUNCTION':
        self._func=kwargs[k]
      else:
        self._parameters[k]=kwargs[k]
    self._min=None
    self._max=None
    self._hist=[]
    self._age=None
    self.timeSensitive=False

  @property
  def val(self):
    if self._func is not None:
      v=self._func(self._parameters)
      self.val=v
    if len(self._hist)>0:
      return self._hist[0]

  @val.setter
  def val(self,v):
    if v is not None:
      if self.timeSensitive:
        if self._age is None:
          self._age = 1
        else:
          v=v*(time()-self._age)
          self._age=time()
      self._hist.insert(0,v)
      if self._max is None:
        self._max=v
      else:
        if v > self._max:
          self._max=v
      if self._min is None:
        self._min=v
      else:
        if v < self._min:
          self._min=v

  @property
  def max(self):
    return self._max

  @property
  def min(self):
    return self._min

  @property
  def len(self):
    return len(self._hist)

  def sum(self,period=0,offset=0):
    period=abs(period)
    offset=abs(offset)
    if period == 0 and offset == 0: return float(sum(self._hist))
    return float(sum(self._hist[offset:offset+period]))

  def avg(self,period=0, offset = 0):
    period=abs(period)
    offset=abs(offset)
    if period == 0 and offset == 0:
      if len(self._hist)==0: return 0.0
      return float(sum(self._hist)/len(self._hist))
    if len(self._hist[offset:offset+period])==0: return 0.0
    else: return float(sum(self._hist[offset:offset+period]))/float(len(self._hist[offset:offset+period]))

#  def reset(self):
#    self._hist=[]

#  def addParameters(self, **kwargs):
#    for k in kwargs:
#      self._parameters[k]=kwargs[k]

FUEL_AIR_RATIO_IDEAL = 14.7
FUEL_AIR_RATIO_MIN = 25.0         #Fuel/Air Ratio x:1
FUEL_AIR_RATIO_MAX = 50.0
FUEL_DENSITY = 850.8              #Diesel Fuel Density g/L
TYRE_WIDTH = 195.0                #Tyre Width in mm
ASPECT_RATIO = 0.65               #Tyre profile
RIM_SIZE = 15.0                   #Rim size in inches

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
  if s == 0: return None                           #Avoid Divide by Zero
  sideWall=TIRE_WIDTH * ASPECT_RATIO               # in mm
  wheelDiameter = sideWall + (RIM_SIZE * 25.4)     # in mm
  whelCirc = wheelDiameter * 3.14159 / 1000.0      # in m
  wheel_rpm = s*1000.0/60/wheel_circ               # in rpm
  return r / wheel_rpm                             # ratio Engine RPM : Wheel RPM

def LPH(p):
  if 'LPS' not in p: return None
  l = p['LPS'].val
  if l is None: return None
  return l * 3600

def LPS(p):
  if 'MAF' not in p or 'ENGINE_LOAD' not in p: return None
  m = p['MAF'].val
  e = p['ENGINE_LOAD'].val
  if m is None or e is None: return None
  if e == 0: return 0.0
  if m == 0: return None
  return m/(FUEL_AIR_RATIO_MAX - ((FUEL_AIR_RATIO_MAX-FUEL_AIR_RATIO_MIN)*(e/100.0)))/FUEL_DENSITY

def LP100K(p):
  #Fuel Consumption in L/100K
  #Depends on Air/Fuel Mixture.  Diesel is documented at 14.7:1
  #Needs to be attaqched to Speed and MAF sensors
  if 'LPH' not in p or 'SPEED' not in p: return None
  l = p['LPH'].val
  s = p['SPEED'].avg(5)
  if l is None or s is None: return None
  if s == 0: return 0
  return 100.0/s*l

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
  d = p['SPEED'].avg(5)
  if d is None: return None
  return d/3600

def OBDdistance(p):
  if 'DISTANCE_SINCE_DTC_CLEAR' not in p: return None
  d = p['DISTANCE_SINCE_DTC_CLEAR'].val
  if d is None: return None
  return d-p['DISTANCE_SINCE_DTC_CLEAR'].min

def gear(p):
  if 'DRIVE_RATIO' not in p: return None
  r=p['DRIVE_RATIO'].val
  if r is None: return None
  if r > 13.5 and r < 17.2:
    return "1st"
  if r > 7.4 and r < 9.1:
    return "2nd"
  if r > 4.7 and r < 5.8:
    return "3rd"
  if r > 3.2 and r < 3.9:
    return "4th"
  if r > 2.3 and r < 2.9:
    return "5th"
  return "Neutal"

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
