import os, csv, logging, sys

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
