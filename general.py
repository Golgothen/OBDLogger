import os, csv, logging, sys, subprocess
from configparser import ConfigParser

###

# General Functions

###

def formatSeconds(d):
    hours, remainder = divmod(d, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 99:
        days,hours = divmod(hours, 99)
        return '{:02.0f}d{:02.0f}:{:02.0f}'.format(days, hours, minutes)
    return '{:02.0f}:{:02.0f}:{:02.0f}'.format(hours, minutes, seconds)

def formatLatitude(d):
    if d < 0: heading = 'S'
    elif d == 0: heading = '0'
    else: heading = 'N'
    minor, deg = modf(abs(d))
    minor, min = modf(minor*60)
    sec = minor * 60
    deg_sign = u'\N{DEGREE SIGN}'
    return '{:3.0f}{}{:2.0f}\'{:2.2f}"{}'.format(deg, deg_sign, min, sec, heading)

def formatLongitude(d):
    if d < 0: heading = 'E'
    elif d == 0: heading = '0'
    else: heading = 'W'
    minor, deg = modf(abs(d))
    minor, min = modf(minor*60)
    sec = minor * 60
    deg_sign = u'\N{DEGREE SIGN}'
    return '{:3.0f}{}{:2.0f}\'{:2.2f}"{}'.format(deg, deg_sign, min, sec, heading)

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

def writeLastTrip(file, data):
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

def writeTripHistory(file, data):
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
    config.add_section('Data Screen')
    config.add_section('Data Layout')
    config.add_section('Transmission')

    config.set('Application','LogPath','./logs/')
    config.set('Application','Log Frequency','1')
    config.set('Application','StatPath','./stats/')
    config.set('Application','Idle Screen Time','10')
    config.set('Application','Busy Screen Time','0.25')
    config.set('Application','Trip Timeout','900')
    config.set('Application','Log Extra Data','True')
    config.set('Application','OBD Product ID','2303')
    config.set('Application','OBD Vendor ID','067b')
    config.set('Application','OBD Baud','38400')
    config.set('Application','Queues','Hi,Medium,Low,Once')
    config.set('Application','Log Headings','TIMESTAMP,RPM,SPEED,DISTANCE,FAM,LP100K,LPS,LPH,MAF,ENGINE_LOAD,DRIVE_RATIO,GEAR')
    config.set('Application','Pipe Timeout','3')
    config.set('Application','GPS Enabled','True')
    config.set('Application','GPS Product ID','ea60')
    config.set('Application','GPS Vendor ID','10c4')
    config.set('Application','Data Screen Size','23')

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
    config.set('Vehicle','Transmission Speeds','5')

    config.set('Queue Hi','Frequency','10.0')
    config.set('Queue Hi','Commands','RPM,SPEED,MAF,ENGINE_LOAD')
    config.set('Queue Medium','Frequency','2.0')
    config.set('Queue Medium','Commands','BAROMETRIC_PRESSURE,INTAKE_PRESSURE,COOLANT_TEMP,FUEL_RAIL_PRESSURE_DIRECT,CONTROL_MODULE_VOLTAGE')
    config.set('Queue Low','Frequency','0.5')
    config.set('Queue Low','Commands','DISTANCE_SINCE_DTC_CLEAR,DISTANCE_W_MIL,COMMANDED_EGR,EGR_ERROR')
    config.set('Queue Low','Default Queue','True')
    config.set('Queue Once','Frequency','10.0')
    config.set('Queue Once','Commands','WARMUPS_SINCE_DTC_CLEAR')
    config.set('Queue Once','Delete After Poll','True')
    config.set('Queue Once','Reconfigure on Restart','True')

    config.set('Data Screen','Line 0','SPEED')
    config.set('Data Screen','Line 1','RPM')
    config.set('Data Screen','Line 2','LP100K')
    config.set('Data Screen','Line 3','ENGINE_LOAD')
    config.set('Data Screen','Line 4','BOOST_PRESSURE')
    config.set('Data Screen','Line 5','COOLANT_TEMP')
    config.set('Data Screen','Line 6','DISTANCE')
    config.set('Data Screen','Line 7','TIME')
    config.set('Data Screen','Line 8','FUEL')
    config.set('Data Screen','Line 9','LPH')
    config.set('Data Screen','Line 10','GEAR')
    config.set('Data Screen','Line 11','MAF')
    config.set('Data Screen','Line 12','FAM')
    config.set('Data Screen','Line 13','VOLTAGE')
    config.set('Data Screen','Line 14','EGR')
    config.set('Data Screen','Line 15','AIR_TEMP')
    config.set('Data Screen','Line 16','INTAKE_TEMP')
    config.set('Data Screen','Line 17','FUEL_RAIL')
    config.set('Data Screen','Line 18','LATITUDE')
    config.set('Data Screen','Line 19','LONGITUDE')
    config.set('Data Screen','Line 20','ALTITUDE')
    config.set('Data Screen','Line 21','GPS_SPD')
    config.set('Data Screen','Line 22','HEADING')

    config.set('Data Layout','SPEED',          '*Speed : SPEED.VAL/SPEED.MAX/SPEED.AVG :')
    config.set('Data Layout','RPM',            '***RPM : RPM.VAL/RPM.MAX :')
    config.set('Data Layout','LPH',            '***LPH : LPH.VAL/LPH.AVG :')
    config.set('Data Layout','LP100K',         'L/100K : LP100K.VAL/LP100K.AVG :')
    config.set('Data Layout','FAM',            '***FAM : FAM.VAL/FAM.MAX :')
    config.set('Data Layout','ENGINE_LOAD',    '**Load : ENGINE_LOAD.VAL/ENGINE_LOAD.AVG :')
    config.set('Data Layout','MAF',            '***MAF : MAF.VAL/MAF.AVG :')
    config.set('Data Layout','BOOST_PRESSURE', '*Boost : BOOST_PRESSURE.VAL/BOOST_PRESSURE.MAX :')
    config.set('Data Layout','COOLANT_TEMP',   '**Temp : COOLANT_TEMP.VAL/COOLANT_TEMP.MAX :')
    config.set('Data Layout','DISTANCE',       '**Trip : DISTANCE.SUM           :')
    config.set('Data Layout','FUEL',           '**Fuel : LPS.SUM/LPH.VAL :')
    config.set('Data Layout','TIME',           '**Time : DURATION.SUM/IDLE_TIME.SUM :')
    config.set('Data Layout','GEAR',           '**Gear : GEAR.VAL/DRIVE_RATIO.VAL :')
    config.set('Data Layout','VOLTAGE',        '*Volts : CONTROL_MODULE_VOLTAGE.VAL/ CONTROL_MODULE_VOLTAGE.MIN/ CONTROL_MODULE_VOLTAGE.MAX :')
    config.set('Data Layout','EGR',            '***EGR : COMMANDED_EGR.VAL/EGR_ERROR.VAL :')
    config.set('Data Layout','AIR_TEMP',       '*Air C : AMBIANT_AIR_TEMP.VAL/AMBIANT_AIR_TEMP.MAX :')
    config.set('Data Layout','FUEL_RAIL',      '**Rail : FUEL_RAIL_PRESSURE_DIRECT.VAL/FUEL_RAIL_PRESSURE_DIRECT.MAX :')
    config.set('Data Layout','INTAKE_TEMP',    'Intake : INTAKE_TEMP.VAL/INTAKE_TEMP.MAX :')
    config.set('Data Layout','LATITUDE',       '***Lat : LATITUDE.VAL           :')
    config.set('Data Layout','LONGITUDE',      '***Lon : LONGITUDE.VAL           :')
    config.set('Data Layout','ALTITUDE',       '***Alt : ALTITUDE.VAL/ALTITUDE.MIN/ALTITUDE.MAX    :')
    config.set('Data Layout','GPS_SPEED',      'GPS Kh : GPS_SPD.VAL/GPS_SPD.MAX/GPS_SPD.AVG  :')
    config.set('Data Layout','HEADING',        '*Track : HEADING.VAL           :')

    config.set('Transmission','Gear Neutral Label','Idle')
    config.set('Transmission','Gear 1 Lower','12.0')
    config.set('Transmission','Gear 1 Upper','14.0')
    config.set('Transmission','Gear 1 Label','1st')
    config.set('Transmission','Gear 2 Lower','6.0')
    config.set('Transmission','Gear 2 Upper','7.4')
    config.set('Transmission','Gear 2 Label','2nd')
    config.set('Transmission','Gear 3 Lower','3.5')
    config.set('Transmission','Gear 3 Upper','4.5')
    config.set('Transmission','Gear 3 Label','3rd')
    config.set('Transmission','Gear 4 Lower','2.7')
    config.set('Transmission','Gear 4 Upper','3.1')
    config.set('Transmission','Gear 4 Label','4th')
    config.set('Transmission','Gear 5 Lower','2.1')
    config.set('Transmission','Gear 5 Upper','2.35')
    config.set('Transmission','Gear 5 Label','5th')

    return config

def saveConfig(config):
    config.write(open('obdlogger.cfg','w'))

def getUSBDevices():
    devices = {}
    # put all dmesg messages into a list
    output_list = []
    output_list = str(subprocess.check_output('dmesg')).split('\\n')

    # Look for 'New USB device' messages
    filter_list = [x for x in output_list if 'New USB device found' in x]
    for f in filter_list:
        # This message gives us vendor, product and bus ID's
        bus_id = f.split(':')[0].split(']')[1].strip()
        devices[bus_id] = {}
        devices[bus_id]['VENDOR'] =  f.split(',')[1].strip().split('=')[1]
        devices[bus_id]['PRODUCT'] =  f.split(',')[2].strip().split('=')[1]
        # list to store all other details about the device
        device_details = []
        # pull out all messages from dmesg in relation to the bus ID
        device_details = [x for x in output_list if bus_id in x]
        # Pick out the info we need:
        for d in device_details:
            if 'Product:' in d:
                # Product Name
                devices[bus_id]['NAME'] = d.split(':')[2].strip()
            if 'Manufacturer' in d:
                # Manufacturer Name
                devices[bus_id]['MANUFACTURER'] = d.split(':')[2].strip()
            if 'now attached to' in d:
                # Block device - if it has one
                devices[bus_id]['FILE'] = d.split('now attached to')[1].strip()
    return devices

def getBlockPath(vendor, product):
    device_path = None
    devices = getUSBDevices()
    for d in devices:
        if devices[d]['VENDOR'] == vendor and \
           devices[d]['PRODUCT'] == product:
            if 'FILE' in devices[d]:
                device_path = devices[d]['FILE']
                break
    return device_path

