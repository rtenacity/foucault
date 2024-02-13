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

with open('phasevolt.csv', 'w') as file:
    file.write('')

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

# For a cooler visual (optional step)
write_to_file(f"{DAC}/out_voltage0_raw", str(500 * (1/DAC_VOLTAGE_SCALE)))
time.sleep(2)

# Establishing target value (average phase detector value, which should correspond to a phase angle of 90 degrees)
df = (pd.read_csv('phasedet_avg.csv', usecols = [0], header = None))
target = df[0].astype(float).mean()

pid = PID(0.6, 0.15, 0.03, setpoint=target)
pid.output_limits = (-2000, 2000)

phase_voltage = int(read_from_file(f"{ADC}/in_voltage0-voltage1_raw")) * ADC_VOLTAGESCALE

# Run the P controller
while True:
    phase_voltages = []
    for i in range (0, 5):
        phase_voltage_pt = int(read_from_file(f"{ADC}/in_voltage0-voltage1_raw")) * ADC_VOLTAGESCALE
        phase_voltages.append(phase_voltage_pt)
        time.sleep(0.1)
    phase_voltage = sum(phase_voltages) / len(phase_voltages)
    correction = VOLTAGE + ((pid(phase_voltage) / 500) * VOLTAGE)
    write_to_file(f"{DAC}/out_voltage0_raw", str(correction))
    with open('phasevolt.csv', 'a', newline='') as file:
        line = []
        line.append(phase_voltage)
        writer = csv.writer(file)
        writer.writerow(line)
    print(f"{phase_voltage}, {correction * DAC_VOLTAGE_SCALE}")