from multiprocessing import Pipe
from threading import Thread
from messages import Message

import logging


# Watcher thread to monitor for incomming messages on a pipe.
# One thread per pipe.

logger = logging.getLogger('root')


class PipeWatcher(Thread):

    def __init__(self, parent, pipe, name):
        super(PipeWatcher, self).__init__()

        self.__pipe = pipe
        self.__parent = parent
        self.__running = False
        self.name = name
        self.daemon = True

    def run(self):
        self.__running = True
        logger.info('Starting listener thread {}'.format(self.name))
        try:
            while self.__running:
                while self.__pipe.poll(None):  # Block indefinately waiting for a message
                    m = self.__pipe.recv()
                    response = getattr(self.__parent, m.message.lower())(m.params)
                    if response is not None:
                        self.send(response)
        except (KeyboardInterrupt, SystemExit):
            self.__running = False

    # Public method to allow the parent to send messages to the pipe
    def send(self, msg):
        self.__pipe.send(msg)