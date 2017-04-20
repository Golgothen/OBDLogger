import os, csv, logging, sys
from configparser import ConfigParser

###

# General Functions

###

def formatSeconds(d):
    hours, remainder = divmod(d, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 99:
        days,hours = divmod(hours, 24)
        return '{:02.0f}d{:02.0f}:{:02.0f}'.format(days, hours, minutes)
    return '{:02.0f}:{:02.0f}:{:02.0f}'.format(hours, minutes, seconds)

def readCSV(file):
    if os.path.isfile(file):
        data = dict()
        try:
            with open(file) as f:
                reader = csv.reader(f)
                headings = next(reader)
                for h in headings:
                    data[h] = []
                for row in reader:
                    for h, v in zip(headings, row):
                        if h == 'DATE':
                            data[h].append(v)
                        else:
                            data[h].append(float(v))
            return data
        except:
            data=None
            #Nulls in file causes CSV reader to fail
            #Recreate the file stripping out all nulls
            with open(file,'rb') as f:
                data=f.read()
            with open(file,'wb') as f:
                f.write(data.replace('\x00',''))
            #Try again
            return readCSV(file)
    else:
        return None

def readLastTrip(file):
    data = dict()
    headings = ['AVG_LP100K', 'DISTANCE', 'AVG_SPEED', 'FUEL', 'AVG_LOAD', 'DURATION', 'IDLE_TIME']
    if os.path.isfile(file):
        with open(file) as f:
            reader = csv.DictReader(f, fieldnames = headings)
            for row in reader:
                for h in row:
                    data[h] = float(row[h])
    else:
        for h in headings:
            data[h] = 0.0
    return data

def writeLastTrip(file,data):
    # Check the output directory exists.  Create it if it doesn't
    if not os.path.isdir(os.path.split(file)[0]):
        os.makedirs(os.path.split(file)[0])
    with open(file,'wb') as f:
        f.write(bytes(
            str(data['AVG_LP100K']) + ',' +
            str(data['DISTANCE']) + ',' +
            str(data['AVG_SPEED']) + ',' +
            str(data['FUEL']) + ',' +
            str(data['AVG_LOAD']) + ',' +
            str(data['DURATION']) + ',' +
            str(data['IDLE_TIME']) + '\n',
        'UTF-8'))

def writeTripHistory(file,data):
    # Check the output directory exists.  Create it if it doesn't
    if not os.path.isdir(os.path.split(file)[0]):
        os.makedirs(os.path.split(file)[0])
    writeheaders = False
    if not os.path.isfile(file):
        writeheaders = True
    with open(file,'ab') as f:
        if writeheaders:
            f.write(bytes('DATE,AVG_LP100K,DISTANCE,AVG_SPEED,FUEL,AVG_LOAD,DURATION,IDLE_TIME\n', 'UTF-8'))
        f.write(bytes(
            str(data['DATE']) + ',' +
            str(data['AVG_LP100K']) + ',' +
            str(data['DISTANCE']) + ',' +
            str(data['AVG_SPEED']) + ',' +
            str(data['FUEL']) + ',' +
            str(data['AVG_LOAD']) + ',' +
            str(data['DURATION']) + ',' +
            str(data['IDLE_TIME']) + '\n',
        'UTF-8'))

def printxy(x, y, text):
    sys.stdout.write("\x1b7\x1b[%d;%df%s\x1b8" % (x, y, text))
    sys.stdout.flush()

def blankHist():
    h = {}
    h['AVG_SPEED'] = [0.0]
    h['AVG_LP100K'] = [0.0]
    h['DISTANCE'] = [0.0]
    h['FUEL'] = [0.0]
    h['AVG_LOAD'] = [0.0]
    h['DURATION'] = [0.0]
    h['IDLE_TIME'] = [0.0]
    return h

def loadConfig():
    config = loadDefaults()
    config.read('obdlogger.cfg')
    return config

def loadDefaults():
    config = ConfigParser()
    config.add_section('Application')
    config.add_section('Vehicle')

    config.set('Application','LogPath','./logs/')
    config.set('Application','Log Frequency','1')
    config.set('Application','StatPath','./stats/')
    config.set('Application','Idle Screen Time','10')
    config.set('Application','Busy Screen Time','0.25')
    config.set('Application','Trip Timeout','900')
    config.set('Application','Log Extra Data','False')
    config.set('Application','OBD Port','/dev/ttyUSB0')
    config.set('Application','OBD Baud','38400')
    config.set('Application','Queues','Hi,Medium,Low,Once')
    config.set('Application','Log Headings','TIMESTAMP,RPM,SPEED,DISTANCE,FAM,LP100K,LPS,LPH,MAF,ENGINE_LOAD,DRIVE_RATIO,GEAR')
    config.set('Application','Pipe Timeout','3')

    for q in config.get('Application','Queues').split(','):
        config.add_section('Queue {}'.format(q))

    config.set('Vehicle','Tank Capacity','53')
    config.set('Vehicle','Odometer','73540')
    config.set('Vehicle','Fuel Air Ratio Ideal','14.7')
    config.set('Vehicle','Fuel Air Ratio Min','25')
    config.set('Vehicle','Fuel Air Ratio Max','50')
    config.set('Vehicle','Fuel Density','850.8')
    config.set('Vehicle','Tyre Width','195')
    config.set('Vehicle','Aspect Ratio','65')
    config.set('Vehicle','Rim Size','15')

    config.set('Queue Hi','Frequency','10.0')
    config.set('Queue Hi','Commands','RPM,SPEED,MAF,ENGINE_LOAD')
    config.set('Queue Medium','Frequency','1.0')
    config.set('Queue Medium','Commands','BAROMETRIC_PRESSURE,INTAKE_PRESSURE,COOLANT_TEMP')
    config.set('Queue Low','Frequency','0.01')
    config.set('Queue Low','Commands','DISTANCE_SINCE_DTC_CLEAR,DISTANCE_W_MIL,COMMANDED_EGR,EGR_ERROR')
    config.set('Queue Low','Default Queue','True')
    config.set('Queue Once','Frequency','1.0')
    config.set('Queue Once','Commands','WARMUPS_SINCE_DTC_CLEAR')
    config.set('Queue Once','Delete After Poll','True')
    config.set('Queue Once','Reconfigure on Restart','True')

    return config

def saveConfig(config):
    config.write(open('obdlogger.cfg','w'))
