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

def printIdleScreen():
    global lastScreenUpdate
    global currentIdleScreen
    global config

    os.system('clear')
    screentime=datetime.now()-lastScreenUpdate
    if screentime.seconds>=config.getfloat('Application', 'Idle Screen Time'):
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
    if sum(tank['AVG_LP100K']) > 0:
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
    sys.stdout.write('   FAM :          /          :')
    sys.stdout.write('  Load :          /          :')
    sys.stdout.write('   MAF :          /          :')
    sys.stdout.write('  Trip :                     :')
    sys.stdout.write('  Time :          /          :')
    sys.stdout.write('  Fuel :          /          :')
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
                        printxy(3, 1, '   LPH')
                        printxy(3, 10, '{:9,.3f}'.format(d['LPH']['VAL']))
                        printxy(3, 20, '{:9,.3f}'.format(d['LPH']['AVG']))
            else:
                if 'LP100K' in d:
                    if d['LP100K']['VAL'] is not None:
                        printxy(3, 1, 'LP100K')
                        printxy(3, 10, '{:9,.3f}'.format(d['LP100K']['VAL']))
                        printxy(3, 10, '{:9,.3f}'.format(d['LP100K']['AVG']))

    if 'RPM' in d:
        if d['RPM']['VAL'] is not None:
            printxy(2 ,10, '{:9,.0f}'.format(d['RPM']['VAL']))
            printxy(2, 20, '{:9,.0f}'.format(d['RPM']['MAX']))

#    if 'BOOST_PRESSURE' in d:
#        if d['BOOST_PRESSURE']['VAL'] is not None:
#            printxy(4, 10, '{:9.2f}'.format(d['BOOST_PRESSURE']['VAL']))
#            printxy(4, 20, '{:9.2f}'.format(d['BOOST_PRESSURE']['MAX']))

    if 'FAM' in d:
        if d['FAM']['VAL'] is not None:
            printxy(4, 10, '{:9.2f}'.format(d['FAM']['VAL']))
            printxy(4, 20, '{:9.2f}'.format(d['FAM']['MAX']))

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
            printxy(6, 10, '{:9.2f}'.format(d['MAF']['VAL']))
            printxy(6, 20, '{:9.2f}'.format(d['MAF']['AVG']))

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

    config = loadConfig()

    try:

        tripstats = readLastTrip(config.get('Application', 'StatPath') + 'LastTrip.csv')
        history = readCSV(config.get('Application', 'StatPath') + 'TripHistory.csv')
        if history is None: history = blankHist()
        tank = readCSV(config.get('Application', 'StatPath') + 'TankHistory.csv')
        if tank is None: tank = blankHist()

        ecu = Monitor(config.get('Application', 'OBD Port'),
                      config.get('Application', 'OBD Baud'))

        ecu.logPath(config.get('Application', 'LogPath'))
        ecu.gpsEnabled = config.getboolean('Application','GPS Enabled')
        logHeadings = config.get('Application', 'Log Headings').split(',')

        for q in config.get('Application', 'Queues').split(','):
            ecu.addQue(q, config.getfloat('Queue {}'.format(q), 'Frequency'))
            if config.has_option('Queue {}'.format(q), 'Delete After Poll'):
                ecu.deleteAfterPoll(q, config.getboolean('Queue {}'.format(q), 'Delete After Poll'))
            if config.has_option('Queue {}'.format(q), 'Commands'):
                for c in config.get('Queue {}'.format(q), 'Commands').split(','):
                    ecu.addCommand(q, c)

        logger.debug('Starting...')

        disconnected=None
        journey = False
        while 1:
            while ecu.isConnected() == True:
                if not journey:
                    journey=True
                    paintFullTable()
                    for q in config.get('Application', 'Queues').split(','):
                        if config.has_option('Queue {}'.format(q), 'Reconfigure on Restart') and \
                           config.has_option('Queue {}'.format(q), 'Commands'):
                            for c in config.get('Queue {}'.format(q), 'Commands').split(','):
                                ecu.addCommand(q, c)
                    sc = None
                    while sc is None:
                        sc = ecu.supportedcommands()
                        sleep(0.01)
                    if config.getboolean('Application', 'Log Extra Data'):
                        loadedCommands = ['STATUS','OBD_COMPLIANCE','STATUS_DRIVE_CYCLE']
                        for q in config.get('Application', 'Queues').split(','):
                            loadedCommands.append(config.get('Queue {}'.format(q),'Commands').split(',')
                        for q in config.get('Application', 'Queues').split(','):
                            if config.has_option('Queue {}'.format(q), 'Default Queue'):
                                for c in sc:
                                    if c not in loadedCommands:
                                        ecu.addCommand(q,c)                     # Add all supported commands that arent already in a que to the LOW que
                                        logHeadings.append(c)                       # Add any added commands to the log headings so they get logged
                    ecu.logHeadings(logHeadings)
                    ecu.resume()
                logger.info(ecu.status())
                printFullTable(ecu.snapshot)
                sleep(config.getfloat('Application', 'Busy Screen Time'))
            while not ecu.isConnected():
                if journey:
                    journey=False
                    ecu.pause()
                    disconnected = datetime.now()
                    if ecu.sum('DURATION') == 0:
                        ecu.discard()
                    else:
                        tripstats = ecu.summary
                        writeLastTrip(config.get('Application', 'StatPath') + 'LastTrip.csv', tripstats)
                if disconnected is not None:
                    if (datetime.now()-disconnected).total_seconds() > config.getfloat('Application', 'Trip Timeout'):
                        ecu.save()
                        logger.info('Finalising trip....')
                        writeTripHistory(config.get('Application', 'StatPath') + 'TripHistory.csv', tripstats)
                        writeTripHistory(config.get('Application', 'StatPath') + 'TankHistory.csv', tripstats)
                        history=readCSV(config.get('Application', 'StatPath') + 'TripHistory.csv')
                        tank=readCSV(config.get('Application', 'StatPath') + 'TankHistory.csv')
                        disconnected = None
                        ecu.reset()
                logger.debug('No ECU fount at {:%H:%M:%S}... Waiting...'.format(datetime.now()))
                #assume engine is off
                printIdleScreen()
                logger.info(ecu.status())
                sleep(1)

    except (KeyboardInterrupt, SystemExit):
        ecu.stop()
        print('Done.')

