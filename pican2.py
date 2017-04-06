# -*- coding: utf-8 -*-

########################################################################
#                                                                      #
# python-OBD: A python OBD-II serial module derived from pyobd         #
#                                                                      #
# Copyright 2004 Donour Sizemore (donour@uchicago.edu)                 #
# Copyright 2009 Secons Ltd. (www.obdtester.com)                       #
# Copyright 2009 Peter J. Creath                                       #
# Copyright 2016 Brendan Whitfield (brendan-w.com)                     #
#                                                                      #
########################################################################
#                                                                      #
# elm327.py                                                            #
#                                                                      #
# This file is part of python-OBD (a derivative of pyOBD)              #
#                                                                      #
# python-OBD is free software: you can redistribute it and/or modify   #
# it under the terms of the GNU General Public License as published by #
# the Free Software Foundation, either version 2 of the License, or    #
# (at your option) any later version.                                  #
#                                                                      #
# python-OBD is distributed in the hope that it will be useful,        #
# but WITHOUT ANY WARRANTY; without even the implied warranty of       #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the        #
# GNU General Public License for more details.                         #
#                                                                      #
# You should have received a copy of the GNU General Public License    #
# along with python-OBD.  If not, see <http://www.gnu.org/licenses/>.  #
#                                                                      #
########################################################################

inport can, logging

logger = logging.getLogger('root')

