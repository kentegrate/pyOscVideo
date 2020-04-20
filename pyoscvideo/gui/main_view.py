"""
Main View
TODO: add proper description
"""

# *****************************************************************************
#  Copyright (c) 2020. Pascal Staudt, Bruno Gola                              *
#                                                                             *
#  This file is part of pyOscVideo.                                           *
#                                                                             *
#  pyOscVideo is free software: you can redistribute it and/or modify         *
#  it under the terms of the GNU General Public License as published by       *
#  the Free Software Foundation, either version 3 of the License, or          *
#  (at your option) any later version.                                        *
#                                                                             *
#  pyOscVideo is distributed in the hope that it will be useful,              *
#  but WITHOUT ANY WARRANTY; without even the implied warranty of             *
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the              *
#  GNU General Public License for more details.                               *
#                                                                             *
#  You should have received a copy of the GNU General Public License          *
#  along with pyOscVideo.  If not, see <https://www.gnu.org/licenses/>.       *
# *****************************************************************************


import logging
import queue
import time
import numpy as np

from typing import Any, Callable, Dict, List

from PyQt5.QtWidgets import QMainWindow, QMessageBox, QLabel, QSizePolicy, QComboBox, QHBoxLayout, QVBoxLayout
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, Qt, QSize
from PyQt5.QtGui import QPixmap, QImage

from pyoscvideo.controllers.main_ctrl import MainController
from pyoscvideo.video.camera import Camera
from pyoscvideo.video.camera_selector import CameraSelector
from pyoscvideo.gui.main_view_ui import Ui_MainWindow


class CameraView:
    def __init__(self, camera: Camera, widget):
        """
        """
        self._logger = logging.getLogger(__name__+f".CameraView[{camera.name}]")
        
        vlayout = QVBoxLayout()
        label = QLabel(widget)
        label.setEnabled(True)
        sp = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        sp.setHorizontalStretch(0)
        sp.setVerticalStretch(0)
        sp.setHeightForWidth(label.sizePolicy().hasHeightForWidth())
        label.setSizePolicy(sp)
        label.setMinimumSize(QSize(1, 1))
        label.setSizeIncrement(QSize(0, 0))
        label.setLayoutDirection(Qt.LeftToRight)
        label.setScaledContents(False)
        label.setAlignment(Qt.AlignCenter)
        label.setObjectName(f"imageLabel for {camera.name}")
        vlayout.addWidget(label)

        hlayout = QHBoxLayout()
        combo_box = QComboBox(widget)
        combo_box.setObjectName(f"comboBox for {camera.name}")

        frame_rate_label = QLabel(widget)
        sp_fps = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        sp_fps.setHorizontalStretch(0)
        sp_fps.setVerticalStretch(0)
        sp_fps.setHeightForWidth(frame_rate_label.sizePolicy().hasHeightForWidth())
        frame_rate_label.setSizePolicy(sp_fps)
        frame_rate_label.setLayoutDirection(Qt.LeftToRight)
        frame_rate_label.setAlignment(Qt.AlignCenter)
        frame_rate_label.setObjectName("frame_rate_label")
        
        hlayout.addWidget(combo_box)
        hlayout.addWidget(frame_rate_label)
        vlayout.addLayout(hlayout)

        self.layout = vlayout
        self.fps_label = frame_rate_label
        self.combo_box = combo_box
        self.image_label = label
        self.camera = camera

        self._camera_list: List[Camera] = []
        
        for camera in CameraSelector.cameras.values():
            self._add_camera_combo_box(camera)

        self.combo_box.setCurrentIndex(self._camera_list.index(self.camera))

        self._bind_actions()
        self._start_capturing()
    
    def _bind_actions(self):
        
        self.combo_box.currentIndexChanged.connect(
            self._change_current_camera)

        CameraSelector.camera_added.connect(
                self._add_camera_combo_box)
        CameraSelector.camera_removed.connect(
                self._remove_camera_combo_box)

    def _start_capturing(self):
        self.camera.start_capturing()
        self.camera.add_change_pixmap_cb(self._on_new_frame)
        self.camera.add_update_fps_label_cb(self._update_fps_label)

    def _update_fps_label(self, fps: float):
        self.fps_label.setText("Fps: " + str(round(fps, 1)))

    def _add_camera_combo_box(self, camera: Camera):
        self._camera_list.append(camera)
        self._camera_list.sort(key=lambda e: e.name)
        idx = self._camera_list.index(camera)
        self.combo_box.insertItem(idx, camera.name)

    def _remove_camera_combo_box(camera: Camera):
        idx = self._camera_list.index(camera)
        del self._camera_list[idx]
        self.combo_box.removeItem(idx)

    def _change_current_camera(self, index: int):
        self._logger.info(f"Changing current camera to: {index}")
        self.camera.remove_change_pixmap_cb(self._on_new_frame)
        self.camera.remove_update_fps_label_cb(self._update_fps_label)
        
        self.camera = self._camera_list[index]
        self._start_capturing()
 
    def _on_new_frame(self, image: np.array):
        """
        Set the image in the main window.
        """
        self.image_label.setPixmap(QPixmap.fromImage(image).scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.FastTransformation))


class MainView(QMainWindow):
    """
    The main Window
    """
    should_quit = pyqtSignal()

    def __init__(self, main_controller):
        super().__init__()
        self._logger = logging.getLogger(__name__+".MainView")

        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)
       
        self.should_quit.connect(main_controller.cleanup)
       
        self._camera_views = []
        for i, camera in enumerate(main_controller._cameras):
            camera_view = CameraView(camera, self._ui.centralwidget)
            self._camera_views.append(camera_view)
            self._ui.camerasLayout.addLayout(camera_view.layout, int(i/2), i%2, 1, 1)
       
        self._ui.recordButton.clicked.connect(
            main_controller.toggle_recording)

        main_controller._model.status_msg_changed.connect(self._set_status_msg)
        main_controller._model.is_recording_changed.connect(self._update_recording_button)

        self.setStatusBar(self._ui.statusbar)

    @pyqtSlot(bool)
    def _update_recording_button(self, is_recording: bool):
        if self._ui.recordButton.isChecked() != is_recording:
            self._ui.recordButton.toggle()
    
    @pyqtSlot(str)
    def _set_status_msg(self, msg: str):
        self._ui.statusbar.setEnabled(True)
        self._logger.debug("Status changed: %s", msg)
        self._ui.statusbar.showMessage(msg)

    def closeEvent(self, event):
        reply = QMessageBox.question(
                self,
                'Message',
                "Are you sure to quit?", QMessageBox.Yes, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.on_quit()
            event.accept()
        else:
            event.ignore()

    def on_quit(self):
        self.should_quit.emit()
