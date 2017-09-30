from __future__ import absolute_import, print_function

try:
    import llspy
except ImportError:
    import os
    import sys
    thisDirectory = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(thisDirectory, os.pardir, os.pardir))
    import llspy

import llspy.gui.exceptions as err
from llspy.gui.qtlogger import LogFileHandler
from llspy.gui.mainwindow import main_GUI, sessionSettings

from PyQt5 import QtWidgets, QtGui

import os
import sys
import multiprocessing
import time
import logging
logger = logging.getLogger()  # set root logger
logger.setLevel(logging.DEBUG)
lhStdout = logger.handlers[0]   # grab console handler so we can delete later
ch = logging.StreamHandler()    # create new console handler
ch.setLevel(logging.ERROR)      # with desired logging level
# ch.addFilter(logging.Filter('llspy'))  # and any filters
logger.addHandler(ch)           # add it to the root logger
logger.removeHandler(lhStdout)  # and delete the original streamhandler


def main():
    if 'test' in sys.argv:
        APP = QtWidgets.QApplication(sys.argv)
        mainGUI = main_GUI()
        time.sleep(.1)
        mainGUI.close()
        sys.exit(0)
    else:
        # freeze multiprocessing support for pyinstaller
        multiprocessing.freeze_support()
        # create the APP instance
        APP = QtWidgets.QApplication(sys.argv)
        appicon = QtGui.QIcon(llspy.util.getAbsoluteResourcePath('gui/logo_dark.png'))
        APP.setWindowIcon(appicon)
        # register icon with windows
        if sys.platform.startswith('win32'):
            import ctypes
            myappid = 'llspy.LLSpy.' + llspy.__version__
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

        firstRun = False if len(sessionSettings.childKeys()) else True

        # set up the logfile
        fh = LogFileHandler(maxBytes=100000, backupCount=2)
        logger.addHandler(fh)
        fh.setLevel(logging.DEBUG)
        logger.debug('>'*10 + '  LLSpy STARTUP  ' + '<'*10)

        # instantiate the main window widget
        mainGUI = main_GUI()
        mainGUI.setWindowIcon(appicon)

        if firstRun:
            box = QtWidgets.QMessageBox()
            box.setWindowTitle('Help improve LLSpy')
            box.setText("Thanks for using LLSpy.\n\nIn order to improve the stability of LLSpy, uncaught "
                "exceptions are automatically sent to sentry.io\n\nNo personal "
                "information is included in this report.  The error-reporting "
                "code can be seen in llspy.gui.exceptions.  If want to disable"
                "automatic error reporting, you may opt out below.\n")
            box.setIcon(QtWidgets.QMessageBox.Information)
            box.addButton(QtWidgets.QMessageBox.Ok)
            box.setDefaultButton(QtWidgets.QMessageBox.Ok)
            pref = QtWidgets.QCheckBox("Opt out of automatic error reporting.")
            box.setCheckBox(pref)

            def setOptOut(value):
                err._OPTOUT = True if value else False
                mainGUI.errorOptOutCheckBox.setChecked(True)

            pref.stateChanged.connect(setOptOut)
            box.exec_()

        # instantiate the execption handler
        exceptionHandler = err.ExceptionHandler()
        sys.excepthook = exceptionHandler.handler
        exceptionHandler.errorMessage.connect(mainGUI.show_error_window)

        # if we crashed last time, send a bug report (if allowed)
        if not firstRun and not sessionSettings.value('cleanExit', type=bool):
            from click import get_app_dir
            logger.error('LLSpy failed to exit cleanly on the previous session')
            if not err._OPTOUT:
                _LOGPATH = os.path.join(get_app_dir('LLSpy'), 'llspygui.log')
                try:
                    with open(_LOGPATH, 'r') as f:
                        crashlog = f.read()
                        err.client.captureMessage('LLSpyGUI Bad Exit\n\n' + crashlog)
                except Exception:
                    pass

        # check to see if the cudaDeconv binary is valid, and alert if not
        try:
            llspy.cudabinwrapper.get_bundled_binary()
            if not llspy.nGPU() > 0:
                QtWidgets.QMessageBox.warning(mainGUI, "No GPUs detected!",
                    "cudaDeconv found no "
                    "CUDA-capable GPUs.\n\n Preview/Processing will likely not work.",
                    QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.NoButton)
        except llspy.CUDAbinException:
            QtWidgets.QMessageBox.warning(mainGUI, "No binary detected!",
                'Unable to detect bundled cudaDeconv binary. We will not be able'
                ' to do much without it.\n\n'
                'The cudaDeconv.exe program is owned by HHMI Janelia Research Campus, '
                'and access to that program can be arranged via a license agreement with them. '
                'Please contact innovation@janelia.hhmi.org.\n\n'
                'More info in the documentation at llspy.readthedocs.io',
                QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.NoButton)

        # ######################## TESTING
        # def tester():
        #     pass

        # mainGUI.shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Shift+E"), mainGUI)
        # mainGUI.shortcut.activated.connect(tester)
        # #############################

        sessionSettings.setValue('cleanExit', False)
        sessionSettings.sync()
        sys.exit(APP.exec_())


if __name__ == '__main__':
    main()
