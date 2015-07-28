import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from PyQt5.QtCore import QDir, QTimer, Qt, QPointF
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QFont, QPolygonF, QPen
from getMaskParams_ui import Ui_MainWindow

import json
import h5py
import os
import numpy as np
import sys
import cv2
import matplotlib.pylab as plt

import sys
sys.path.append('../..')
from MWTracker.compressVideos.compressVideo import getROIMask
from MWTracker.helperFunctions.compressVideoWorker import compressVideoWorker
from MWTracker.helperFunctions.getTrajectoriesWorker import getTrajectoriesWorker

class getMaskParams(QMainWindow):
	def __init__(self):
		super().__init__()
		
		# Set up the user interface from Designer.
		self.ui = Ui_MainWindow()
		self.ui.setupUi(self)

		self.ui.dial_min_area.valueChanged.connect(self.ui.spinBox_min_area.setValue)
		self.ui.dial_max_area.valueChanged.connect(self.ui.spinBox_max_area.setValue)
		self.ui.dial_block_size.valueChanged.connect(self.ui.spinBox_block_size.setValue)
		self.ui.dial_thresh_C.valueChanged.connect(self.ui.spinBox_thresh_C.setValue)

		self.ui.spinBox_max_area.valueChanged.connect(self.updateMaxArea)
		self.ui.spinBox_min_area.valueChanged.connect(self.updateMinArea)
		self.ui.spinBox_block_size.valueChanged.connect(self.updateBlockSize)
		self.ui.spinBox_thresh_C.valueChanged.connect(self.updateThreshC)

		self.mask_files_dir = '/Users/ajaver/Desktop/Pratheeban_videos/MaskedVideos/'
		self.results_dir = '/Users/ajaver/Desktop/Pratheeban_videos/Results/'
		self.video_file = ''

		self.videos_dir = '/Users/ajaver/Desktop/Pratheeban_videos/Worm_Videos/'
		self.buffer_size = 25
		self.Ifull = np.zeros(0)

		if not os.path.exists(self.mask_files_dir):
			self.mask_files_dir = ''
		
		if not os.path.exists(self.results_dir):
			self.results_dir = ''
					

		self.ui.lineEdit_mask.setText(self.mask_files_dir)
		self.ui.lineEdit_results.setText(self.results_dir)

		self.ui.pushButton_video.clicked.connect(self.getVideoFile)
		self.ui.pushButton_results.clicked.connect(self.updateResultsDir)
		self.ui.pushButton_mask.clicked.connect(self.updateMasksDir)
		
		self.ui.pushButton_start.clicked.connect(self.startAnalysis)

	#file dialog to the the hdf5 file
	def getVideoFile(self):
		video_file, _ = QFileDialog.getOpenFileName(self, "Find video file", 
		self.videos_dir, "MJPG files (*.mjpg);; All files (*)")

		if video_file:
			self.video_file = video_file
			if os.path.exists(self.video_file):
				self.ui.label_full.clear()
				self.Ifull = np.zeros(0)

				self.videos_dir = self.video_file.rpartition(os.sep)[0] + os.sep
				

				self.ui.lineEdit_video.setText(self.video_file)
				vid = cv2.VideoCapture(self.video_file);

				self.im_width= vid.get(cv2.CAP_PROP_FRAME_WIDTH)
				self.im_height= vid.get(cv2.CAP_PROP_FRAME_HEIGHT)
				if self.im_width == 0 or self.im_height == 0:
					 QMessageBox.critical(self, 'Cannot read video file.', "Cannot read video file. Try another file",
					QMessageBox.Ok)
					 return

				if 'Worm_Videos' in self.videos_dir:
					self.results_dir = self.videos_dir.replace('Worm_Videos', 'Results')
					self.mask_files_dir = self.videos_dir.replace('Worm_Videos', 'MaskedVideos')
				
				Ibuff = np.zeros((self.buffer_size, self.im_height, self.im_width), dtype = np.uint8)
				for ii in range(self.buffer_size):    
					ret, image = vid.read() #get video frame, stop program when no frame is retrive (end of file)
					if ret == 0:
						break
					Ibuff[ii] = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
				self.Imin = np.min(Ibuff, axis=0)
				self.Ifull = Ibuff[0]
				
				self.updateMask()

				self.updateImage()
			

	def updateImage(self):
		if self.Ifull.size == 0:
			return

		self.full_size = min(self.ui.label_full.height(), self.ui.label_full.width())
		
		image = QImage(self.Ifull.data, 
			self.im_width, self.im_height, self.Ifull.strides[0], QImage.Format_Indexed8)
		
		image = image.scaled(self.full_size, self.full_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
		self.img_w_ratio = image.size().width()/self.im_width;
		self.img_h_ratio = image.size().height()/self.im_height;
		
		pixmap = QPixmap.fromImage(image)
		self.ui.label_full.setPixmap(pixmap);

		self.mask_size = min(self.ui.label_mask.height(), self.ui.label_mask.width())
		mask = QImage(self.Imask.data, 
			self.im_height, self.im_width, self.Imask.strides[0], QImage.Format_Indexed8)
		
		mask = mask.scaled(self.mask_size, self.mask_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
		
		self.img_w_ratio = mask.size().width()/self.im_width;
		self.img_h_ratio = mask.size().height()/self.im_height;
		
		pixmap = QPixmap.fromImage(mask)
		self.ui.label_mask.setPixmap(pixmap);

	def updateMaxArea(self):
		self.ui.dial_max_area.setValue(self.ui.spinBox_max_area.value())
		self.updateMask()
		self.updateImage()

	def updateMinArea(self):
		self.ui.dial_min_area.setValue(self.ui.spinBox_min_area.value())
		self.updateMask()
		self.updateImage()

	def updateBlockSize(self):
		self.ui.dial_block_size.setValue(self.ui.spinBox_block_size.value())
		self.updateMask()
		self.updateImage()

	def updateThreshC(self):
		self.ui.dial_thresh_C.setValue(self.ui.spinBox_thresh_C.value())
		self.updateMask()
		self.updateImage()

	def updateMask(self):
		if self.Ifull.size == 0:
			return

		max_area = self.ui.spinBox_max_area.value()
		min_area = self.ui.spinBox_min_area.value()
		thresh_block_size = self.ui.spinBox_block_size.value()
		thresh_C = self.ui.spinBox_thresh_C.value()
		
		mask = getROIMask(self.Imin.copy(),  min_area=min_area, max_area=max_area, thresh_block_size=thresh_block_size, thresh_C=thresh_C, has_timestamp=False)
		self.Imask =  mask*self.Ifull
		
	#update image if the GUI is resized event
	def resizeEvent(self, event):
		self.updateImage()

	def startAnalysis(self):
		if self.video_file == '' or self.Ifull.size == 0:
			QMessageBox.critical(self, 'No valid video file selected.', "No valid video file selected.", QMessageBox.Ok)
			return

		self.close()


		mask_param = {'max_area': self.ui.spinBox_max_area.value(),
		'min_area' : self.ui.spinBox_min_area.value(), 
		'thresh_block_size' : self.ui.spinBox_block_size.value(),
		'thresh_C' : self.ui.spinBox_thresh_C.value()}

		json_file = self.video_file.rpartition('.')[0] + '.json'
		with open(json_file, 'w') as fid:
			json.dump(mask_param, fid)

		
		masked_image_file = compressVideoWorker(self.video_file, self.mask_files_dir, param_file = json_file)
		getTrajectoriesWorker(masked_image_file, self.results_dir, param_file = json_file)

		

	def updateResultsDir(self):
		results_dir = QFileDialog.getExistingDirectory(self, "Selects the directory where the analysis results will be stored", 
		self.results_dir)
		if results_dir:
			self.results_dir = results_dir + os.sep
			self.ui.lineEdit_results.setText(self.results_dir)

	def updateMasksDir(self):
		mask_files_dir = QFileDialog.getExistingDirectory(self, "Selects the directory where the hdf5 video will be stored", 
		self.mask_files_dir)
		if mask_files_dir:
			self.mask_files_dir = mask_files_dir + os.sep
			self.ui.lineEdit_mask.setText(self.mask_files_dir)


if __name__ == '__main__':
	app = QApplication(sys.argv)
	
	ui = getMaskParams()
	ui.show()
	app.exec_()
	

	#sys.exit()

