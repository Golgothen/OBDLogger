#from gps import *
from time import sleep
from datetime import datetime
#from multiprocessing import Queue, Pipe
#import threading
from general import *
from monitor import Monitor
from logger import DataLogger
import sys, logging

logger = logging.getLogger('root')
logName = (datetime.now().strftime('RUN-%Y-%m-%d')+'.log')
file_handler = logging.FileHandler('./'+logName) # sends output to file
#file_handler = logging.StreamHandler() # sends output to stderr
file_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s - [%(module)s.%(funcName)s:%(lineno)s] %(message)s'))
logger.addHandler(file_handler)

logger.setLevel(logging.INFO)

lastScreenUpdate = datetime.now()
currentIdleScreen = 0
snapshot=dict()

OBD_PORT = '/dev/ttyUSB0'
OBD_BAUD = 38400

SETTINGS_PATH = './settings/'
LOG_PATH = './logs/'
TANK_CAPACITY = 53.0
IDLE_SCREEN_TIME = 10
ODOMETER = 66482.0
TRIP_TIMEOUT = 900


def printIdleScreen():
  global lastScreenUpdate
  global currentIdleScreen

#  os.system('clear')
    
  screentime=datetime.now()-lastScreenUpdate
  if screentime.seconds>=IDLE_SCREEN_TIME:
    currentIdleScreen+=1
    lastScreenUpdate=datetime.now()
  if currentIdleScreen>2:
    currentIdleScreen=0
  if currentIdleScreen==0:
    printTrip()
  elif currentIdleScreen==1:
    if len(tank['AVG_SPEED'])>0:
      printTank()
    else:
      printTrip()
  else:
    if len(history['AVG_SPEED'])>0:
      printHistory()
    else:
      printTrip()

def printTrip():
  sys.stdout.write(' Last Trip:                   ')
  sys.stdout.write('------------------------------')
  sys.stdout.write('         Avg. Speed: {:8.2f} '.format(tripstats['AVG_SPEED']))
  sys.stdout.write('        Avg. L/100K: {:8.2f} '.format(tripstats['AVG_LP100K']))
  sys.stdout.write('  Distance Traveled: {:8,.1f} '.format(tripstats['DISTANCE']))
  sys.stdout.write('      Fuel Consumed: {:8.2f} '.format(tripstats['FUEL']))
  sys.stdout.write('   Avg. Engine Load: {:8.2f} '.format(tripstats['AVG_LOAD']))
  sys.stdout.write('           Duration: {:>8} '.format(formatSeconds(tripstats['DURATION'])))
  sys.stdout.write('          Idle Time: {:>8} '.format(formatSeconds(tripstats['IDLE_TIME'])))
  sys.stdout.flush()

def printHistory():
  sys.stdout.write(' Recorded History:            ')
  sys.stdout.write('------------------------------')
  sys.stdout.write('         Avg. Speed: {:8.2f} '.format(sum(history['AVG_SPEED'])/len(history['AVG_SPEED'])))
  sys.stdout.write('        Avg. L/100K: {:8.2f} '.format(sum(history['AVG_LP100K'])/len(history['AVG_LP100K'])))
  sys.stdout.write('  Distance Traveled: {:8,.1f} '.format(sum(history['DISTANCE'])))
  sys.stdout.write('           Odometer: {:8,.0f} '.format(sum(history['DISTANCE'])+ODOMETER))
  sys.stdout.write('      Fuel Consumed: {:8,.2f} '.format(sum(history['FUEL'])))
  sys.stdout.write('   Avg. Engine Load: {:8.2f} '.format(sum(history['AVG_LOAD'])/len(history['AVG_LOAD'])))
  sys.stdout.write('           Duration: {:>8} '.format(formatSeconds(sum(history['DURATION']))))
  sys.stdout.write('          Idle Time: {:>8} '.format(formatSeconds(sum(history['IDLE_TIME']))))
  sys.stdout.flush()

def printTank():
  sys.stdout.write(' Tank History:                ')
  sys.stdout.write('------------------------------')
  sys.stdout.write('         Avg. Speed: {:8.2f} '.format(sum(tank['AVG_SPEED'])/len(tank['AVG_SPEED'])))
  sys.stdout.write('        Avg. L/100K: {:8.2f} '.format(sum(tank['AVG_LP100K'])/len(tank['AVG_LP100K'])))
  sys.stdout.write('  Distance Traveled: {:8,.1f} '.format(sum(tank['DISTANCE'])))
  sys.stdout.write('           Est. DTE: {:8.1f} '.format((TANK_CAPACITY-sum(tank['FUEL']))/(sum(tank['AVG_LP100K'])/len(tank['AVG_LP100K']))*100 ))
  sys.stdout.write('      Fuel Consumed: {:8.2f} '.format(sum(tank['FUEL'])))
  sys.stdout.write('           Duration: {:>8} '.format(formatSeconds(sum(tank['DURATION']))))
  sys.stdout.write('          Idle Time: {:>8} '.format(formatSeconds(sum(tank['IDLE_TIME']))))
  sys.stdout.flush()

