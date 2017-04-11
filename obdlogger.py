from time import sleep
from datetime import datetime
from general import *
from monitor import Monitor
from logger import DataLogger
import sys, logging
logger = logging.getLogger('root')
logName = (datetime.now().strftime('RUN-%Y-%m-%d')+'.log')
file_handler = logging.FileHandler('./'+logName) # sends output to file
#file_handler = logging.StreamHandler() # sends output to stderr
file_handler.setFormatter(logging.Formatter('%(asctime)-16s:%(levelname)-8s[%(module)-10s.%(funcName)-17s:%(lineno)-5s] %(message)s'))
logger.addHandler(file_handler)

logger.setLevel(logging.WARNING)

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

<<<<<<< HEAD
=======
GPS_ENABLE = False

>>>>>>> f000669c6c6a71b2a7ef7418b2439fff8d185c3f
def printIdleScreen():
    global lastScreenUpdate
    global currentIdleScreen

    os.system('clear')
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

def paintFullTable():
    os.system('clear')
    # paint the screen
    sys.stdout.write(' Speed :     /    /          :')
    sys.stdout.write('   RPM :          /          :')
    sys.stdout.write('   LPH :          /          :')
    sys.stdout.write(' Boost :          /          :')
    sys.stdout.write('  Load :          /          :')
    sys.stdout.write('   MAF :          /          :')
    sys.stdout.write('  Trip :                     :')
    sys.stdout.write('  Time :          /          :')
    sys.stdout.write('  Fuel :                     :')
    sys.stdout.write('  Gear :          /          :')
    sys.stdout.flush()

def printFullTable(d):
    if 'SPEED' in d:
        if d['SPEED']['VAL'] is not None:
            printxy(1,10,'{:4.0f}'.format(d['SPEED']['VAL']))
            printxy(1,15,'{:4.0f}'.format(d['SPEED']['MAX']))
            printxy(1,20,'{:9.2f}'.format(d['SPEED']['AVG']))
            if d['SPEED']['VAL'] == 0:
                if 'LPH' in d:
                    if d['LPH']['VAL'] is not None:
                        printxy(3, 1, '   LPH :')
                        printxy(3, 10, '{:9,.3f}'.format(d['LPH']['VAL']))
                        printxy(3, 20, '{:9,.3f}'.format(d['LPH']['AVG']))
            else:
                if 'LP100K' in d:
                    if d['LP100K']['VAL'] is not None:
                        printxy(3, 1, 'LP100K :')
                        printxy(3, 10, '{:9,.3f}'.format(d['LP100K']['VAL']))
                        printxy(3, 10, '{:9,.3f}'.format(d['LP100K']['AVG']))
    if 'RPM' in d:
        if d['RPM']['VAL'] is not None:
            printxy(2 ,10, '{:9,.0f}'.format(d['RPM']['VAL']))
            printxy(2, 20, '{:9,.0f}'.format(d['RPM']['MAX']))
    if 'BOOST_PRESSURE' in d:
        if d['BOOST_PRESSURE']['VAL'] is not None:
            printxy(4, 10, '{:9.2f}'.format(d['BOOST_PRESSURE']['VAL']))
            printxy(4, 20, '{:9.2f}'.format(d['BOOST_PRESSURE']['MAX']))
    if 'ENGINE_LOAD' in d:
        if d['ENGINE_LOAD']['VAL'] is not None:
            printxy(5, 10, '{:9.2f}'.format(d['ENGINE_LOAD']['VAL']))
            printxy(5, 20, '{:9.2f}'.format(d['ENGINE_LOAD']['MAX']))
