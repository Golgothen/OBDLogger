import os, csv, logging

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
        #try:
        with open(file) as f:
            reader = csv.DictReader(f)
            headings = next(reader)
            for h in headings:
                data[h] = []
            f.seek(0)
            next(reader)
            for row in reader:
                for h in row:
                    if h == 'DATE':
                        data[h].append(row[h])
                    else:
                        data[h].append(float(row[h]))
        return data
        #except:
        #    f.close()
        #    data=None
            #Nulls in file causes CSV reader to fail
            #Recreate the file stripping out all nulls
        #    f = open(file,'rb')
        #    data=f.read()
        #    f.close()
        #    f = open(file,'wb')
        #    f.write(data.replace('\x00',''))
        #    f.close()
            #Try again
        #    return readCSV(file)
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
