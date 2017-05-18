import subprocess

class USBInfo():

    def __init__(self):

        self.devices = {}

        output = []
        output = str(subprocess.check_output('lsusb')).split('\\n')
        for o in output:
            if ':' not in o:
                continue
            vendorID = o.split(':')[1].strip().split(' ')[1]
            productID = o.split(':')[2].split(' ')[0]
            dmesg = subprocess.Popen(('dmesg'), stdout = subprocess.PIPE)
            grep = subprocess.Popen(('grep', '=' +vendorID), stdin = dmesg.stdout, stdout = subprocess.PIPE)
            busID = str(subprocess.check_output(('grep', '=' + productID), stdin = grep.stdout)).split(':')[0].split(']')[1].strip().split(' ')[1]
            self.devices[busID] = {}
            self.devices[busID]['VendorID'] = vendorID
            self.devices[busID]['ProductID'] = productID
            device_details = []
            dmesg = subprocess.Popen(('dmesg'), stdout = subprocess.PIPE)
            device_details = str(subprocess.check_output(('grep', busID + ':'), stdin = dmesg.stdout)).split('\\n')
            for d in device_details:
                if 'USB device strings' in d:
                    self.devices[busID]['Device Strings'] = {}
                    strings = d.split(':')[2].strip().split(',')
                    for s in strings:
                        string = s.split('=')
                        self.devices[busID]['Device Strings'][string[0].strip()] = string[1].strip()
                if 'Product:' in d:
                    self.devices[busID]['Product Name'] = d.split(':')[2].strip()
                if 'Manufacturer:' in d:
                    self.devices[busID]['Manufacturer'] = d.split(':')[2].strip()
                if 'SerialNumber:' in d:
                    self.devices[busID]['Serial Number'] = d.split('SerialNumber:')[1].strip()
                if 'input:' in d:
                    if 'Inputs' not in self.devices[busID]:
                        self.devices[busID]['Inputs'] = {}
                    i = d.split('input:')[1].strip()
                    self.devices[busID]['Inputs'][i.split(' as ')[0]] = i.split(' as ')[1]
                if 'now attached to' in d:
                    self.devices[bus_id]['File'] = d.split('now attached to')[1].strip()

    def getDevice(self, **kwargs):
        devices = []
        for k in kwargs:
            if k == 'BUS':
                return self.devices[kwargs[k]]
            if k == 'VENDOR':
                for d in self.devices:
                    if self.devices[d]['VendorID'] == kwargs[k]:
                        devices.append(self.devices[d])
                if len(devices) == 0:
                    return None
                elif len(devices) == 1:
                    return devices[0]
                else:
                    return devices
            if k == 'PRODUCT':
                if len(devices) > 0:
                    for d in devices:
                        if d['ProductID'] == kwargs[k]:
                            return d
                else:
                    for d in self.devices:
                        if self.devices[d]['ProductID'] == kwargs[k]:
                            devices.append(self.devices[d])
                    if len(devices) == 0:
                        return None
                    elif len(devices) == 1:
                        return devices[0]
                    else:
                        return devices

