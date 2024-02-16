import PySimpleGUI as sg

import serial
import time
import glob
import os
import pathlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy as sp
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from constants import *
from main_window import MainWindow
import pyvisa

rm = pyvisa.ResourceManager()

sg.theme("Dark")


class App:
    def __init__(self):
        self.devices = {"oscope": self.connect_to_oscope(), "ps": self.connect_to_ps()}
        self.create_log_paths()
        self.run_log = self.load_log()
        self.windows = [
            MainWindow(
                self.run_log,
                self.devices,
            )
        ]

    def connect_to_oscope(self):
        if DEBUG:
            return None
        while True:
            try:
                oscope = rm.open_resource("TCPIP0::192.168.4.2::inst0::INSTR")
                return oscope
            except Exception as e:
                print("Failed to connect to SMU")
                time.sleep(1)

    def connect_to_ps(self):
        if DEBUG:
            return None
        while True:
            try:
                ps = rm.open_resource("TCPIP0::192.168.4.3::INSTR")

                return ps
            except Exception as e:
                print("Failed to connect to SMU")
                time.sleep(1)

    def create_path(self, path):
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)

    def create_log_paths(self):
        self.create_path("data/runlogs")

    def load_log(self):
        run_log = None
        if pathlib.Path("data/runlogs/latest.csv").exists():
            run_log = pd.read_csv("data/runlogs/latest.csv")
        else:
            run_log = pd.DataFrame(columns=LOG_COLUMNS)
            run_log.to_csv("data/runlogs/latest.csv", index=False)
        # set flux dtype to float64
        run_log["flux"] = run_log["flux"].astype("float64")
        return run_log

    def create_window(self, window_class, row, *args, **kwargs):
        for window in self.windows:
            if hasattr(window, "get_row") and (window.get_row() == row):
                window.bring_to_front()
                return
        new_window = window_class(row, *args, **kwargs)
        self.windows.append(new_window)

    def close_devices(self):
        if DEBUG:
            return


if __name__ == "__main__":
    app = App()
    while True:

        # window event loop
        for window in app.windows:
            if window.window_event_loop():
                window.close()
                app.windows.remove(window)
                break

        # if no windows, exit
        if len(app.windows) == 0:
            break

    # close devices
    app.close_devices()
