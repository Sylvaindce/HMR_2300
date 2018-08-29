"""
Created on Tue Jan 23 13:44:05 2018
@author: Sylvain Decombe
"""

import sys, os, glob, pathlib, time, datetime, io, csv, serial, binascii, numpy, re, smtplib, random
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from email import encoders

# HMR
class HMR2300_API:

    def __init__(self, devid="99"):
        self.__devid = devid

    @property
    def devid(self):
        return self.__devid

    @devid.setter
    def devid(self, devid):
        self.__devid = devid

    @staticmethod
    def devid_cmd():
        return "*99ID\r".encode()

    @property
    def continuous_stream_cmd(self):
        return "*ddC\r".replace("dd", self.__devid).encode()

    @staticmethod
    def esc_cmd():
        return chr(27).encode()

    @property
    def hw_cmd(self):
        return "*ddH\r".replace("dd", self.__devid).encode()

    @property
    def sw_cmd(self):
        return "*ddF\r".replace("dd", self.__devid).encode()

    @property
    def serial_cmd(self):
        return "*dd#\r".replace("dd", self.__devid).encode()

    @property
    def write_enable_cmd(self):
        return "*ddWE\r".replace("dd", self.__devid).encode()

    def baudrate_cmd(self, baudrate):
        """ 19200 correspond to F and 9600 to S """
        if baudrate is 19200:
            baudrate = "F"
        else:
            baudrate = "S"
        return "*99!BR=bd\r".replace("bd", baudrate).encode()

    @property
    def factory_settings_cmd(self):
        return "*ddD\r".replace("dd", self.__devid).encode()

    def sample_rate_cmd(self, rate):
        nnn = [10, 20, 25, 30, 40, 50, 60, 100, 123, 154]
        rate = min(nnn, key=lambda x: abs(x - rate))
        return ("*ddR=" + str(rate) + "\r").replace("dd", self.__devid).encode()
    
    def format_cmd(self, format):
        if format == 'binary':
            _format = 'B'
        else:
            _format = 'A'
        return "*{0!s}{1!s}\r".format(self.__devid, _format).encode()


class Utils:

    @staticmethod
    def is_int(s):
        is_int = True
        try:
            int(s)
        except (ValueError):
            is_int = False
        return is_int

    @staticmethod
    def serial_ports():
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result

    @staticmethod
    def write_csv_file(tab, send_mail=False):
        path = str(os.getcwd())
        date_str = datetime.datetime.today().strftime("%Y-%m-%d_%H%M")
        file_path = os.path.join(path, "magnetometer_data_" + date_str + ".csv")
        print (file_path)
        try:
            with open(file_path, 'wt') as csvfile:
                writer = csv.writer(csvfile, delimiter=';', quoting=csv.QUOTE_MINIMAL, quotechar='|', lineterminator='\n')
                writer.writerow(["Date", date_str + time.strftime("%z", time.gmtime())])
                writer.writerow(["Timestamp [s]", "B_x [uT]", "B_y [uT]", "B_z [uT]"])
                for value in tab:
                    writer.writerow(value)
            if send_mail:
                Utils.send_mail(["email@email.com"], "Mag_" + date_str, "Message", [file_path])
        except:
            print(sys.exc_info())
        

    @staticmethod
    def generate_message_id(msg_from):
        domain = msg_from.split("@")[1]
        r = "%s.%s" % (time.time(), random.randint(0, 100))
        mid = "<%s@%s>" % (r, domain)
        return mid

    @staticmethod
    def send_mail(msg_to, subject, text, files=[]):
        msg_from = "email@email.com"
        pwd = "password"
        assert type(msg_to)==list
        assert type(files)==list

        msg = MIMEMultipart()
        msg['From'] = msg_from
        msg['To'] = COMMASPACE.join(msg_to)
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = subject

        text = text.encode("utf-8")
        text = MIMEText(text, 'plain', "utf-8")
        msg.attach(text)

        msg.add_header('Message-ID', Utils.generate_message_id(msg_from))

        for file in files:
            part = MIMEBase('application', "octet-stream")
            part.set_payload( open(file,"rb").read() )
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename="%s"'% os.path.basename(file))
            msg.attach(part)

        smtp = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        smtp.ehlo()
        smtp.login(msg_from, pwd)
        smtp.sendmail(msg_from, msg_to, msg.as_string())
        print("Email sent to " + "".join(msg_to))
        smtp.close()

        return msg


