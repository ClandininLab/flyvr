import sys
import time

import numpy as np

from matplotlib.backends.qt_compat import QtCore, QtWidgets

from matplotlib.backends.backend_qt5agg import (FigureCanvas, NavigationToolbar2QT as NavigationToolbar)

from matplotlib.figure import Figure

class PlotWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        layout = QtWidgets.QVBoxLayout(self._main)

        dynamic_canvas = FigureCanvas(Figure(figsize=(5, 3)))
        layout.addWidget(dynamic_canvas)
        self.addToolBar(QtCore.Qt.BottomToolBarArea,NavigationToolbar(dynamic_canvas, self))

        self._dynamic_ax = dynamic_canvas.figure.subplots()
        self._timer = dynamic_canvas.new_timer(10, [(self._update_canvas, (), {})])
        self._timer.start()
        self.show()

    def _update_canvas(self):
        self._dynamic_ax.clear()
        t = np.linspace(0, 10, 101)
        self._dynamic_ax.plot(t, np.sin(t + time.time()))
        self._dynamic_ax.figure.canvas.draw()

class ImgWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        layout = QtWidgets.QVBoxLayout(self._main)

        dynamic_canvas = FigureCanvas(Figure(figsize=(5, 3)))
        layout.addWidget(dynamic_canvas)
        self.addToolBar(QtCore.Qt.BottomToolBarArea,NavigationToolbar(dynamic_canvas, self))

        self._dynamic_ax = dynamic_canvas.figure.imshow()
        self._timer = dynamic_canvas.new_timer(10, [(self._update_canvas, (), {})])
        self._timer.start()
        self.show()

    def _update_canvas(self):
        self.plot_data = np.zeros((128, 128))
        #self._dynamic_ax.clear()
        #t = np.linspace(0, 10, 101)
        #self._dynamic_ax.plot(t, np.sin(t + time.time()))
        self._dynamic_ax.plot(self.plot_data)
        self._dynamic_ax.figure.canvas.draw()