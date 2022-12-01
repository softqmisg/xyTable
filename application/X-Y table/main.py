from msilib.schema import Dialog
from pickle import FALSE
from tokenize import String
from turtle import isvisible
from matplotlib.backend_bases import MouseEvent


from PyQt5 import QtCore, QtGui, QtWidgets,uic
import PyQt5
from PyQt5.QtWidgets import QApplication,QStyle,QMessageBox,QFileDialog
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QThread,QByteArray,QEvent,QObject,QPoint
from PyQt5.QtGui import QPixmap
import sys
import cv2
import numpy as np
import datetime
import os
import x_y_ui_large as x_y_ui

class HoverTracker(QObject):
    positionChanged = pyqtSignal(QPoint)
    def __init__(self, widget):
        super().__init__(widget)
        self._widget = widget
        self.widget.setMouseTracking(True)
        self.widget.installEventFilter(self)

    @property
    def widget(self):
        return self._widget

    def eventFilter(self, obj, event):
        if obj is self.widget and event.type() == QEvent.MouseMove:
            self.positionChanged.emit(event.pos())
        return super().eventFilter(obj, event)

class Qlabel_Clickable(QtWidgets.QLabel):
    clicked=pyqtSignal(QtGui.QMouseEvent)
    enter=pyqtSignal(QtGui.QEnterEvent)
    def __init__(self,parent=None):
        QtWidgets.QLabel.__init__(self, parent=parent)

    def mousePressEvent(self, ev):
        self.clicked.emit(ev)
    def enterEvent(self,ev):
        self.enter.emit(ev)

class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    disablebutton_signal = pyqtSignal(np.ndarray)
    def __init__(self,cap):
        super().__init__()
        self._run_flag = True
        self.cap=cap
    def run(self):
        # capture from web cam
        while self._run_flag:
            ret, cv_img = self.cap.read()
            ret=True
            if ret:
                self.change_pixmap_signal.emit(cv_img)
        # shut down capture system
        self.cap.release()

    def stop(self):
        """Sets run flag to False and waits for thread to finish"""
        self._run_flag = False
        self.wait()

