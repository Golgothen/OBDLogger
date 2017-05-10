from time import sleep
from datetime import datetime
from general import *
from monitor import Monitor
from logger import DataLogger
from configparser import ConfigParser
from threading import Timer
from multiprocessing import Queue
from queuehandler import LogListener, QueueHandler

import sys, logging

# Configuration for the listener
log_config = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'detailed': {
            'class': 'logging.Formatter',
            'format': '%(asctime)-16s:%(levelname)-8s[%(module)-12s.%(funcName)-20s:%(lineno)-5s] %(message)s'
            },
        'brief': {
            'class': 'logging.Formatter',
            'format': '%(asctime)-16s: %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'CRITICAL',
            'formatter': 'detailed'
        },
        'debug-file': {
            'class': 'logging.FileHandler',
            'filename': (datetime.now().strftime('RUN-%Y%m%d')+'.log'),
            'mode': 'w',
            'formatter': 'detailed',
            'level': 'DEBUG'
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'RUN.log',
            'mode': 'w',
            'formatter': 'detailed',
            'level': 'ERROR'
        }
    },
    'loggers': {
        'root': {
            'handlers': ['console', 'file']
        },
    }
}

# Start the log listener
logQueue = Queue()
listener = LogListener(logQueue, log_config)
listener.start()

# Configure logger for the rest of the application
logger = logging.getLogger('root')
logger.addHandler(QueueHandler(logQueue))
logger.setLevel(logging.DEBUG)

currentIdleScreen = 0
snapshot=dict()
timer = None

def printIdleScreen():
    global lastScreenUpdate
    global currentIdleScreen
    global config
    global timer

    #os.system('clear')
    currentIdleScreen+=1
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
    timer = Timer(config.getfloat('Application', 'Idle Screen Time'), printIdleScreen)
    timer.start()

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
    sys.stdout.write('           Odometer: {:8,.0f} '.format(sum(history['DISTANCE'])+config.getfloat('Vehicle', 'Odometer')))
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
        sys.stdout.write('           Est. DTE: {:8.1f} '.format((config.getfloat('Vehicle', 'Tank Capacity')-sum(tank['FUEL']))/(sum(tank['AVG_LP100K'])/len(tank['AVG_LP100K']))*100 ))
    sys.stdout.write('      Fuel Consumed: {:8.2f} '.format(sum(tank['FUEL'])))
    sys.stdout.write('           Duration: {:>8} '.format(formatSeconds(sum(tank['DURATION']))))
    sys.stdout.write('          Idle Time: {:>8} '.format(formatSeconds(sum(tank['IDLE_TIME']))))
    sys.stdout.flush()

def printFullTable():
    lines = []
    for l in range(config.getint('Application','Data Screen Size')):
        if config.has_option('Data Screen','Line {}'.format(l)):
            if config.get('Data Screen','Line {}'.format(l)) == 'LP100K':
                if ecu.val('SPEED') == 0:
                    lines.append(ecu.dataLine('LPH'))
                else:
                    lines.append(ecu.dataLine('LP100K'))
            else:
                lines.append(ecu.dataLine(config.get('Data Screen','Line {}'.format(l))))
    #os.system('clear')
    for l in lines:
        sys.stdout.write(l)
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

        printIdleScreen()

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
            while ecu.isConnected:
                if not journey:
                    journey=True
                    timer.cancel()
                    for q in config.get('Application', 'Queues').split(','):
                        if config.has_option('Queue {}'.format(q), 'Reconfigure on Restart') and \
                           config.has_option('Queue {}'.format(q), 'Commands'):
                            for c in config.get('Queue {}'.format(q), 'Commands').split(','):
                                ecu.addCommand(q, c)
                    sc = None
                    while sc is None:
                        sc = ecu.supportedCommands
                        sleep(0.01)
                    if config.getboolean('Application', 'Log Extra Data'):
                        loadedCommands = ['STATUS','OBD_COMPLIANCE','STATUS_DRIVE_CYCLE']
                        for q in config.get('Application', 'Queues').split(','):
                            for c in config.get('Queue {}'.format(q),'Commands').split(','):
                                loadedCommands.append(c)
                        for q in config.get('Application', 'Queues').split(','):
                            if config.has_option('Queue {}'.format(q), 'Default Queue'):
                                for c in sc:
                                    if c not in loadedCommands:
                                        ecu.addCommand(q, c)                     # Add all supported commands that arent already in a que to the LOW que
                                    if c not in logHeadings:
                                        logHeadings.append(c)                    # Add any added commands to the log headings so they get logged
                                break
                    ecu.logHeadings(logHeadings)
                    ecu.resume()
                #logger.info(ecu.status())
                printFullTable()
                sleep(config.getfloat('Application', 'Busy Screen Time'))
            while not ecu.isConnected:
                if journey:
                    journey=False
                    printIdleScreen()
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
                #logger.info(ecu.status())
                sleep(0.1)

    except (KeyboardInterrupt, SystemExit):
        listener.stop()

        ecu.stop()
        timer.cancel()
        print('Done.')

