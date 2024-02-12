import os
import time
import subprocess
import serial
import csv

#! A DAC output of about 650mV will almost keep the PD output constant at the current room temp. - Mr. Sandoz

def execute_shell_command(cmd):
    process = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, universal_newlines=True)
    return process.stdout.strip()

def write_to_file(file_path, data):
    with open(file_path, 'w') as file:
        file.write(data)

def read_from_file(file_path):
    with open(file_path, 'r') as file:
        return file.read().strip()

print(time.strftime("%Y-%m-%d %H:%M:%S"))

onevolt = 209658
DAC_OUTPUT = str(onevolt)

AD5791 = "/sys/bus/iio/devices/iio:device0"
AD7124 = "/sys/bus/iio/devices/iio:device1"

AD7124_SAMPLEFREQ = 711

DAC_VOLTAGE_SCALE = float(read_from_file(f"{AD5791}/out_voltage_scale"))
DAC_OUTPUT_RAW = float(read_from_file(f"{AD5791}/out_voltage0_raw"))

AD7124_VOLTAGESCALE = float(read_from_file(f"{AD7124}/in_voltage0-voltage1_scale"))
AD7124_RAW = float(read_from_file(f"{AD7124}/in_voltage0-voltage1_raw"))

PHASEDET_SUMVOLT = 0
PHASEDET_MINRAW = 99999999
PHASEDET_MAXRAW = 0

file_path = 'phasedet_avg.csv'

COUNTER = '/dev/ttyUSB0'
baud = 9600
timeout = 1 

adc_array = []

if not (os.path.isdir(AD5791) and os.path.isfile(f"{AD5791}/out_voltage0_raw")):
    print("ad5791 device tree not instantiated.")
    exit(1)

if not (os.path.isdir(AD7124) and os.path.isfile(f"{AD7124}/in_voltage0-voltage1_raw")):
    print("ad7124 device tree not instantiated.")
    exit(2)

write_to_file(f"{AD5791}/out_voltage0_raw", DAC_OUTPUT)

if read_from_file(f"{AD5791}/out_voltage_powerdown") != "0":
    write_to_file(f"{AD5791}/out_voltage_powerdown", "0")
    time.sleep(1)
    

current_sample_freq = int(read_from_file(f"{AD7124}/in_voltage0-voltage1_sampling_frequency"))
if current_sample_freq != AD7124_SAMPLEFREQ:
    print(f"sample freq changed from {current_sample_freq}")
    write_to_file(f"{AD7124}/in_voltage0-voltage1_sampling_frequency", str(AD7124_SAMPLEFREQ))
    print(f"sample freq changed to {AD7124_SAMPLEFREQ}")
    
print(f"DAC: {DAC_VOLTAGE_SCALE * DAC_OUTPUT_RAW / 1:.6f}")
print(f"ADC: {AD7124_VOLTAGESCALE * AD7124_RAW / 1:.6f}")

write_to_file(f"{AD7124}/in_voltage2-voltage3_sampling_frequency", "100")

for i in range(1, 33):
    PHASEDET_REFRAW = int(read_from_file(f"{AD7124}/in_voltage2-voltage3_raw"))
    PHASEDET_MINRAW = min(PHASEDET_MINRAW, PHASEDET_REFRAW)
    PHASEDET_MAXRAW = max(PHASEDET_MAXRAW, PHASEDET_REFRAW)
    PHASEDET_REFVOLT = PHASEDET_REFRAW * AD7124_VOLTAGESCALE / 1
    PHASEDET_MIDVOLT = PHASEDET_REFVOLT / 2
    PHASEDET_SUMVOLT += PHASEDET_MIDVOLT
    PHASEDET_AVGVOLT = PHASEDET_SUMVOLT / i
    
print(f"REF: {PHASEDET_AVGVOLT * 2:.6f}")
print(f"MIN: {PHASEDET_MINRAW * AD7124_VOLTAGESCALE / 2:.6f}")
print(f"AVG: {PHASEDET_AVGVOLT:.6f}")
print(f"MAX: {PHASEDET_MAXRAW * AD7124_VOLTAGESCALE / 2:.6f}")

with serial.Serial(COUNTER, baud, timeout=timeout) as ser:
    data = ser.readline()
    data_formatted = data.decode().strip()
    if data_formatted is None:
        data = ser.readline()
        data_formatted = data.decode().strip()
    
    print(f"COUNTER: {data_formatted}")

print()

basetime = time.time_ns()
for i in range(1024):
    adc_array.append(int(read_from_file(f"{AD7124}/in_voltage0-voltage1_raw")))
adc_time = (time.time_ns() - basetime) / 1e9
print(f"adc time: {adc_time:.3f} seconds")

print()

for i in range(10):
    adc_raw = adc_array[i]
    adc_voltage = adc_raw * AD7124_VOLTAGESCALE / 1
    print(f"{i} : {adc_raw} : {adc_voltage:.3f} : {180 - (adc_voltage * 100 / 1000):.2f}")
    
with open(file_path, 'a', newline='') as file:
    line = []
    line.append(PHASEDET_AVGVOLT)
    writer = csv.writer(file)
    writer.writerow(line)

print("---------------------------------")

print()

time.sleep(1)