class mainApp(QtWidgets.QDialog, x_y_ui.Ui_Dialog):

    def __init__(self, parent=None) :
        super(mainApp,self).__init__(parent)
        self.setupUi(self)

        icons = sorted([attr for attr in dir(QStyle) if attr.startswith("SP_")])
        name=icons[6]
        pixmapi = getattr(QStyle, name)
        icon = self.style().standardIcon(pixmapi)
        self.refreshButton.setIcon(icon)

        
        self.disply_width = 640
        self.display_height = 360

        self.imageLabel=Qlabel_Clickable(self)
        self.imageLabel.setGeometry(600, 35, self.disply_width, self.display_height)
        self.imageLabel.setText("")
        self.imageLabel.clicked.connect(self.on_imageLabel_clicked)
        self.imageLabel.enter.connect(self.on_imageLabel_enter)
        hover_tracking=HoverTracker(self.imageLabel)
        hover_tracking.positionChanged.connect(self.on_position_changed)

        self.fullviewDialog = None
        self.fullviewDialog = QtWidgets.QDialog(self)
        self.fullviewDialog.setWindowTitle('Full View')
        self.fullviewDialog.resize(1920, 1080)
        self.fullviewDialog.fullviewLabel=QtWidgets.QLabel(self.fullviewDialog)
        self.fullviewDialog.fullviewLabel.resize(1920,1080) 
        self.fullviewDialog.setVisible(False)       
        
        self.m_serial=QSerialPort()
        self.portscomboBox.addItems([ port.portName() for port in QSerialPortInfo().availablePorts() ])        
        self.m_serial.readyRead.connect(self.readData)  
        self.delayLabel.setText(str(self.delaySlider.value())) 

        self.cap  = cv2.VideoCapture(0)#,cv2.CAP_DSHOW) 
        if(not self.cap.isOpened()):
            self.captureButton.setEnabled(False)
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Camera problem")
            msg.setInformativeText("Camera is not found")
            msg.setWindowTitle("Warning")
            msg.setStandardButtons(QMessageBox.Ok )
            msg.exec_()            
            self.cap.release()
        else :
            codec = 0x47504A4D  # MJPG
            self.cap.set(cv2.CAP_PROP_FPS, 30.0)
            self.cap.set(cv2.CAP_PROP_FOURCC, codec)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE,0.9)

            self.thread = VideoThread(self.cap)
            self.thread.change_pixmap_signal.connect(self.update_image)
            self.thread.start()
            self.exposureSlider.setValue(int(self.cap.get(cv2.CAP_PROP_EXPOSURE)))  
            self.exposureSlider.valueChanged.connect(self.on_exposureSlider_valueChanged)
            self.exposureLabel.setText(str(self.exposureSlider.value()))        
            self.gainSlider.setValue(int(self.cap.get(cv2.CAP_PROP_GAIN)))  
            self.gainSlider.valueChanged.connect(self.on_gainSlider_valueChanged)
            self.gainLabel.setText(str(self.gainSlider.value()))        
            self.autoexposurecheckBox.clicked.connect(self.on_autoexposurecheckBox_clicekd)

        self.capturetrig=False
        self.getposition=True
        self.capturenamex=0
        self.capturenamey=0
        self.bufferstr=""
        self.framestate=0
        # self.iscapture=False
        self.isprofilerunning=False
        self.folderimage="."
        self.mousepositionx=0
        self.mousepositiony=0
        self.mouseclickedx=0
        self.mouseclickedy=0

        self.singlecapture=False
        self.clickedcross=False


    def readData(self):
        data = self.m_serial.readAll()
        str_data=bytes(data.data()).decode('utf-8')
        # print(str_data)
        if(str_data.find('@')!=-1):
            self.framestate=1
            self.bufferstr=""
            str_data= str_data[str_data.find('@'):]
        if(self.framestate==1):
            self.bufferstr=self.bufferstr+str_data
            if(str_data.find('\n')!=-1):
                self.framestate=2
                receivedframe=self.bufferstr[:self.bufferstr.find('\n')]
                self.bufferstr=self.bufferstr[self.bufferstr.find('\n')+1:]
                # print("end frame:"+self.bufferstr)
        if(self.framestate==2):
            self.framestate=0
            deliminatedstr=receivedframe.split(',')

            if(deliminatedstr[0]=="@trigcapture"):
                self.capturenamex=eval(deliminatedstr[1])
                self.capturenamey=eval(deliminatedstr[2])
                self.currentcellLabel.setText("("+str(self.capturenamex)+","+str(self.capturenamey)+")")                 
                # self.iscapture=True
                self.capturetrig=True
            elif(deliminatedstr[0]=="@endprofile"):
                self.startprofileButton.setText("Start Profile")
                self.capturenamex=0
                self.capturenamey=0   
                # self.iscapture=False  
                self.isprofilerunning=False     
                self.currentcellLabel.setText("")   
            elif(deliminatedstr[0]=="@position"):
                xpos=float(deliminatedstr[1])
                ypos=float(deliminatedstr[2])
                self.xposLabel.setText(str(eval(deliminatedstr[1])))
                self.yposLabel.setText(str(eval(deliminatedstr[2])))   
                # print(str(xpos)+" "+str(ypos))
                self.getposition=True  
            elif(deliminatedstr[0]=="@wakeup"):
                cmd="reset\n"
                res=bytes(cmd, 'utf-8')
                self.writeData(res)                          
            # self.bufferstr=""

    def writeData(self, data):        
        self.m_serial.write(data)
    
    # @QtCore.pyqtSlot(np.ndarray)
    # def disablecapture(self,dummy):
    #     self.captureButton.setEnabled(False)
    #     msg = QMessageBox()
    #     msg.setIcon(QMessageBox.Warning)
    #     msg.setText("Camera problem")
    #     msg.setInformativeText("Camera is not found")
    #     msg.setWindowTitle("Warning")
    #     msg.setStandardButtons(QMessageBox.Ok )
    #     msg.exec_()

    @QtCore.pyqtSlot(np.ndarray)
    def update_image(self, cv_img):
        """Updates the image_label with a new opencv image"""
        if(self.capturetrig):
            self.capturetrig=False
            current_time = datetime.datetime.now()
            current_time=datetime.datetime(current_time.year-2000,\
                                            current_time.month,\
                                            current_time.day,\
                                            current_time.hour,\
                                            current_time.minute,\
                                            current_time.second,\
                                            current_time.microsecond)            
            namefile=str('{:02d}'.format(current_time.year))+"_"+\
                str('{:02d}'.format(current_time.month))+"_"+\
                str('{:02d}'.format(current_time.day))+" "+\
                str('{:02d}'.format(current_time.hour))+"_"+\
                str('{:02d}'.format(current_time.minute))+"_"+\
                str('{:02d}'.format(current_time.second))+"."+\
                str('{:02d}'.format(int(current_time.microsecond/10000)))+"_"+\
                "{:02d}".format(self.capturenamex)+"_"+\
                "{:02d}".format(self.capturenamey)+".jpg" 
            namefile =self.folderimage+"/"+namefile
            if(self.autocapturecheckBox.isChecked() or self.singlecapture):
                self.singlecapture=False
                cv2.imwrite(namefile, cv_img,[int(cv2.IMWRITE_JPEG_QUALITY), 100])        
            cmd="resumeprofile\n"
            res=bytes(cmd, 'utf-8')
            self.writeData(res)

        cv_image_scale=cv2.resize(cv_img,[self.disply_width, self.display_height])
        if(self.crosscheckBox.isChecked()):
            if(self.clickedcross):
                cv2.line(img=cv_image_scale, pt1=(0, self.mouseclickedy), pt2=(self.disply_width, self.mouseclickedy), color=(0, 0, 255), thickness=1, lineType=8, shift=0)
                cv2.line(img=cv_image_scale, pt1=(self.mouseclickedx, 0), pt2=(self.mouseclickedx,self.display_height), color=(0, 0, 255), thickness=1, lineType=8, shift=0)   
            else:
                cv2.line(img=cv_image_scale, pt1=(0, self.mousepositiony), pt2=(self.disply_width, self.mousepositiony), color=(0,255, 255), thickness=1, lineType=8, shift=0)
                cv2.line(img=cv_image_scale, pt1=(self.mousepositionx, 0), pt2=(self.mousepositionx,self.display_height), color=(0,255,  255), thickness=1, lineType=8, shift=0)   
        else:
            self.clickedcross=False

        cv_qimage = self.convert_cv_image(cv_image_scale)
        self.imageLabel.setPixmap(QPixmap.fromImage(cv_qimage))

        if self.fullviewDialog.isVisible():
            if(self.crosscheckBox.isChecked()):
                cv2.line(img=cv_img, pt1=(0, self.mouseclickedy*3), pt2=(self.disply_width*3, self.mouseclickedy*3), color=(0, 0, 255), thickness=1, lineType=8, shift=0)
                cv2.line(img=cv_img, pt1=(self.mouseclickedx*3, 0), pt2=(self.mouseclickedx*3,self.display_height*3), color=(0, 0, 255), thickness=1, lineType=8, shift=0)  
            cv_qimage_full = self.convert_cv_image(cv_img)
            self.fullviewDialog.fullviewLabel.setPixmap(QPixmap.fromImage(cv_qimage_full))
   
    def convert_cv_image(self, cv_img):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2BGRA)    
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_ARGB32)
        return convert_to_Qt_format
  
    @QtCore.pyqtSlot()
    def on_fullviewButton_clicked(self):
        self.fullviewDialog.setVisible(True)
        self.fullviewDialog.show()

    def on_imageLabel_clicked(self,ev):
        self.mouseclickedx=ev.pos().x()
        self.mouseclickedy=ev.pos().y()
        self.clickedcross=True

    def on_imageLabel_enter(self,ev):
        # print(ev.pos().x(),ev.pos().y())
        pass

    @QtCore.pyqtSlot(QPoint)
    def on_position_changed(self, p):
        self.mousepositionx=p.x()
        self.mousepositiony=p.y()

    def on_autoexposurecheckBox_clicekd(self):
        if(self.autoexposurecheckBox.isChecked()):
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE,0.9)
        else:
            self.cap.set(cv2.CAP_PROP_EXPOSURE,self.exposureSlider.value()) 

    def on_gainSlider_valueChanged(self):
        self.cap.set(cv2.CAP_PROP_GAIN,self.gainSlider.value())  

    def on_exposureSlider_valueChanged(self):
        self.cap.set(cv2.CAP_PROP_EXPOSURE,self.exposureSlider.value())   

    @QtCore.pyqtSlot()
    def on_captureButton_clicked(self):
        self.capturetrig=True
        self.singlecapture=True
        print("clicked capture")
    
    @QtCore.pyqtSlot()    
    def on_refreshButton_clicked(self):
        self.portscomboBox.clear()
        self.portscomboBox.addItems([ port.portName() for port in QSerialPortInfo().availablePorts() ])        

    @QtCore.pyqtSlot()    
    def on_opencloseButton_clicked(self):
        self.m_serial.setPortName(self.portscomboBox.currentText())
        # print(self.portscomboBox.currentText())
        self.m_serial.setBaudRate(QSerialPort.BaudRate.Baud115200)
        self.m_serial.setDataBits(QSerialPort.DataBits.Data8)
        self.m_serial.setStopBits(QSerialPort.StopBits.OneStop)
        self.m_serial.setParity(QSerialPort.Parity.NoParity)
        if (not self.m_serial.isOpen()): #port is close
            r= self.m_serial.open(QtCore.QIODevice.ReadWrite)
            if not r:
                print('Port open error' )
                self.opencloseButton.setChecked(False)
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setText("Comport problem")
                msg.setInformativeText("Comport could not be opend")
                msg.setWindowTitle("Warning")
                msg.setStandardButtons(QMessageBox.Ok )
                msg.exec_()
            else:
                self.opencloseButton.setText("Close")
                print('Port opened' )
                self.opencloseButton.setChecked(True)
        else: #port is open
            self.m_serial.close()
            self.opencloseButton.setChecked(False)
            self.opencloseButton.setText("Open")

    @QtCore.pyqtSlot()        
    def on_movexButton_pressed(self):
        cmd=""
        if(self.xcontcheckBox.isChecked() and self.getposition):
            self.getposition=False
            cmd="movcxy,"+str(self.movexstepSpin.value())+",0\n"
        res = bytes(cmd, 'utf-8')
        self.writeData(res)

    @QtCore.pyqtSlot()        
    def on_movexButton_clicked(self):
        cmd=""
        if(not self.xcontcheckBox.isChecked()):
            cmd="movxy,"+str(self.movexstepSpin.value())+",0\n"
        # print(cmd)
        res = bytes(cmd, 'utf-8')
        self.writeData(res)
        # self.serialPort.write((res)) 

    @QtCore.pyqtSlot()    
    def on_movexButton_released(self):
        cmd="stopc\n"
        res = bytes(cmd, 'utf-8')
        self.writeData(res)
        # self.serialPort.write((res))        

    @QtCore.pyqtSlot()   
    def on_moveyButton_pressed(self):
        cmd=""
        if(self.ycontcheckBox.isChecked() and self.getposition):
            self.getposition=False
            cmd="movcxy,0,"+str(self.moveystepSpin.value())+"\n"
        # print(cmd)
        res = bytes(cmd, 'utf-8')
        self.writeData(res)

    @QtCore.pyqtSlot()   
    def on_moveyButton_clicked(self):
        cmd=""
        if(not self.ycontcheckBox.isChecked()):
            cmd="movxy,0,"+str(self.moveystepSpin.value())+"\n"
        # print(cmd)
        res = bytes(cmd, 'utf-8')
        self.writeData(res)

    @QtCore.pyqtSlot()          
    def on_moveyButton_released(self):
        cmd="stopc\n"
        # print(cmd)
        res = bytes(cmd, 'utf-8')
        # self.serialPort.write((res))  
        self.writeData(res)

    @QtCore.pyqtSlot()          
    def on_stopButton_released(self):
        self.isprofilerunning=False
        cmd="stopc\n"
        res = bytes(cmd, 'utf-8')
        self.writeData(res)

    @QtCore.pyqtSlot()   
    def on_rampxyButton_clicked(self):
        cmd="rampxy,"+str(self.movexstepSpin.value())+","+str(self.moveystepSpin.value())+"\n"
        # print(cmd)
        res = bytes(cmd, 'utf-8')
        # self.serialPort.write((res)) 
        self.writeData(res)

    @QtCore.pyqtSlot()   
    def on_setzeroButton_clicked(self):
        cmd="setzero\n"
        res = bytes(cmd, 'utf-8')
        self.writeData(res)

    @QtCore.pyqtSlot()   
    def on_movtozeroButton_clicked(self):
        cmd="mov2zero\n"
        # print(cmd)
        res = bytes(cmd, 'utf-8')
        # self.serialPort.write(res)        
        self.writeData(res)
    
    @QtCore.pyqtSlot()
    def on_selectfolderButton_clicked(self):
        # options = QFileDialog.Options()
        # options |= QFileDialog.ShowDirsOnly
        # dir,check=QFileDialog.getOpenFileName(self,"Select File","", "", options=options)
        # if(check):
        #     self.folderimage=dir
        dir=QFileDialog.getExistingDirectory(self, "Select Directory")
        self.folderimage = str(dir)
        print(self.folderimage)

    @QtCore.pyqtSlot()
    def on_loadButton_clicked(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"Load Profile setting", "","All Files (*);;xy Files (*.xy)", options=options)
        if(fileName):
            print(fileName)
            f=open(fileName,"r")
            line=f.readline()
            splittedtext=line.split(",")
            if(splittedtext[0]=="profile"):
                self.numxcellsSpin.setValue(eval(splittedtext[1]))
                self.pitchxSpin.setValue(eval(splittedtext[2]))
                self.offsetxSpin.setValue(eval(splittedtext[3]))
                self.numycellsSpin.setValue(eval(splittedtext[4]))
                self.pitchySpin.setValue(eval(splittedtext[5]))
                self.offsetySpin.setValue(eval(splittedtext[6]))
                self.delaySlider.setValue(eval(splittedtext[7]))
                self.autocapturecheckBox.setChecked(eval(splittedtext[8]))

    @QtCore.pyqtSlot()
    def on_saveButton_clicked(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, check = QFileDialog.getSaveFileName(self,"Save Profile setting", "","All Files (*);;xy Files (*.xy)", options=options)
        if(check):
            print(fileName)
            f=open(fileName,"w")
            savetext="profile,"+\
                str(self.numxcellsSpin.value())+","+\
                str(self.pitchxSpin.value())+","+\
                str(self.offsetxSpin.value())+","+\
                str(self.numycellsSpin.value())+","+\
                str(self.pitchySpin.value())+","+\
                str(self.offsetySpin.value())+","+\
                str(self.delaySlider.value())+","+\
                str(self.autocapturecheckBox.isChecked())+"\n"
            print("save:"+savetext)
            f.write(savetext)

    @QtCore.pyqtSlot()
    def on_startprofileButton_clicked(self):
        if not self.isprofilerunning:
            print(">>>>>>>>>>>profile")
            self.isprofilerunning=True
            self.startprofileButton.setText("Stop Profile")
            cmd="profile,"+\
                str(self.numxcellsSpin.value())+","+\
                str(self.pitchxSpin.value())+","+\
                str(self.offsetxSpin.value())+","+\
                str(self.numycellsSpin.value())+","+\
                str(self.pitchySpin.value())+","+\
                str(self.offsetySpin.value())+","+\
                str(self.delaySlider.value())+","+\
                "1\n"
            res=bytes(cmd, 'utf-8')
            self.writeData(res)
        else :
            self.isprofilerunning=False
            self.startprofileButton.setText("Start Profile")
            cmd="stopc\n"
            res = bytes(cmd, 'utf-8')
            self.writeData(res)

    def closeEvent(self, event):
        if self.m_serial.isOpen():
            self.m_serial.close()
        self.thread.stop()
        self.fullviewDialog.close()
        print("closing")
        event.accept()        


def main():
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"]="1"
    if hasattr(QtCore.Qt,'AA_EnableHighDpiScaling'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling,True)
    if hasattr(QtCore.Qt,'AA_UseHighDpiPixmaps'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps,True)    
    app=QApplication(sys.argv)
    form=mainApp()
    form.show()
    app.exec_()
 
if __name__=='__main__':
    main()