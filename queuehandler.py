from multiprocessing import Queue, Process

import logging, logging.handlers, logging.config #, logging.Filter

class QueueHandler(logging.Handler):

    def __init__(self, queue):
        logging.Handler.__init__(self)
        self.queue = queue

    def emit(self, record):
        try:
            ei = record.exc_info
            if ei:
                dummy = self.format(record) # just to get traceback text into record.exc_text
                record.exc_info = None  # not needed any more
            self.queue.put_nowait(record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

class LogListener(Process):

    def __init__(self, queue, config):
        super(LogListener, self).__init__()
        self.__queue = queue
        self.deamon = True
        self.config = config

    def run(self):
        logging.config.dictConfig(self.config)
        root = logging.getLogger()
        self.running = True
        while True:
            try:
                record = self.__queue.get()
                if record is None:
                    break
                logger = logging.getLogger(record.name)
                logger.handle(record)
            except (KeyboardInterrupt, SystemExit):
                break
            except:
                import sys, traceback
                print >> sys.stderr, 'Error in logging process!'
                traceback.print_exc(file=sys.stderr)

    def stop(self):
        self.__queue.put(None)

class obdFilter(logging.Filter):

    def filter(self, record):
        if record.getMessage().startswith('[Errno 2] could not open port'):
            return False
        if record.getMessage().startswith('Cannot load commands: No connection to car'):
            return False
        return True
