from mplogger import *
# Configure and start the logging listener process
listener = LogListener()
listener.start()

logging.config.dictConfig(worker_config)
logger = logging.getLogger('application')

from time import sleep, time
from datetime import datetime
from monitor import Monitor
from logger import DataLogger
from configparser import ConfigParser
from threading import Timer

import sys

from general import *


if __name__ == '__main__':

    # Start the log listener
    logging.config.dictConfig(worker_config)
    logger = logging.getLogger()


    #logger.setLevel(logging.INFO)


    config = loadConfig()

    try:
        ecu = Monitor()

        ecu.logPath(config.get('Application', 'LogPath'))
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
        t = time()
        while True:
            while time() - t < 60: #ecu.isConnected:
                print('Running connected loop {}'.format(time() - t))
                if not journey:
                    journey=True
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
                #logger.info(ecu.status['GPS'])
                sleep(config.getfloat('Application', 'Busy Screen Time'))
            #while not ecu.isConnected:
            while time() - t > 60: #ecu.isConnected:
                print('Running disconnected loop {}'.format(time() - t))
                if (time() - t) > 70:
                    t = time()
                if journey:
                    journey=False
                    ecu.pause()
                    disconnected = datetime.now()
                    if ecu.sum('DURATION') != 0:
                        ecu.discard()
                        disconnected = None
                    else:
                        tripstats = ecu.summary
                        writeLastTrip(config.get('Application', 'StatPath') + 'LastTrip.csv', tripstats)
                if disconnected is not None:
                    if (datetime.now()-disconnected).total_seconds() > config.getfloat('Application', 'Trip Timeout'):
                        ecu.save()
                        logger.info('Finalising trip....')
                        disconnected = None
                        ecu.reset()
                logger.debug('No ECU fount at {:%H:%M:%S}... Waiting...'.format(datetime.now()))
                #assume engine is off
                #logger.info(ecu.status())
                sleep(0.1)

    except (KeyboardInterrupt, SystemExit):
        ecu.pause()
        ecu.save()
        ecu.stop()
        listener.stop()
        listener.join()
        print('Done.')