#    if 'COOLANT_TEMP' in d:
#        if d['COOLANT_TEMP']['VAL'] is not None:
#            printxy(6, 10, '{:9}'.format(d['COOLANT_TEMP']['VAL']))
#            printxy(6, 20, '{:9}'.format(d['COOLANT_TEMP']['MAX']))
    if 'MAF' in d:
        if d['MAF']['VAL'] is not None:
            printxy(6, 10, '{:9}'.format(d['MAF']['VAL']))
            printxy(6, 20, '{:9}'.format(d['MAF']['AVG']))
    if 'DISTANCE' in d:
        if d['DISTANCE']['VAL'] is not None:
            printxy(7, 10, '{:9,.2f}'.format(d['DISTANCE']['SUM']))
    if 'DURATION' in d and 'IDLE_TIME' in d:
        if d['DURATION']['VAL'] is not None and \
           d['IDLE_TIME']['VAL'] is not None:
            printxy(8, 10, '{:>9}'.format(formatSeconds(d['DURATION']['SUM'])))
            printxy(8, 20, '{:>9}'.format(formatSeconds(d['IDLE_TIME']['SUM'])))
    if 'LPS' in d:
        if d['LPS']['VAL'] is not None:
            printxy(9, 10, '{:9.2f}'.format(d['LPS']['SUM']))
            printxy(9, 20, '{:9.2f}'.format(d['LPS']['VAL']))
    if 'GEAR' in d:
        if d['GEAR']['VAL'] is not None and \
           d['DRIVE_RATIO']['VAL'] is not None:
            printxy(10, 10, '{:>9}'.format(d['GEAR']['VAL']))
            printxy(10, 20, '{:9.2f}'.format(d['DRIVE_RATIO']['VAL']))
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

        ecu.gpsEnable = GPS_ENABLE

        ecu.logPath(LOG_PATH)
        logHeadings = ['TIMESTAMP','RPM','SPEED','DISTANCE','OBD_DISTANCE',
                       'LP100K','LPS','LPH','MAF','ENGINE_LOAD',
                       'BAROMETRIC_PRESSURE','INTAKE_PRESSURE','BOOST_PRESSURE',
                       'DISTANCE_SINCE_DTC_CLEAR','COOLANT_TEMP','DURATION',
                       'IDLE_TIME','EGR_ERROR','COMMANDED_EGR','DISTANCE_W_MIL',
                       'WARMUPS_SINCE_DTC_CLEAR','DRIVE_RATIO','GEAR']

        ecu.addQue('HI',10)
        ecu.addQue('MED',1)
        ecu.addQue('LOW',0.1)
        ecu.addQue('ONCE',1)

        ecu.deleteAfterPoll('ONCE',True)

        Commands = {'HI'  : ['RPM','SPEED','MAF','ENGINE_LOAD'],
                    'MED' : ['BAROMETRIC_PRESSURE','INTAKE_PRESSURE','COOLANT_TEMP'],
                    'LOW' : ['DISTANCE_SINCE_DTC_CLEAR','DISTANCE_W_MIL','COMMANDED_EGR',
                             'EGR_ERROR'],
                    'ONCE' : ['WARMUPS_SINCE_DTC_CLEAR']}

        for q in Commands:
            for c in Commands[q]:
                ecu.addCommand(q, c)

        ecu.GPSEnable = False

        logger.debug('Starting...')

        disconnected=None
        journey = False
        while 1:
            while ecu.isConnected() == True:
                if not journey:
                    journey=True
                    paintFullTable()
                    l = ecu.getQueCommands('ONCE')
                    for c in Commands['ONCE']:                          # Add all the ONCE commands back into the ONCE que if they do not already exist
                        if c not in l:
                            ecu.addCommand('ONCE',c)
                    sc = None
                    while sc is None:
                        sc = ecu.supportedcommands()
                        sleep(0.01)
                    for c in sc:
                        if c not in ['STATUS','OBD_COMPLIANCE','STATUS_DRIVE_CYCLE'] + Commands['HI'] + Commands['MED'] + Commands['LOW'] + Commands['ONCE']:
                            Commands['LOW'].append(c)
                            ecu.addCommand('LOW',c)                     # Add all supported commands that arent already in a que to the LOW que
                            logHeadings.append(c)                       # Add any added commands to the log headings so they get logged
                    ecu.logHeadings(logHeadings)
                    ecu.resume()
                logger.info(ecu.status())
                printFullTable(ecu.snapshot)
                sleep(0.25)
            while not ecu.isConnected():
                if journey:
                    journey=False
                    ecu.pause()
                    disconnected = datetime.now()
                    if ecu.sum('DURATION') == 0:
                        ecu.discard()
                    else:
                        tripstats = ecu.summary
                if disconnected is not None:
                    if (datetime.now()-disconnected).total_seconds() > TRIP_TIMEOUT:
                        logger.info('Finalising trip....')
                        writeTripHistory(SETTINGS_PATH + 'TripHistory.csv', tripstats)
                        writeTripHistory(SETTINGS_PATH + 'TankHistory.csv', tripstats)
                        writeLastTrip(SETTINGS_PATH + 'LastTrip.csv', tripstats)
                        history=readCSV(SETTINGS_PATH + 'TripHistory.csv')
                        tank=readCSV(SETTINGS_PATH + 'TankHistory.csv')
                        disconnected=None
                logger.debug('No ECU fount at {:%H:%M:%S}... Waiting...'.format(datetime.now()))
                #assume engine is off
                printIdleScreen()
                logger.info(ecu.status())
                sleep(1)

    except (KeyboardInterrupt, SystemExit):
        ecu.stop()
        print('Done.')

