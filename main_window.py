import PySimpleGUI as sg
from constants import *
from layout import *
import time
import pathlib
import numpy as np
import threading
import glob


class MainWindow:
    def __init__(self, run_log, devices):
        self.run_log = run_log
        self.devices = devices
        self.exp_running = False
        self.values = None
        self.start_time = time.time()
        self.time_passed = 0
        self.transient_folder = "\\\\K-EXR104A-10192\\Waveforms"
        self.transient_folder_count = self.get_transient_count()
        print(self.transient_folder_count)

        self.layout = [
            LAYOUT_PS_CONFIG,
            LAYOUT_RUN_CONFIG,
            LAYOUT_TABLE_MODIFICATIONS,
            LAYOUT_RUN_TABLE_CONFIG,
        ]
        self.current_run = None
        self.main_window = sg.Window("LBNL 2024", self.layout, finalize=True)
        self.update_log(False)

    def get_transient_count(self):
        return len(glob.glob1(self.transient_folder, "*.h5"))

    def set_ps_voltage(self, channel, voltage):
        self.devices["ps"].write(f"INST CH{channel}")
        self.devices["ps"].write(f"VOLT {voltage}")

    def set_ps_channel_on(self, channel):
        self.devices["ps"].write(f"INST CH{channel}")
        self.devices["ps"].write(f"OUTP ON")

    def set_ps_channel_off(self, channel):
        self.devices["ps"].write(f"INST CH{channel}")
        self.devices["ps"].write(f"OUTP OFF")

    def ps_on(self):
        self.exp_running = True
        self.set_ps_voltage(1, self.values["-PS_SLIDER_A-"])
        self.set_ps_voltage(2, 15)
        self.set_ps_voltage(3, 15)
        self.set_ps_channel_on(1)
        self.set_ps_channel_on(2)
        self.set_ps_channel_on(3)

    def ps_off(self):
        self.exp_running = False
        self.set_ps_channel_off(1)
        self.set_ps_channel_off(2)
        self.set_ps_channel_off(3)

    def create_log(self, part, ion, let, angle, board, time, date):
        # get the latest run number from run_log
        run = self.run_log["run"].max() + 1
        if run is None or np.isnan(run):
            run = 0

        # add a new row to run_log
        self.run_log.loc[len(self.run_log)] = [
            run,
            part,
            ion,
            let,
            angle,
            board,
            time,
            date,
            None,
            None,
            None,
            None,
        ]
        self.current_run = run
        self.update_log()

    def save_log(self):
        # save as backup with time
        self.run_log.to_csv(
            f"data/runlogs/{time.strftime('%Y-%m-%d_%H-%M-%S')}.csv", index=False
        )
        self.run_log.to_csv("data/runlogs/latest.csv", index=False)

    def update_log(self, save=True):
        self.main_window["-RUN_LOG-"].update(self.run_log.values.tolist())
        if save:
            self.save_log()

    def test_end(self):
        transient_test = self.get_transient_count()
        self.run_log.loc[self.run_log["run"] == self.current_run, "transients"] = (
            transient_test - self.transient_folder_count
        )
        self.transient_folder_count = transient_test
        self.exp_running = False
        self.main_window["-EXP-"].update("Start")
        self.main_window["-PS_SLIDER_A-"].update(disabled=False)
        self.main_window["-PROGRESS-"].update(
            current_count=0,
        )
        self.run_log.loc[self.run_log["run"] == self.current_run, "end_time"] = (
            time.strftime("%H-%M-%S")
        )
        self.run_log.loc[self.run_log["run"] == self.current_run, "end_date"] = (
            time.strftime("%Y-%m-%d")
        )
        self.update_log()

    def window_event_loop(self):

        event, self.values = self.main_window.read(timeout=1)
        if event == sg.WIN_CLOSED:
            self.ps_off()
            return True
        if event == "-EXP-":
            if self.exp_running:
                self.ps_off()
                self.main_window["-EXP-"].update("Start")
                self.main_window["-PS_SLIDER_A-"].update(disabled=False)
            else:
                self.start_time = time.time()
                self.end_time = self.start_time + self.values["-TIME-"] * 60
                self.create_log(
                    self.values["-PART-"],
                    self.values["-ION-"],
                    self.values["-LET-"],
                    self.values["-ANGLE-"],
                    self.values["-BOARD-"],
                    time.strftime("%H-%M-%S"),
                    time.strftime("%Y-%m-%d"),
                )
                self.ps_on()
                self.main_window["-EXP-"].update("Stop")
                self.main_window["-PS_SLIDER_A-"].update(disabled=True)
        if event == "-SET_FLUX-":
            # make sure values["-FLUX-"] is a valid number
            try:
                float(self.values["-FLUX-"])
            except ValueError:
                # non blocking popup
                sg.popup(
                    "Invalid flux value", title="Error", non_blocking=True, font=FONT
                )
                return False
            if len(self.selected_rows) > 0:
                if len(self.selected_rows) > 1:
                    pass
                else:
                    self.run_log.loc[self.selected_rows[0], "flux"] = self.values[
                        "-FLUX-"
                    ]
                    self.update_log()
        if event == "-RUN_LOG-":
            self.selected_rows = self.values["-RUN_LOG-"]

        if self.exp_running:
            a = self.end_time - time.time()
            b = self.end_time - self.start_time
            c = int((b - a) / b * 100)

            self.main_window["-PROGRESS-"].update(
                current_count=c,
            )
            if c >= 100:
                self.ps_off()
                self.test_end()

        return False

    def close(self):
        pass
