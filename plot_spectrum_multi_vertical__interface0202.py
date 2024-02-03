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

class Validator(QValidator):  # 文本编辑验证器, 防止输入数字以外的其他信息
    def validate(self, input_str, pos_int):  # 文本输入验证器,保证输入为数字,为文本时则不显示(输入文本,光标位置)
        try:  # try-except异常处理机制
            if 0 <= float(input_str) <= 999999:  # 输入结果有效, 如若输入文本为字母则不显示
                return (QValidator.Acceptable, input_str, pos_int)
            else:
                return (QValidator.Invalid, input_str, pos_int)
        except:
            if len(input_str) == 0:
                return (QValidator.Intermediate, input_str, pos_int)  # 文本框清空则进入待定状态
            return (QValidator.Invalid, input_str, pos_int)

class Awp_plot_demo(QWidget):

    #  通过类成员对象定义信号对象
    # _startThread = pyqtSignal()

    # 初始化
    def __init__(self):
        super(Awp_plot_demo, self).__init__()

        # 参数定义
        self.ip = ''
        self.port = ''
        self.socket_flag = 0  # socket建立标志
        self.NFFT = 8192*2  # FFT点数设置
        self.timeout = 1  # fpga返回数据等待时间
        self.pic_path = 'spec_2.png'
        self.AMPTITUD_MAX = 2 ** 16  # 幅度归一化值
        self.buffuer_size = 1024  # 设置缓冲区大小
        self.pen_sepc = pg.mkPen(color="#33FFCC")  # 频谱绘图颜色
        self.pen_time_I = pg.mkPen(color="#1E90FF")  # 时域绘图颜色 I
        self.pen_time_Q = pg.mkPen(color="#A52A2A")  # 时域绘图颜色 Q

        self.file_name = './' + 'base_IQ' + '_'  # 设置IQ数据保存路径
        self.styles = {"color": "#FFFFFF", "font-size": "20px"}  # 设置网格样式

        # 建立socket套接字
        # self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        # self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.buffuer_size)  # 设置套接字层选项,并设置发送和接收缓冲区大小
        # self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, self.buffuer_size)

        # 左上方图片
        self.pix = QPixmap(self.pic_path)
        self.spec_pic = QLabel(self)
        self.spec_pic.setPixmap(self.pix)
        self.setWindowTitle('Usrp_Spectrum_Plot')
        self.setWindowIcon(QIcon('awp_logo.png'))

        # 实例化文本框控件
        self.IP = QLineEdit(self)  # IP输入框
        self.port_num = QLineEdit(self)  # 端口号输入框
        self.center_fre = QLineEdit(self)  # 中心频率输入框
        self.sub_fre = QLineEdit(self)  # 子频率输入框
        # self.sample_rate = QLineEdit(self)  # 采样率输入框
        # self.duration = QLineEdit(self)  # 时间输入框

        # 设置文本框的默认浮现文本
        # self.IP.setPlaceholderText('设备IP')
        # self.port_num.setPlaceholderText('端口号')
        self.IP.setText('192.168.3.242')
        self.port_num.setText('7755')
        self.center_fre.setPlaceholderText('中心频率:fc(MHz)')
        self.sub_fre.setPlaceholderText('子频率:f_sub(MHz)')
        # self.sample_rate.setPlaceholderText('采样率:fs(MHz),输入范围:0-3')
        # self.duration.setPlaceholderText('采样时间:ts(s),输入范围:1-5')
        self.IP.setStyleSheet('color:cyan')
        self.port_num.setStyleSheet('color:cyan')
        self.center_fre.setStyleSheet('color:cyan')
        self.sub_fre.setStyleSheet('color:cyan')
        # self.sample_rate.setStyleSheet('color:cyan')
        # self.duration.setStyleSheet('color:cyan')

        # 下拉复选框控件
        self.sample_rate = QComboBox(self)  # 采样率复选
        self.duration = QComboBox(self)  # 采样时间复选
        self.gain = QComboBox(self)  # 天线增益复选
        self.sample_rate.setStyleSheet("QComboBox{color:cyan}")
        self.duration.setStyleSheet("QComboBox{color:cyan}")
        self.gain.setStyleSheet("QComboBox{color:cyan}")

        # 添加复选框条目
        self.sample_rate.addItems(['122.88MHz', '61.44MHz', '30.72MHz', '15.36MHz'])
        self.duration.addItems(['10ms', '20ms', '30ms', '40ms', '50ms'])
        self.gain.addItems(['1', '10', '20', '30', '40', '55'])

        # 设置验证器
        validator = Validator()  # 实例化验证器
        self.center_fre.setValidator(validator)  # 设置输入文本框验证器
        self.sub_fre.setValidator(validator)  # 设置输入文本框验证器
        self.port_num.setValidator(validator)  # 设置输入文本框验证器

        # 实例化按钮控件
        self.single = QPushButton('单次绘制', self)  # 单次载入数据
        self.continuous = QPushButton('实时绘制', self)  # 持续载入数据
        self.udp_connect = QPushButton('连接设备', self)  # 建立 fpga
        self.udp_disconnect = QPushButton('断开设备', self)  # 断开 fpga
        self.single.setFixedSize(110, 50)  # 设置按钮大小
        self.continuous.setFixedSize(110, 50)  # 设置按钮大小
        self.udp_connect.setFixedSize(110, 50)  # 设置按钮大小
        self.udp_disconnect.setFixedSize(110, 50)  # 设置按钮大小
        self.single.setStyleSheet("QPushButton""{""background-color : none;""}"
                             "QPushButton:pressed""{""background-color : cyan;""}"
                             )  # 设置按下和释放后的背景颜色
        self.continuous.setStyleSheet("QPushButton""{""background-color : none;""}"
                             "QPushButton:pressed""{""background-color : cyan;""}"
                             )  # 设置按下和释放后的背景颜色
        self.udp_connect.setStyleSheet("QPushButton""{""background-color : none;""}"
                             "QPushButton:pressed""{""background-color : cyan;""}"
                             )  # 设置按下和释放后的背景颜色
        self.udp_disconnect.setStyleSheet("QPushButton""{""background-color : none;""}"
                             "QPushButton:pressed""{""background-color : cyan;""}"
                             )  # 设置按下和释放后的背景颜色

        # 实例化并设置频谱绘图对象控件
        self.graph_plot_spec = pg.PlotWidget()
        self.graph_plot_spec.setBackground('k')  # 设置图表标题和颜色
        self.graph_plot_spec.setTitle("频谱图", color="w", size="14pt")
        self.graph_plot_spec.setLabel("bottom", "频率(MHz)", **self.styles)
        self.graph_plot_spec.setLabel("left", "功率谱密度(dB/Hz)", **self.styles)
        self.graph_plot_spec.showGrid(x=True, y=True)  # 绘制网格线
        # self.graph_plot_spec.setXRange(-16, 16)  # 设置y轴范围

        # 实例化并设置xx绘图对象控件
        self.graph_plot_time = pg.PlotWidget()
        self.graph_plot_time.setBackground('k')  # 设置图表标题和颜色
        self.graph_plot_time.setTitle("时域图", color="w", size="14pt")
        self.graph_plot_spec.setLabel("left", "幅度", **self.styles)
        self.graph_plot_time.setLabel("bottom", "时间(s)", **self.styles)
        self.graph_plot_time.showGrid(x=True, y=True)  # 绘制网格线

        # 实例化并设置xx绘图对象控件
        self.graph_plot_2 = pg.PlotWidget()
        self.graph_plot_2.setBackground('k')  # 设置图表标题和颜色
        self.graph_plot_2.setTitle("时频图", color="w", size="14pt")
        self.graph_plot_2.setLabel("bottom", "频率(MHz)", **self.styles)
        self.graph_plot_2.showGrid(x=True, y=True)  # 绘制网格线

        # 槽函数
        self.udp_connect.clicked.connect(self.device_con)  # 与服务端连接
        self.udp_disconnect.clicked.connect(self.device_discon)  # 与服务端断连
        self.single.clicked.connect(self.single_trigger)   # 设置单次绘制
        self.continuous.clicked.connect(self.continuous_trigger)   # 设置实时绘制
        self.center_fre.editingFinished.connect(self.para_input)  # 结束编辑传值
        self.sub_fre.editingFinished.connect(self.para_input)  # 结束编辑传值
        self.sample_rate.activated.connect(self.para_input)  # 用户选中则发射该信号
        self.duration.activated.connect(self.para_input)  # 用户选中则发射该信号
        self.gain.activated.connect(self.para_input)  # 用户选中则发射该信号
        self.IP.editingFinished.connect(self.ip_input)  # 结束编辑传值
        self.port_num.editingFinished.connect(self.ip_input)  # 结束编辑传值
        self.port_num.returnPressed.connect(self.ip_input_control)  # 回车之后不可编辑

        # 界面布局
        self.trigger_h_layout = QHBoxLayout()  # 触发按钮布局
        self.connect_h_layout = QHBoxLayout()  # 连接按钮布局
        self.grid = QGridLayout()  # 网格布局文本框
        self.left = QVBoxLayout()  # 网格布局文本框和按钮
        self.plot_layout = QVBoxLayout()  # 设置水平绘图布局
        self.all_layout = QHBoxLayout()  # 设置整体布局
        # 按钮布局
        self.trigger_h_layout.addWidget(self.single)  # 水平布局单次触发按钮
        self.trigger_h_layout.addWidget(self.continuous)  # 水平布局实时触发按钮
        self.connect_h_layout.addWidget(self.udp_connect)  # 水平布局连接按钮
        self.connect_h_layout.addWidget(self.udp_disconnect)  # 水平布局断连按钮
        # 绘图布局
        self.plot_layout.addWidget(self.graph_plot_spec)
        self.plot_layout.addWidget(self.graph_plot_time)
        # self.plot_layout.addWidget(self.graph_plot_2)

        # 网格布局
        self.grid.addWidget(self.IP, 0, 0, 1, 3)
        self.grid.addWidget(self.port_num, 1, 0, 1, 3)
        self.grid.addWidget(self.center_fre, 2, 0, 1, 3)
        self.grid.addWidget(self.sub_fre, 3, 0, 1, 3)
        self.grid.addWidget(self.sample_rate, 4, 0, 1, 3)
        self.grid.addWidget(self.duration, 5, 0, 1, 3)
        self.grid.addWidget(self.gain, 6, 0, 1, 3)

        self.left.addWidget(self.spec_pic)
        self.left.addLayout(self.trigger_h_layout)
        self.left.addLayout(self.connect_h_layout)
        self.left.addLayout(self.grid)
        self.left.setSpacing(16)  # 设置间距

        self.all_layout.addLayout(self.left)  # 界面总体布局加入上端控件
        self.all_layout.addLayout(self.plot_layout)  # 界面总体布局加入绘图控件
        self.setLayout(self.all_layout)  # 完成布局设置

    # 槽函数
    def single_trigger(self):
        print('>>>single plot...')
        self.graph_plot_spec.clear()  # 清除绘图
        self.graph_plot_time.clear()  # 清除绘图
        self.single_thread = threading.Thread(target=self.send_plot)
        self.single_thread.start()

    def continuous_trigger(self):
        print('>>>continuous plot...')
        self.graph_plot_spec.clear()  # 清除绘图
        self.graph_plot_time.clear()  # 清除绘图
        self.continuous_thread = threading.Thread(target=self.loop_send_plot)
        self.continuous_thread.start()

    def device_con(self):
        try:
            self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)  # 建立socket套接字
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.buffuer_size)  # 设置套接字层选项,并设置发送和接收缓冲区大小
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, self.buffuer_size)
            self.sock.connect((self.ip, int(self.port)))  # 绑定ip和端口并设置连接
            state = self.sock.getpeername()
            if state:
                print('建立成功!服务器地址和端口号为:{}'.format(state))
                self.socket_flag = 1
                self.udp_connect.setText('建立成功')
                self.udp_disconnect.setText('断开设备')
        except socket.error as e:
            print('Connection failed.', e)

    def device_discon(self):
        if self.socket_flag == 1:
            self.sock.shutdown(2)  # 0代表禁止下次数据读取;1代表禁止下次写入数据;2代表禁止下次数据读取和写入;
            self.sock.close()  # 断开与服务器之间的连接
            print('已与服务器断开')
            self.socket_flag = 0
            self.udp_connect.setText('连接设备')
            self.udp_disconnect.setText('已断开')
            self.center_fre.setEnabled(True)  # 设置可编辑
            self.sub_fre.setEnabled(True)  # 设置可编辑
            # self.sample_rate.setEnabled(True)  # 设置可编辑
            # self.duration.setEnabled(True)  # 设置可编辑
            self.IP.setEnabled(True)  # 设置可编辑
            self.port_num.setEnabled(True)  # 设置可编辑
        else:
            print('服务器尚未连接')
            self.udp_disconnect.setText('尚未连接')
            self.IP.setEnabled(True)  # 设置不可编辑
            self.port_num.setEnabled(True)  # 设置不可编辑

    def para_input(self):  # 参数输入读取
        fs_real = 0
        ts_real = 0
        fc = self.center_fre.text()   # 从输入框获得中心频率信息
        f_sub = self.sub_fre.text()  # 从输入框获得子频率信息
        fs = self.sample_rate.currentText()     # 从输入框获得采样率信息
        ts = self.duration.currentText()  # 从输入框获得采样时间信息
        gain = self.gain.currentText()  # 从输入框获得增益信息
        if fs == '122.88MHz':  # 转换为实际采样率
            fs_real = 0
        elif fs == '61.44MHz':
            fs_real = 1
        elif fs == '30.72MHz':
            fs_real = 2
        elif fs == '15.36MHz':
            fs_real = 3
        if ts == '10ms':  # 转换为实际采样率
            ts_real = 1
        elif ts == '20ms':
            ts_real = 2
        elif ts == '30ms':
            ts_real = 3
        elif ts == '40ms':
            ts_real = 4
        elif ts == '50ms':
            ts_real = 5
        para_input = '%s,%s,%s,%s' % (fc, f_sub, fs_real, ts_real)  # 输入参数字符串
        gain_input = '%s,%s' % ('gain', gain)  # 输入参数字符串
        print(type(para_input))
        print('读入参数 :{}'.format(para_input))
        print('增益设置 :{}'.format(gain_input))
        return para_input, gain_input

    def ip_input(self):
        self.ip = self.IP.text()     # 从输入框获得用户输入的文本信息，单行显示
        self.port = self.port_num.text()  # 从输入框获得用户输入的文本信息，单行显示

    def ip_input_control(self):  # 参数输入读取
        self.IP.setEnabled(False)  # 设置不可编辑
        self.port_num.setEnabled(False)  # 设置不可编辑

    def para_input_control(self):  # 参数输入读取
        self.center_fre.setEnabled(False)  # 设置不可编辑
        self.sub_fre.setEnabled(False)  # 设置不可编辑
        # self.sample_rate.setEnabled(False)  # 设置不可编辑
        # self.duration.setEnabled(False)  # 设置不可编辑

    def send_plot(self):
        try:
            [b, a] = self.para_input()
            self.sock.sendto(str.encode(a), (self.ip, int(self.port)))  # 设定向设备发送参数(接收增益)
            self.sock.sendto(str.encode(b), (self.ip, int(self.port)))  # 设定向设备发送参数(中心频率、子频率、采样率、采样时间)
        except Exception as e:  # 捕获所有其他异常的通用处理
            print('尚未建立成功...', e)
        else:
            print("获取设备数据中...... (UDP)")
            msgFromServer = self.sock.recvfrom(self.buffuer_size)  # 从设备获取数据
            rev_data_length = len(msgFromServer[0])  # 数据长度
            rcv_data = msgFromServer[0]  # 接收数据
            print('第一次接收的数据长度:{},数据类型:{}.'.format(rev_data_length, type(rcv_data)))
            # 设备返回的参数
            freq_kHz = (rcv_data[0] * (1 << 24) + rcv_data[1] * (1 << 16) + rcv_data[2] * (1 << 8) + rcv_data[3])
            sample_rate = (rcv_data[4] * (1 << 24) + rcv_data[5] * (1 << 16) + rcv_data[6] * (1 << 8) + rcv_data[7])
            time_stamp = (rcv_data[8] * (1 << 24) + rcv_data[9] * (1 << 16) + rcv_data[10] * (1 << 8) + rcv_data[11])
            print('设备返回参数,中心频率:{}MHz;采样率:{};时间戳:{}.'.format(freq_kHz / 1e3, sample_rate, time_stamp))
            while True:
                ready = select.select([self.sock], [], [], self.timeout)
                if ready[0]:
                    msgFromServer = self.sock.recvfrom(self.buffuer_size)
                    rcv_data += msgFromServer[0]
                    rev_data_length += len(msgFromServer[0])
                    self.graph_plot_spec.clear()  # 清除绘图
                    self.graph_plot_time.clear()  # 清除绘图
                else:
                    print('数据已被接收,长度为{}'.format(len(rcv_data)))
                    td = self.bytes_to_td(rcv_data)
                    fre, pwr = signal.welch(td, fs=self.sr_match(sample_rate), nperseg=self.NFFT, return_onesided=False, detrend=False)
                    t = np.linspace(0, len(td), len(td))
                    self.graph_plot_spec.plot().setData(np.fft.fftshift(fre/1e6), np.fft.fftshift(10 * np.log10(pwr)), pen=self.pen_sepc)  # 用scipy的这个函数需要shift否则会有一根显示DC的直线
                    self.graph_plot_time.plot().setData(t/self.sr_match(sample_rate), td.real, pen=self.pen_time_I)  # 绘制时域I
                    self.graph_plot_time.plot().setData(t/self.sr_match(sample_rate), td.imag, pen=self.pen_time_Q)  # 绘制时域Q
                    self.save_data_to_csv(self.file_name, td)  # 保存数据
                    break

    def loop_send_plot(self):  # 数据获取
        while True:
            self.send_plot()

    def sr_match(self, sr):  # 采样率匹配
        sr_real = 1
        if sr == 0:  # 转换为实际采样率
            sr_real = 122.88e6
        elif sr == 1:
            sr_real = 61.44e6
        elif sr == 2:
            sr_real = 30.72e6
        elif sr == 3:
            sr_real = 15.36e6
        return sr_real

    def bytes_to_td(self, message):  # 字节数据转为IQ数据
        # IQ数据
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
            i_val = i_hex / self.AMPTITUD_MAX  # 归一化
            q_val = q_hex / self.AMPTITUD_MAX  # 归一化
            td[i] = i_val + q_val * 1.j
        td_dcr_i = td.real - np.mean(td.real)  # 去均值
        td_dcr_q = td.imag - np.mean(td.imag)  # 去均值
        td_dcr = td_dcr_i + td_dcr_q * 1.j
        return td_dcr

    def save_data_to_csv(self, path, td_data):  # 保存基带IQ数据.csv
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
        print('文件保存路径为:{}'.format(save_path))
        return save_path

if __name__ == '__main__':
    app = QApplication(sys.argv)  # 在app实例化之后，应用样式
    apply_stylesheet(app, theme='default_dark.xml')
    Awp_plot = Awp_plot_demo()
    # Awp_plot.showMinimized()
    Awp_plot.show()
    sys.exit(app.exec_())