def printFuelTable():
  if snapshot['SPEED']>0:
#    os.system('clear')
    sys.stdout.write('  Time :   L/100K : Fuel(ml) :')
    sys.stdout.write('   Now : {:8,.2f} : {:8,.2f} :'.format(snapshot['FUEL_CONSUMPTION'],snapshot['LPS']))
    sys.stdout.write('   60s : {:8,.2f} : {:8,.2f} :'.format(sensors['FUEL_CONSUMPTION'].avg(60,0),sensors['LPS'].sum(60,0)*1000))
    sys.stdout.write('    5m : {:8,.2f} : {:8,.2f} :'.format(sensors['FUEL_CONSUMPTION'].avg(300,60),sensors['LPS'].sum(300,60)*1000))
    sys.stdout.write('   10m : {:8,.2f} : {:8,.2f} :'.format(sensors['FUEL_CONSUMPTION'].avg(300,360),sensors['LPS'].sum(300,360)*1000))
    sys.stdout.write('   15m : {:8,.2f} : {:8,.2f} :'.format(sensors['FUEL_CONSUMPTION'].avg(300,660),sensors['LPS'].sum(300,660)*1000))
    sys.stdout.write('   30m : {:8,.2f} : {:8,.2f} :'.format(sensors['FUEL_CONSUMPTION'].avg(900,960),sensors['LPS'].sum(900,960)*1000))
    sys.stdout.write('   45m : {:8,.2f} : {:8,.2f} :'.format(sensors['FUEL_CONSUMPTION'].avg(900,1860),sensors['LPS'].sum(900,1860)*1000))
    sys.stdout.write('    1h : {:8,.2f} : {:8,.2f} :'.format(sensors['FUEL_CONSUMPTION'].avg(3600,2760),sensors['LPS'].sum(3600,2760)*1000))
    sys.stdout.write('    2h : {:8,.2f} : {:8,.2f} :'.format(sensors['FUEL_CONSUMPTION'].avg(3600,6360),sensors['LPS'].sum(3600,6360)*1000))

  sys.stdout.flush()

def printFullTable(d):
#  os.system('clear')
  if 'SPEED' in d:
    sys.stdout.write(' Speed : {:4.0f}/{:4.0f}/{:9.2f} :'.format(d['SPEED']['VAL'], d['SPEED']['MAX'], d['SPEED']['AVG']))
  else:
    sys.stdout.write(' Speed :     /    /         :')
  if 'RPM' in d:
    sys.stdout.write('   RPM : {:9,.0f}/{:9,.0f} :'.format(d['RPM']['VAL'], d['RPM']['MAX']))
  else:
    sys.stdout.write('   RPM :          /         :')
  if 'ENGINE_LOAD' in d:
    sys.stdout.write('  Load : {:9.2f}/{:9.2f} :'.format(d['ENGINE_LOAD']['VAL'], d['ENGINE_LOAD']['MAX']))
  else:
    sys.stdout.write('  Load :          /         :')
  if 'SPEED' in d:
    if d['SPEED']['VAL'] == 0:
      if 'LPH' in d:
        sys.stdout.write('   LPH : {:9,.3f}/{:9,.3f} :'.format(d['LPH']['VAL'], d['LPH']['AVG']))
      else:
        sys.stdout.write('   LPH :          /         :')
    else:
      if 'LP100K' in d:
        sys.stdout.write('L/100K : {:9,.3f}/{:9,.3f} :'.format(d['LP100K']['VAL'], d['LP100K']['AVG']))
      else:
        sys.stdout.write('L/100K :          /         :')
  else:
    sys.stdout.write('   LPH :          /         :')
  if 'BOOST_PRESSURE' in d:
    sys.stdout.write(' Boost : {:9.2f}/{:9.2f} :'.format(d['BOOST_PRESSURE']['VAL'], d['BOOST_PRESSURE']['MAX']))
  else:
    sys.stdout.write(' Boost :          /          :')
  if 'COOLANT_TEMP' in d:
    sys.stdout.write('  Temp : {:9}/{:9} :'.format(d['COOLANT_TEMP']['VAL'], d['COOLANT_TEMP']['MAX']))
  else:
    sys.stdout.write('  Temp :          /         :')
  if 'DISTANCE' in d:
    sys.stdout.write('  Trip : {:9,.2f}           :'.format(d['DISTANCE']['SUM']))
  else:
    sys.stdout.write('  Trip :                    :')
  if 'DURATION' in d and 'IDLE_TIME' in d:
    sys.stdout.write('  Time : {:>9}/{:>9} :'.format(formatSeconds(d['DURATION']['SUM']), formatSeconds(d['IDLE_TIME']['SUM'])))
  else:
    sys.stdout.write('  Time :          /         :')
  if 'LPS' in d:
    sys.stdout.write('  Fuel : {:9.2f}           :'.format(d['LPS']['SUM']))
  else:
    sys.stdout.write('  Fuel :                    :')
  if 'GEAR' in d:
    sys.stdout.write('  Gear : {:>9}           :'.format(d['GEAR']['VAL']))
  else:
    sys.stdout.write('  Fuel :                     :')

  sys.stdout.flush()



