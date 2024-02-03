import sys
import select
import socket
import datetime
import threading
import matplotlib
import numpy as np
import pyqtgraph as pg
import matplotlib.pyplot as plt
from scipy import signal
from qt_material import apply_stylesheet
from PyQt5.QtGui import QIcon, QValidator, QPixmap
from PyQt5.QtWidgets import QApplication, QWidget, QLineEdit, QPushButton, QHBoxLayout, QGridLayout, QLabel, \
    QVBoxLayout, QComboBox

matplotlib.use('Agg')

class Validator(QValidator):  # text input validator
    def validate(self, input_str, pos_int):  # text input validator
        try:  # try-except
            if 0 <= float(input_str) <= 999999:
                return (QValidator.Acceptable, input_str, pos_int)
            else:
                return (QValidator.Invalid, input_str, pos_int)
        except:
            if len(input_str) == 0:
                return (QValidator.Intermediate, input_str, pos_int) 

class Awp_plot_demo(QWidget):
    
    # Initialization
    def __init__(self):
        super(Awp_plot_demo, self).__init__()

        # parameters definition
        self.ip = ''
        self.port = ''
        self.socket_flag = 0  # socket
        self.NFFT = 8192*2  # FFT num
        self.timeout = 1  # fpga timeout
        self.pic_path = 'spec_2.png'
        self.AMPTITUD_MAX = 2 ** 16  # amp_normalized
        self.buffuer_size = 1024  # buffersize
        self.pen_sepc = pg.mkPen(color="#33FFCC")  # spec_plot color
        self.pen_time_I = pg.mkPen(color="#1E90FF")  # time_plot I
        self.pen_time_Q = pg.mkPen(color="#A52A2A")  # time_plot Q

        self.file_name = './' + 'base_IQ' + '_'  # save path
        self.styles = {"color": "#FFFFFF", "font-size": "20px"}

        # up left pic
        self.pix = QPixmap(self.pic_path)
        self.spec_pic = QLabel(self)
        self.spec_pic.setPixmap(self.pix)
        self.setWindowTitle('Usrp_Spectrum_Plot')
        self.setWindowIcon(QIcon('awp_logo.png'))

        # QlineEdit
        self.IP = QLineEdit(self)  # IP
        self.port_num = QLineEdit(self)  # PORT
        self.center_fre = QLineEdit(self)  # center_fre
        self.sub_fre = QLineEdit(self)  # sub_fre

        self.IP.setText('192.168.3.242')
        self.port_num.setText('7755')
        self.center_fre.setPlaceholderText('fc(MHz)')
        self.sub_fre.setPlaceholderText('f_sub(MHz)')
        self.IP.setStyleSheet('color:cyan')
        self.port_num.setStyleSheet('color:cyan')
        self.center_fre.setStyleSheet('color:cyan')
        self.sub_fre.setStyleSheet('color:cyan')
        
        # QcomboBox
        self.sample_rate = QComboBox(self)  # fs
        self.duration = QComboBox(self)  # ts
        self.gain = QComboBox(self)  # gain
        self.sample_rate.setStyleSheet("QComboBox{color:cyan}")
        self.duration.setStyleSheet("QComboBox{color:cyan}")
        self.gain.setStyleSheet("QComboBox{color:cyan}")

        # add QcomboBox Items
        self.sample_rate.addItems(['122.88MHz', '61.44MHz', '30.72MHz', '15.36MHz'])
        self.duration.addItems(['10ms', '20ms', '30ms', '40ms', '50ms'])
        self.gain.addItems(['1', '10', '20', '30', '40', '55'])

        # validator
        validator = Validator() 
        self.center_fre.setValidator(validator)  # input validator
        self.sub_fre.setValidator(validator)  
        self.port_num.setValidator(validator) 

        # QPushButton
        self.single = QPushButton('single plot', self)  # single load
        self.continuous = QPushButton('continuous plot', self)  # continuous load
        self.udp_connect = QPushButton('connect device', self)  # connect fpga
        self.udp_disconnect = QPushButton('disconnect device', self)  # discon fpga
        self.single.setFixedSize(110, 50)  # resize button
        self.continuous.setFixedSize(110, 50)  
        self.udp_connect.setFixedSize(110, 50)  
        self.udp_disconnect.setFixedSize(110, 50) 
        self.single.setStyleSheet("QPushButton""{""background-color : none;""}"
                             "QPushButton:pressed""{""background-color : cyan;""}"
                             )  # set press and release background color
        self.continuous.setStyleSheet("QPushButton""{""background-color : none;""}"
                             "QPushButton:pressed""{""background-color : cyan;""}"
                             )  # set press and release background color
        self.udp_connect.setStyleSheet("QPushButton""{""background-color : none;""}"
                             "QPushButton:pressed""{""background-color : cyan;""}"
                             )  # set press and release background color
        self.udp_disconnect.setStyleSheet("QPushButton""{""background-color : none;""}"
                             "QPushButton:pressed""{""background-color : cyan;""}"
                             )  # set press and release background color

        # spec_plot widget
        self.graph_plot_spec = pg.PlotWidget()
        self.graph_plot_spec.setBackground('k')
        self.graph_plot_spec.setTitle("Spectrogram", color="w", size="14pt")
        self.graph_plot_spec.setLabel("bottom", "Fre(MHz)", **self.styles)
        self.graph_plot_spec.setLabel("left", "PSD(dB/Hz)", **self.styles)
        self.graph_plot_spec.showGrid(x=True, y=True)  # plot grid

        # time_plot widget
        self.graph_plot_time = pg.PlotWidget()
        self.graph_plot_time.setBackground('k') 
        self.graph_plot_time.setTitle("Time Domain", color="w", size="14pt")
        self.graph_plot_spec.setLabel("left", "Amp", **self.styles)
        self.graph_plot_time.setLabel("bottom", "time(s)", **self.styles)
        self.graph_plot_time.showGrid(x=True, y=True)

        # slot func
        self.udp_connect.clicked.connect(self.device_con)  # connect
        self.udp_disconnect.clicked.connect(self.device_discon)  # disconnect
        self.single.clicked.connect(self.single_trigger)   # single plot
        self.continuous.clicked.connect(self.continuous_trigger)   # continuous plot
        self.center_fre.editingFinished.connect(self.para_input)  # editingFinished convey value
        self.sub_fre.editingFinished.connect(self.para_input)  # editingFinished convey value
        self.sample_rate.activated.connect(self.para_input)  # editingFinished convey value
        self.duration.activated.connect(self.para_input)  # editingFinished convey value
        self.gain.activated.connect(self.para_input)  # select and emit
        self.IP.editingFinished.connect(self.ip_input)  # editingFinished convey value
        self.port_num.editingFinished.connect(self.ip_input)  # editingFinished convey value
        self.port_num.returnPressed.connect(self.ip_input_control)  # enter edit 

        # layout
        self.trigger_h_layout = QHBoxLayout()
        self.connect_h_layout = QHBoxLayout()
        self.grid = QGridLayout()
        self.left = QVBoxLayout()
        self.plot_layout = QVBoxLayout() 
        self.all_layout = QHBoxLayout()  # whole layout
        # button layout
        self.trigger_h_layout.addWidget(self.single)  
        self.trigger_h_layout.addWidget(self.continuous)  
        self.connect_h_layout.addWidget(self.udp_connect)  
        self.connect_h_layout.addWidget(self.udp_disconnect)  
        # plot layout
        self.plot_layout.addWidget(self.graph_plot_spec)
        self.plot_layout.addWidget(self.graph_plot_time)
        # grid layout
        self.grid.addWidget(self.IP, 0, 0, 1, 3)
        self.grid.addWidget(self.port_num, 1, 0, 1, 3)
        self.grid.addWidget(self.center_fre, 2, 0, 1, 3)
        self.grid.addWidget(self.sub_fre, 3, 0, 1, 3)
        self.grid.addWidget(self.sample_rate, 4, 0, 1, 3)
        self.grid.addWidget(self.duration, 5, 0, 1, 3)
        self.grid.addWidget(self.gain, 6, 0, 1, 3)
        # left layout
        self.left.addWidget(self.spec_pic)
        self.left.addLayout(self.trigger_h_layout)
        self.left.addLayout(self.connect_h_layout)
        self.left.addLayout(self.grid)
        self.left.setSpacing(16)  # set interval

        self.all_layout.addLayout(self.left) 
        self.all_layout.addLayout(self.plot_layout)  
        self.setLayout(self.all_layout)  # set whole layout

    # slot func
    def single_trigger(self):
        print('>>>single plot...')
        self.graph_plot_spec.clear()  # clear plot
        self.graph_plot_time.clear() 
        self.single_thread = threading.Thread(target=self.send_plot)
        self.single_thread.start()

    def continuous_trigger(self):
        print('>>>continuous plot...')
        self.graph_plot_spec.clear()  
        self.graph_plot_time.clear()  
        self.continuous_thread = threading.Thread(target=self.loop_send_plot)
        self.continuous_thread.start()

    def device_con(self):
        try:
            self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)  # socket
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.buffuer_size)  # set send and receiver buffer size
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, self.buffuer_size)
            self.sock.connect((self.ip, int(self.port)))  # bind ip port
            state = self.sock.getpeername()
            if state:
                print('Successfully established! The server address and port number are:{}'.format(state))
                self.socket_flag = 1
                self.udp_connect.setText('Successfully established')
                self.udp_disconnect.setText('Disconnect device')
        except socket.error as e:
            print('Connection failed.', e)

    def device_discon(self):
        if self.socket_flag == 1:
            self.sock.shutdown(2)  # 0 prohibit read;1 prohibit write;2 prohibit read & write;
            self.sock.close()  # discon
            print('Disconnected from server')
            self.socket_flag = 0
            self.udp_connect.setText('Connect device')
            self.udp_disconnect.setText('Disconnected')
            self.center_fre.setEnabled(True)  
            self.sub_fre.setEnabled(True)  
            self.IP.setEnabled(True) 
            self.port_num.setEnabled(True) 
        else:
            print('The server is not connected yet')
            self.udp_disconnect.setText('Not connected yet')
            self.IP.setEnabled(True)
            self.port_num.setEnabled(True)

    def para_input(self):  
        fs_real = 0
        ts_real = 0
        fc = self.center_fre.text()   
        f_sub = self.sub_fre.text()  
        fs = self.sample_rate.currentText()
        ts = self.duration.currentText()  
        gain = self.gain.currentText()  
        if fs == '122.88MHz': 
            fs_real = 0
        elif fs == '61.44MHz':
            fs_real = 1
        elif fs == '30.72MHz':
            fs_real = 2
        elif fs == '15.36MHz':
            fs_real = 3
        if ts == '10ms': 
            ts_real = 1
        elif ts == '20ms':
            ts_real = 2
        elif ts == '30ms':
            ts_real = 3
        elif ts == '40ms':
            ts_real = 4
        elif ts == '50ms':
            ts_real = 5
        para_input = '%s,%s,%s,%s' % (fc, f_sub, fs_real, ts_real)  
        gain_input = '%s,%s' % ('gain', gain)
        print(type(para_input))
        print('read para :{}'.format(para_input))
        print('gain set :{}'.format(gain_input))
        return para_input, gain_input

    def ip_input(self):
        self.ip = self.IP.text()     
        self.port = self.port_num.text() 

    def ip_input_control(self): 
        self.IP.setEnabled(False) 
        self.port_num.setEnabled(False)  
        
    def para_input_control(self):
        self.center_fre.setEnabled(False) 
        self.sub_fre.setEnabled(False) 

    def send_plot(self):
        try:
            [b, a] = self.para_input()
            self.sock.sendto(str.encode(a), (self.ip, int(self.port)))  # set send para(receiver gain)
            self.sock.sendto(str.encode(b), (self.ip, int(self.port)))  # set send para(fc、fsub、fs、ts)
        except Exception as e: 
            print('Not established yet...', e)
        else:
            print("Obtaining device data...... (UDP)")
            msgFromServer = self.sock.recvfrom(self.buffuer_size)  # receive data
            rev_data_length = len(msgFromServer[0])  # data length
            rcv_data = msgFromServer[0]
            print('first receive len:{},data type:{}.'.format(rev_data_length, type(rcv_data)))
            # device return
            freq_kHz = (rcv_data[0] * (1 << 24) + rcv_data[1] * (1 << 16) + rcv_data[2] * (1 << 8) + rcv_data[3])
            sample_rate = (rcv_data[4] * (1 << 24) + rcv_data[5] * (1 << 16) + rcv_data[6] * (1 << 8) + rcv_data[7])
            time_stamp = (rcv_data[8] * (1 << 24) + rcv_data[9] * (1 << 16) + rcv_data[10] * (1 << 8) + rcv_data[11])
            print('device return,fc:{}MHz;fs:{};time stamp:{}.'.format(freq_kHz / 1e3, sample_rate, time_stamp))
            while True:
                ready = select.select([self.sock], [], [], self.timeout)
                if ready[0]:
                    msgFromServer = self.sock.recvfrom(self.buffuer_size)
                    rcv_data += msgFromServer[0]
                    rev_data_length += len(msgFromServer[0])
                    self.graph_plot_spec.clear()  
                    self.graph_plot_time.clear()
                else:
                    print('data received,len is{}'.format(len(rcv_data)))
                    td = self.bytes_to_td(rcv_data)
                    fre, pwr = signal.welch(td, fs=self.sr_match(sample_rate), nperseg=self.NFFT, return_onesided=False, detrend=False)
                    t = np.linspace(0, len(td), len(td))
                    self.graph_plot_spec.plot().setData(np.fft.fftshift(fre/1e6), np.fft.fftshift(10 * np.log10(pwr)), pen=self.pen_sepc)
                    self.graph_plot_time.plot().setData(t/self.sr_match(sample_rate), td.real, pen=self.pen_time_I)  # plot I
                    self.graph_plot_time.plot().setData(t/self.sr_match(sample_rate), td.imag, pen=self.pen_time_Q)  # plot Q
                    self.save_data_to_csv(self.file_name, td)  # save IQ data
                    break

    def loop_send_plot(self):
        while True:
            self.send_plot()

    def sr_match(self, sr): 
        sr_real = 1
        if sr == 0: 
            sr_real = 122.88e6
        elif sr == 1:
            sr_real = 61.44e6
        elif sr == 2:
            sr_real = 30.72e6
        elif sr == 3:
            sr_real = 15.36e6
        return sr_real

    def bytes_to_td(self, message): 
        # IQ data
        msg_length = len(message)
        print(msg_length)
        length = int(msg_length / 4)
        if msg_length % 4 != 0:
            print('data_format_error')
        td = np.zeros(length, dtype=np.complex128)
        for i in range(length):
            q_hex = message[i * 4] * 256 + message[i * 4 + 1]
            if q_hex > 32767:
                q_hex -= 65536
            i_hex = message[i * 4 + 2] * 256 + message[i * 4 + 3]
            if i_hex > 32767:
                i_hex -= 65536
            i_val = i_hex / self.AMPTITUD_MAX  
            q_val = q_hex / self.AMPTITUD_MAX 
            td[i] = i_val + q_val * 1.j
        td_dcr_i = td.real - np.mean(td.real)  
        td_dcr_q = td.imag - np.mean(td.imag)  
        td_dcr = td_dcr_i + td_dcr_q * 1.j
        return td_dcr

    def save_data_to_csv(self, path, td_data):  
        i_data = np.real(td_data)
        q_data = np.imag(td_data)
        data_length = len(td_data)
        dt = datetime.datetime.now()
        dtstr = dt.strftime('%Y%m%d_%H%M%S')
        with open(path + dtstr + '.csv', 'w') as file:
            for i in range(data_length):
                file.write('%d,%f,%f\n' % (i + 1, i_data[i], q_data[i]))
            file.close()
        save_path = path + dtstr + '.csv'
        print('file save path:{}'.format(save_path))
        return save_path

if __name__ == '__main__':
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='default_dark.xml')
    Awp_plot = Awp_plot_demo()
    Awp_plot.show()
    sys.exit(app.exec_())
