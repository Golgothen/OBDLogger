from gps import GPS
from multiprocessing import Queue, Pipe
from messages import Message
from time import sleep, time
from math import modf

import logging

logger = logging.getLogger('root')
file_handler = logging.StreamHandler()
file_handler.setFormatter(logging.Formatter('%(asctime)-16s:%(levelname)-8s[%(module)-12s.%(funcName)-20s:%(lineno)-5s] %(message)s'))
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)


def formatLatitude(d):
    if d is None: return ''
    if d < 0: heading = 'S'
    elif d == 0: heading = '0'
    else: heading = 'N'
    minor, deg = modf(abs(d))
    minor, min = modf(minor*60)
    sec = minor * 60
    deg_sign = u'\N{DEGREE SIGN}'
    return '{:3.0f}{}{:2.0f}\'{:2.2f}"{}'.format(deg, deg_sign, min, sec, heading)

def formatLongitude(d):
    if d is None: return ''
    if d < 0: heading = 'E'
    elif d == 0: heading = '0'
    else: heading = 'W'
    minor, deg = modf(abs(d))
    minor, min = modf(minor*60)
    sec = minor * 60
    deg_sign = u'\N{DEGREE SIGN}'
    return '{:3.0f}{}{:2.0f}\'{:2.2f}"{}'.format(deg, deg_sign, min, sec, heading)




if __name__ == '__main__':
    pipeOut, pipeIn = Pipe()
    q = Queue()

    g = GPS(q, pipeOut)
    g.start()
    #sleep(2)
    data = {}
    headings = ['LATITUDE','LONGITUDE','GPS_SPD','HEADING','ALTITUDE']
    outfile = open('test.txt',mode = 'wt', buffering = 1, encoding = 'UTF-8')
    l = ''
    for h in headings:
        l += '{},'.format(h)
    outfile.write('{}\n'.format(l[:len(l)-1]))

    pipeIn.send(Message('RESUME'))

    try:
        t = time()
        while True:
            while q.qsize() > 0:
                m = q.get()
                print(m.message)
                print(m.params)
                data[m.message] = None if type(m.params['VALUE']) not in [float, int] else m.params['VALUE']
            if time() - t > 1.0:
                l = ''
                for h in headings:
                    print(data)
                    if h in data:
                        if h == 'LATITUDE':
                            l += '{},'.format(formatLatitude(data[h]))
                        elif h == 'LONGITUDE':
                            l += '{},'.format(formatLongitude(data[h]))
                        else:
                            l += '{},'.format(data[h])
                    else:
                        l += '-,'
                outfile.write('{}\n'.format(l[:len(l)-1]))
                t = time()
            sleep(0.1)
    except (KeyboardInterrupt):
        outfile.close()
        pipeIn.send(Message('STOP'))


