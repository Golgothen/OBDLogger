from multiprocessing import Process, Event, Queue, current_process
import logging, logging.handlers, logging.config

shared_logging_queue = Queue()

worker_config = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'queue': {
            'class': 'logging.handlers.QueueHandler',
            'queue': shared_logging_queue,
        },
    },
    'loggers': {
        'collector': {
            'level':       'DEBUG',
        },
        'fmt': {
            'level':       'INFO',
        },
        'gps': {
            'level':       'INFO',
        },
        'kpi': {
            'level':       'DEBUG',
        },
        'logger': {
            'level':       'INFO',
        },
        'monitor': {
            'level':       'INFO',
        },
        'pipewatcher': {
            'level':       'INFO',
        },
        'worker': {
            'level':       'INFO',
        },
        'ecu': {
            'level':       'INFO',
        },
        'que': {
            'level':       'INFO',
        },
        'messages': {
            'level':       'INFO',
        },
        'obd': {
            'level':       'ERROR',
        },
        'elm327': {
            'level':       'ERROR',
        },
        'OBDCommand': {
            'level':       'ERROR',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['queue']
    },
}

listener_config = {
    'version': 1,
    'disable_existing_loggers': True,
    'respect_handler_level': True,
    #'filters': {
    #    'usb-unplugged': {
    #        '()': 'queuehandler.obdFilter'
    #        }
    #},
    'formatters': {
        'detailed': {
            'class':       'logging.Formatter',
            'format':      '%(asctime)-16s:%(name)-21s:%(levelname)-8s[%(module)-13s.%(funcName)-20s %(lineno)-5s] %(message)s'
            },
        'brief': {
            'class':       'logging.Formatter',
            'format':      '%(asctime)-16s:%(message)s'
        }
    },
    'handlers': {
        'console': {
            'class':       'logging.StreamHandler',
            'level':       'ERROR',
            'formatter':   'brief'
        },
        #'file': {
        #    'class':       'logging.FileHandler',
        #    'filename':    (datetime.now().strftime('RUN-%Y%m%d')+'.log'),
        #    'mode':        'w',
        #    'formatter':   'detailed',
        #},
        'filerotate': {
            'class':       'logging.handlers.TimedRotatingFileHandler',
            'filename':    'run.log',
            'when':        'midnight',
            'interval':    1,
            'formatter':   'detailed',
            'backupCount': 10
        }
    },
    'root': {
        'handlers':    ['console', 'filerotate'],
    },
}


class MyHandler(object):
    def handle(self, record):
        #print(record.name)
        #print(record)
        logger = logging.getLogger(record.name)
        #record.processName = '%s (for %s)' % (current_process().name, record.processName)
        logger.handle(record)

class LogListener(Process):
    def __init__(self):
        super(LogListener, self).__init__()
        self.__stop_event = Event()
        self.name = 'listener'

    def run(self):
        try:
            logging.config.dictConfig(listener_config)
            logger = logging.getLogger('listener')
            logger.info('Logging system initialised')
            listener = logging.handlers.QueueListener(shared_logging_queue, MyHandler())
            listener.start()
            logger.info('Logging system running')
            self.__stop_event.wait()
            listener.stop()
            logger.info('Logging system stopped')
        except (KeyboardInterrupt, SystemExit):
            listener.stop()
        logger.info('Logging system stopped')

    def stop(self):
        self.__stop_event.set()

