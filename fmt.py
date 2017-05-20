from general import *
from datetime import datetime
#import logging

#logger = logging.getLogger('obdlogger').getChild(__name__)

class FMT():

    def __init__(self, **kwargs):
        # Set the defaults
        self.length = 9
        self.precision = 2
        self.type = 'f'
        self.alignment = '>'
        self.commas = True
        self.truncate = True
        self.none = '- '

        for k in kwargs:
            if k == 'LENGTH':
                self.length = kwargs[k]
            if k == 'PRECISION':
                self.precision = kwargs[k]
            if k == 'TYPE':
                self.type = kwargs[k]
            if k == 'ALIGNMENT':
                self.alignment = kwargs[k]
            if k == 'COMMAS':
                self.commas = kwargs[k]
            if k == 'TRUNCATE':
                self.truncate = kwargs[k]
            if k == 'NONE':
                self.none = kwargs[k]
        if self.type in ['s','d','t','lat','lon']:
            self.commas = False
        if self.type in ['s','t','lat','lon']:
            self.precision = None

    @property
    def fmtstr(self):
        str = '{:'
        if self.type in ['s','d','t','lat','lon']:
            str += self.alignment
        str += '{}'.format(self.length)
        if self.commas:
            str+=','
        if self.precision is not None and self.type != 'd':
            str += '.{}'.format(self.precision)
        if self.type not in ['s','t','d','lat','lon']:
            str+='{}'.format(self.type)
        str += '}'
        return str

    def __call__(self, v):
        ##logger.debug('Type = {}'.format(self.type))
        if v is None:                                             # Null values
            return ' ' * (self.length - len(self.none)) + self.none
        if self.type == 'd' and type(v) is datetime:              # Dates
            return self.fmtstr.format(v.strftime(self.precision)) # Return it immediately. No firther processing required
        elif self.type == 't':                                    # Time counters
            return self.fmtstr.format(formatSeconds(v))           # Return it immediately. No further processing required
        elif self.type == 'lat':                                  # Latitude
            #logger.debug(self.fmtstr)
            return self.fmtstr.format(formatLatitude(v))          # Return it immediately. No further processing required
        elif self.type == 'lon':                                  # Longitude
            #logger.debug(self.fmtstr)
            return self.fmtstr.format(formatLongitude(v))         # Return it immediately. No further processing required
        else:                                                     # everything else
            if type(v) in [float, int]:
                tmp = self.fmtstr.format(v)
            else:
                self.type = 's'
                self.precision = None
                tmp = self.fmtstr.format(v)
        if len(tmp) > self.length\
           and self.precision is not None\
           and self.truncate:                                     # String is too long.  See if we can drop some precision to get it to fit
            c = self.commas                                       # Store commas so we can reset it
            p = self.precision                                    # store the presisopn so we can reset it later
            while len(tmp) > self.length \
              and self.precision > 0:
                self.precision -= 1
                #print(self.fmtstr)
                tmp = self.fmtstr.format(v)
            # Still too long and no more precision to remove.
            # if the number contains commas, try removing those next
            if self.precision == 0 and \
               len(tmp) > self.length and \
               ',' in tmp:
                self.commas = False
                tmp = self.fmtstr.format(v)
            self.precision = p
            self.commas = c
        return tmp

    def clone(self):
        return FMT(LENGTH = self.length,
                   PRECISION = self.precision,
                   TYPE = self.type,
                   ALIGNMENT = self.alignment,
                   COMMAS = self.commas,
                   TRUNCATE = self.truncate,
                   NONE = self.none)
