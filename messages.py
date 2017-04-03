from multiprocessing import Pipe
import logging

logger = logging.getLogger('root')

class PipeCont():
  def __init__(self):
    self.s, self.r = Pipe()

class Message():
  def __init__(self, message, **kwargs):
    self.message = message
    self.params = dict()
    for k in kwargs:
      self.params[k] = kwargs[k]
    logger.debug("Message: " + str(self.message) + " : " + str(self.params))
