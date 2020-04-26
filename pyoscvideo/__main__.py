

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

import sys
import signal

from PyQt5.QtWidgets import QApplication

# Initialize logging module
from pyoscvideo.helpers import load_settings
from pyoscvideo.video.manager import VideoManager
from pyoscvideo.gui.main_view import MainView
from pyoscvideo.osc.interface import OSCInterface


class App(QApplication):
    """The application class for initializing the app."""

    def __init__(self, sys_argv):
        """
        Init the QApplication.
        """
        super(App, self).__init__(sys_argv)

        # TODO: this should be a command line option also
        settings = load_settings("settings/pyoscvideo.yml")

        self.video_manager = VideoManager(settings.get('camera', {}))

        self.osc_interface = OSCInterface(
                self.video_manager, **settings['osc'])
        self.osc_interface.start()

        if settings.get('gui', False):
            self.main_view = MainView(self.video_manager, **settings['gui'])
            self.main_view.show()
        else:
            # so ctrl+c stops the OSC thread
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            self.osc_interface.wait()


def main():
    """Start the application."""
    app = App(sys.argv)
    app.exit(app.exec_())


if __name__ == '__main__':
    main()
