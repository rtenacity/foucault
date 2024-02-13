import shutup
shutup.please() # Temporary until i get pandas to stop being annoying

import os
import time
import subprocess
import serial
import csv
import numpy as np
import pandas as pd
from simple_pid import PID
from time import sleep

#! A DAC output of about 650mV will almost keep the PD output constant at the current room temp.

# Helper functions to make the program easier to work with
def execute_shell_command(cmd):
    process = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, universal_newlines=True)
    return process.stdout.strip()

# write_to_file(f"{AD7124}/in_voltage2-voltage3_sampling_frequency", "100")
def write_to_file(file_path, data):
    with open(file_path, 'w') as file:
        file.write(data)

def read_from_file(file_path):
    with open(file_path, 'r') as file:
        return file.read().strip()

# Identify components that are interacting with the system
DAC = "/sys/bus/iio/devices/iio:device0"
ADC = "/sys/bus/iio/devices/iio:device1"

ADC_SAMPLEFREQ = 711

DAC_VOLTAGE_SCALE = float(read_from_file(f"{DAC}/out_voltage_scale"))
DAC_OUTPUT_RAW = float(read_from_file(f"{DAC}/out_voltage0_raw"))

ADC_VOLTAGESCALE = float(read_from_file(f"{ADC}/in_voltage0-voltage1_scale"))
ADC_RAW = float(read_from_file(f"{ADC}/in_voltage0-voltage1_raw"))

VOLTAGE = 650 * (1/DAC_VOLTAGE_SCALE)
DAC_OUTPUT = str(VOLTAGE)


# Intializing DAC and ADC
if not (os.path.isdir(DAC) and os.path.isfile(f"{DAC}/out_voltage0_raw")):
    print("ad5791 device tree not instantiated.")
    exit(1)

if not (os.path.isdir(ADC) and os.path.isfile(f"{ADC}/in_voltage0-voltage1_raw")):
    print("ad7124 device tree not instantiated.")
    exit(2)

if read_from_file(f"{DAC}/out_voltage_powerdown") != "0":
    write_to_file(f"{DAC}/out_voltage_powerdown", "0")
    time.sleep(1)

current_sample_freq = int(read_from_file(f"{ADC}/in_voltage0-voltage1_sampling_frequency"))
if current_sample_freq != ADC_SAMPLEFREQ:
    print(f"sample freq changed from {current_sample_freq}")
    write_to_file(f"{ADC}/in_voltage0-voltage1_sampling_frequency", str(ADC_SAMPLEFREQ))
    print(f"sample freq changed to {ADC_SAMPLEFREQ}")

# Establishing target value (average phase detector value, which should correspond to a phase angle of 90 degrees)
df = (pd.read_csv('phasedet_avg.csv', usecols = [0], header = None))
target = df[0].astype(float).mean()

pid = PID(1, 0.1, 0, setpoint=target)

pid.sample_time = 1

phase_voltage = int(read_from_file(f"{ADC}/in_voltage0-voltage1_raw")) * ADC_VOLTAGESCALE
error = phase_voltage - target

while True:
    correction = pid(phase_voltage)
    print(correction)
    write_to_file(f"{DAC}/out_voltage0_raw", str(correction * VOLTAGE))
    phase_voltage = int(read_from_file(f"{ADC}/in_voltage0-voltage1_raw")) * ADC_VOLTAGESCALE
    print(phase_voltage)
    sleep(0.5)