class Magnetometer:

    def __init__(self, baudrate=9600, timeout=2, data_format="binary"):
        self.init_sleep = 0.05
        self.tab = []
        self.__baudrate = baudrate
        self.__timeout = timeout
        self.__format = data_format
        self.__ser = None
        self.__api = HMR2300_API()

    def init_acquisition(self, timed=0, automated=-1):
        ports = Utils.serial_ports()
        for i in range(len(ports)):
            print(str(i) + ": " + ports[i] + ", ")

        response = automated
        if automated == -1:
            response = input("Please select your communication port: ")
        if (Utils.is_int(response) and int(response) < len(ports)):
            try:
                if self.init_com(ports[int(response)]):
                    print("Init com okay !")
                    if timed == 0:
                        self.infinite_read()
                    else:
                        if self.timed_read(timed) == True:
                            self.close_com()
                print("Erreur de communication")
                exit()
            except KeyboardInterrupt:
                self.close_com()
        else:
            sys.stderr.write("Error, Incorrect communication port\n")


    def init_com(self, com):
        """ Send command to get Device ID """
        self.__ser = serial.Serial(com, self.__baudrate, timeout=self.__timeout)

        ## Stop the Continious Stream, avoid error
        self.__ser.write(self.__api.esc_cmd())
        self.__ser.write(self.__api.devid_cmd())
        tmp = self.__ser.readline().decode()

        ## Get Dev ID
        if "ID= " in tmp:
            self.__api.devid = tmp.split("ID= ")[1].replace("\r", "")
            print(self.__api.devid)

            init_cmds = [self.__api.factory_settings_cmd, self.__api.format_cmd(self.__format), self.__api.sample_rate_cmd(100), self.__api.continuous_stream_cmd]

            for cmd in init_cmds:
                self.__ser.write(self.__api.write_enable_cmd)
                print(self.__ser.readline().decode())
                time.sleep(self.init_sleep)
                print(cmd)
                self.__ser.write(cmd)
                if cmd != self.__api.continuous_stream_cmd:
                    print(self.__ser.readline().decode())
                time.sleep(self.init_sleep)
            return True
        return False


    def infinite_read(self):
        while True:
            self.read_stream()

    def timed_read(self, loop_time=1):
        t_end = time.time() + 60 * loop_time

        while time.time() < t_end:
            self.read_stream()   
        
        return True

    def read_stream(self):
        eol = b'\r'
        line = bytearray()
        while True:
            char = self.__ser.read(1)
            if char:
                if char == eol:
                    break
                else:
                    line += char
        tmp = []
        tmp.clear()
        answer = self.parse_xyz(line)
        if answer is not None:
            tmp.append(str(datetime.datetime.today().timestamp()))
            tmp.append(round(answer[0], 3))
            tmp.append(round(answer[1], 3))
            tmp.append(round(answer[2], 3))
            self.tab.append(tmp)

    def parse_xyz(self, answer):
        if answer == b'':
            return None
        if self.__format == "binary":
            answer = binascii.hexlify(answer)
            hexa = [answer[:4], answer[4:8], answer[8:12]]
            try:
                decimal = [int(hexa[0], 16), int(hexa[1], 16), int(hexa[2], 16)]
                for j in range(0, 3):
                    if decimal[j] >= 35536:
                        decimal[j] -= 65536
                    decimal[j] = numpy.around(decimal[j] * 0.006667, 10)
                x, y, z = decimal[0], decimal[1], decimal[2]
            except:
                return None
        else:
            answer = answer.decode("utf-8")
            answer = answer.replace("\r", "")
            x = re.sub("[ ,]", '', answer[:7])
            x = (float(x) / 150)
            y = re.sub("[ ,]", '', answer[9:16])
            y = (float(y) / 150)
            z = re.sub("[ ,]", '', answer[18:25])
            z = (float(z) / 150)
       
        result = []
        result.append(x)
        result.append(y)
        result.append(z)
        print (result)
        return result

    def close_com(self):
        print("exit")
        self.__ser.write(self.__api.esc_cmd())
        self.__ser.close()
        Utils.write_csv_file(self.tab)
        exit()  

def main():
    mag = Magnetometer()
    mag.init_acquisition()


if __name__ == "__main__":
    main()
