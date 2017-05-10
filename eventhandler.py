from multiprocessing import Event
import _thread

class EventHandler():

    def __init__(self, event, callback, auto_reset = True):
        self.event = event
        self.callback = callback
        self.autoreset = auto_reset
        _thread.start_new_thread(self.__event,())

    def __event(self):
        self.event.wait()
        self.callback()
        if self.autoreset:
            self.event.clear()
            _thread.start_new_thread(self.__event, ())