if __name__ == '__main__':

  tripstats = dict()
  history = dict()
  tank = dict()

  #obd.logger.setLevel(obd.logging.DEBUG)

  try:

    tripstats = readLastTrip(SETTINGS_PATH + 'LastTrip.csv')
    history=readCSV(SETTINGS_PATH + 'TripHistory.csv')
    tank=readCSV(SETTINGS_PATH + 'TankHistory.csv')

    ecu = Monitor(OBD_PORT,OBD_BAUD)
  
    ecu.logPath(LOG_PATH)
    ecu.logHeadings(['TIMESTAMP','RPM','SPEED','DISTANCE','OBD_DISTANCE',
                     'LP100K','LPS','LPH','MAF','ENGINE_LOAD',
                     'BAROMETRIC_PRESSURE','INTAKE_PRESSURE','BOOST_PRESSURE',
                     'DISTANCE_SINCE_DTC_CLEAR','COOLANT_TEMP','DURATION',
                     'IDLE_TIME','EGR_ERROR','COMMANDED_EGR','DISTANCE_W_MIL',
                     'WARMUPS_SINCE_DTC_CLEAR','DRIVE_RATIO','GEAR'])

    ecu.addQue('HI',10)
    ecu.addQue('MED',1)
    ecu.addQue('LOW',0.1)
    ecu.addQue('ONCE',1)

    ecu.deleteAfterPoll('ONCE',True)

    Commands = {'HI'   : ['RPM','SPEED','MAF','ENGINE_LOAD'],
                'MED'  : ['BAROMETRIC_PRESSURE','INTAKE_PRESSURE','COOLANT_TEMP'],
                'LOW'  : ['DISTANCE_SINCE_DTC_CLEAR','DISTANCE_W_MIL','COMMANDED_EGR',
                          'EGR_ERROR'],
                'ONCE' : ['WARMUPS_SINCE_DTC_CLEAR']}

    for q in Commands:
      for c in Commands[q]:
        ecu.addCommand(q, c)


    logger.debug('Starting...')

    disconnected=None
    journey = False
    while 1:
      while ecu.isConnected() == True:
        if not journey:
          journey=True
          ecu.resume()
        print(ecu.status())
        #print(ecu.status()['Worker Status'])
        #printFullTable(ecu.summary)
        sleep(1)
      while not ecu.isConnected():
        if journey: 
          journey=False
          ecu.pause()
          disconnected = datetime.now()
          if ecu.sum('DURATION') == 0:
            ecu.discard()
          else:
            if (datetime.now()-disconnected).total_seconds() > TRIP_TIMEOUT:
              logger.debug('Finalising trip....')
              #tripstats = updateTripStats(kpis)
              #writeTripHistory(SETTINGS_PATH + 'TripHistory.csv',tripstats)
              #writeTripHistory(SETTINGS_PATH + 'TankHistory.csv',tripstats)
              #writeLastTrip(SETTINGS_PATH + 'LastTrip.csv',tripstats)
              history=readCSV(SETTINGS_PATH + 'TripHistory.csv')
              tank=readCSV(SETTINGS_PATH + 'TankHistory.csv')
              disconnected=None
        logger.debug('No ECU fount at {:%H:%M:%S}... Waiting...'.format(datetime.now()))
        #assume engine is off
        #printIdleScreen()
        print(ecu.status())
        #print(ecu.status()['Worker Status'])
        sleep(1)

  except (KeyboardInterrupt, SystemExit):
    ecu.stop()
    print('Done.')