class CANBUS:
    """
        Handles communication with the PiCAN2 hat.

        After instantiation with an interface (can0, etc...),
        the following functions become available:

            send_and_parse()
            close()
            status()
            port_name()
            protocol_name()
            ecus()
    """

    def __init__(self, channel):
        """Initializes port by resetting device and gettings supported PIDs. """

        logger.debug("Initializing CAN Interface: INTERFACE=%s" %
                    (
                        interface
                    ))

        self.__status   = 'Not Connected'
        self.__canID    = None
        #self.__protocol = UnknownProtocol([])
        #self.__nodatacount = 0


        # ------------- open port -------------
        try:
            self.__bus = can.interface.Bus(channel = channel, bustype = 'socketcan_native')

        except OSError as e:
            # OSError [Error 19] No Such Device
            self.__error(e)
            return

        self.__status = 'CAN Connected'

        # try to communicate with the car, and load the correct protocol parser
        if self.set_protocol(protocol):
            self.__status = OBDStatus.CAR_CONNECTED
            logger.info("Connected Successfully: PORT=%s BAUD=%s PROTOCOL=%s" %
                        (
                            portname,
                            self.__port.baudrate,
                            self.__protocol.ELM_ID,
                        ))
        else:
            logger.debug("Connected to the adapter, but failed to connect to the vehicle")


    def set_protocol(self, protocol):
        if protocol is not None:
            # an explicit protocol was specified
            if protocol not in self._SUPPORTED_PROTOCOLS:
                logger.debug("%s is not a valid protocol. Please use \"1\" through \"A\"")
                return False
            return self.manual_protocol(protocol)
        else:
            # auto detect the protocol
            return self.auto_protocol()


    def manual_protocol(self, protocol):
        r = self.__send(b"ATTP" + protocol.encode())
        r0100 = self.__send(b"0100")

        if not self.__has_message(r0100, "UNABLE TO CONNECT"):
            # success, found the protocol
            self.__protocol = self._SUPPORTED_PROTOCOLS[protocol](r0100)
            return True

        return False


    def auto_protocol(self):
        """
            Attempts communication with the car.

            If no protocol is specified, then protocols at tried with `ATTP`

            Upon success, the appropriate protocol parser is loaded,
            and this function returns True
        """

        # -------------- try the ELM's auto protocol mode --------------
        r = self.__send(b"ATSP0")

        # -------------- 0100 (first command, SEARCH protocols) --------------
        r0100 = self.__send(b"0100")
        logger.debug("r0100 : " + str(r0100))

        # ------------------- ATDPN (list protocol number) -------------------
        r = self.__send(b"ATDPN")
        if len(r) != 1:
            logger.debug("Failed to retrieve current protocol")
            return False


        p = r[0] # grab the first (and only) line returned
        # suppress any "automatic" prefix
        p = p[1:] if (len(p) > 1 and p.startswith("A")) else p

        # check if the protocol is something we know
        if p in self._SUPPORTED_PROTOCOLS:
            # jackpot, instantiate the corresponding protocol handler
            self.__protocol = self._SUPPORTED_PROTOCOLS[p](r0100)
            return True
        else:
            # an unknown protocol
            # this is likely because not all adapter/car combinations work
            # in "auto" mode. Some respond to ATDPN responded with "0"
            logger.debug("ELM responded with unknown protocol. Trying them one-by-one")

            for p in self._TRY_PROTOCOL_ORDER:
                r = self.__send(b"ATTP" + p.encode())
                r0100 = self.__send(b"0100")
                if not self.__has_message(r0100, "UNABLE TO CONNECT"):
                    # success, found the protocol
                    self.__protocol = self._SUPPORTED_PROTOCOLS[p](r0100)
                    return True

        # if we've come this far, then we have failed...
        logger.debug("Failed to determine protocol")
        return False


    def set_baudrate(self, baud):
        if baud is None:
            # when connecting to pseudo terminal, don't bother with auto baud
            if self.port_name().startswith("/dev/pts"):
                logger.debug("Detected pseudo terminal, skipping baudrate setup")
                return True
            else:
                return self.auto_baudrate()
        else:
            self.__port.baudrate = baud
            return True


    def auto_baudrate(self):
        """
        Detect the baud rate at which a connected ELM32x interface is operating.
        Returns boolean for success.
        """

        # before we change the timout, save the "normal" value
        timeout = self.__port.timeout
        self.__port.timeout = 0.1 # we're only talking with the ELM, so things should go quickly

        for baud in self._TRY_BAUDS:
            self.__port.baudrate = baud
            self.__port.flushInput()
            self.__port.flushOutput()

            # Send a nonsense command to get a prompt back from the scanner
            # (an empty command runs the risk of repeating a dangerous command)
            # The first character might get eaten if the interface was busy,
            # so write a second one (again so that the lone CR doesn't repeat
            # the previous command)
            self.__port.write(b"\x7F\x7F\r\n")
            self.__port.flush()
            response = self.__port.read(1024)
            logger.debug("Response from baud %d: %s" % (baud, repr(response)))

            # watch for the prompt character
            if response.endswith(b">"):
                logger.debug("Choosing baud %d" % baud)
                self.__port.timeout = timeout # reinstate our original timeout
                return True


        logger.debug("Failed to choose baud")
        self.__port.timeout = timeout # reinstate our original timeout
        return False



    def __isok(self, lines, expectEcho=False):
        if not lines:
            return False
        if expectEcho:
            # don't test for the echo itself
            # allow the adapter to already have echo disabled
            return self.__has_message(lines, 'OK')
        else:
            return len(lines) == 1 and lines[0] == 'OK'


    def __has_message(self, lines, text):
        for line in lines:
            if text in line:
                return True
        return False


    def __error(self, msg):
        """ handles fatal failures, print logger.info info and closes serial """
        self.close()
        logger.debug(str(msg))


    def port_name(self):
        if self.__port is not None:
            return self.__port.portstr
        else:
            return ""


    def status(self):
        return self.__status

    def set_status(self,status):
        self.__status=status
        #logger.debug("Set status to " + self.__status)

    def ecus(self):
        return self.__protocol.ecu_map.values()


    def protocol_name(self):
        return self.__protocol.ELM_NAME


    def protocol_id(self):
        return self.__protocol.ELM_ID


    def close(self):
        """
            Resets the device, and sets all
            attributes to unconnected states.
        """

        self.__status   = OBDStatus.NOT_CONNECTED
        self.__protocol = None

        if self.__port is not None:
            logger.info("closing port")
            self.__write(b"ATZ")
            self.__port.close()
            self.__port = None


    def send_and_parse(self, cmd):
        """
            send() function used to service all OBDCommands

            Sends the given command string, and parses the
            response lines with the protocol object.

            An empty command string will re-trigger the previous command

            Returns a list of Message objects
        """

        if self.__status == OBDStatus.NOT_CONNECTED:
            logger.info("cannot send_and_parse() when unconnected")
            return None

        lines = self.__send(cmd)
        messages = self.__protocol(lines)
        return messages


    def __send(self, cmd, delay=None):
        """
            unprotected send() function

            will __write() the given string, no questions asked.
            returns result of __read() (a list of line strings)
            after an optional delay.
        """

        self.__write(cmd)

        if delay is not None:
            logger.debug("wait: %d seconds" % delay)
            time.sleep(delay)

        return self.__read()


    def __write(self, cmd):
        """
            "low-level" function to write a string to the port
        """

        if self.__port:
            cmd += b"\r\n" # terminate
            logger.debug("write: " + repr(cmd))
            self.__port.flushInput() # dump everything in the input buffer
            self.__port.write(cmd) # turn the string into bytes and write
            self.__port.flush() # wait for the output buffer to finish transmitting
        else:
            logger.info("cannot perform __write() when unconnected")


    def __read(self):
        """
            "low-level" read function

            accumulates characters until the prompt character is seen
            returns a list of [/r/n] delimited strings
        """
        if not self.__port:
            logger.info("cannot perform __read() when unconnected")
            return []

        buffer = bytearray()

        while True:
            # retrieve as much data as possible
            data = self.__port.read(self.__port.in_waiting or 1)

            # if nothing was recieved
            if not data:
                logger.warning("Failed to read port")
                break

            buffer.extend(data)

            # end on chevron (ELM prompt character)
            if self.ELM_PROMPT in buffer:
                break

        # log, and remove the "bytearray(   ...   )" part
        logger.debug("read: " + repr(buffer)[10:-1])
        if repr(buffer)[12:19]=='NO DATA':
            self.__nodatacount+=1
            logger.debug("NoData count: " + str(self.__nodatacount))
            if self.__nodatacount > 10:
                self.set_status('ELM Connected')
        else:
            self.__nodatacount = 0
        if repr(buffer)[12:21]=='CAN ERROR':
            self.set_status('ELM Connected')

        #print temp

        # clean out any null characters
        buffer = re.sub(b"\x00", b"", buffer)

        # remove the prompt character
        if buffer.endswith(self.ELM_PROMPT):
            buffer = buffer[:-1]

        # convert bytes into a standard string
        string = buffer.decode()

        # splits into lines while removing empty lines and trailing spaces
        lines = [ s.strip() for s in re.split("[\r\n]", string) if bool(s) ]

        return lines
