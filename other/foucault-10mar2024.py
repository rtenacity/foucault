import os
import time
import subprocess
from simple_pid import PID

#! A DAC output of about 650mV will keep the PD output ~constant at an ambient tempetature of approximately 22'C
#! This is based on some experimental characterization of the oscillator circa 20 Feb 2024.

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
MON = "/sys/devices/platform/soc/3f804000.i2c/i2c-1/1-0048/hwmon/hwmon1"

ADC_SAMPLEFREQ = 411
# ADC_SAMPLEFREQ = 19200

DAC_VOLTAGE_SCALE = float(read_from_file(f"{DAC}/out_voltage_scale"))
DAC_OUTPUT_RAW = float(read_from_file(f"{DAC}/out_voltage0_raw"))

ADC_VOLTAGESCALE = float(read_from_file(f"{ADC}/in_voltage0-voltage1_scale"))
ADC_RAW = float(read_from_file(f"{ADC}/in_voltage0-voltage1_raw"))

VOLTAGE = 800 * (1/DAC_VOLTAGE_SCALE)
DAC_OUTPUT = str(VOLTAGE)

LIMIT = 100

PHASEDET_SUMVOLT = 0

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
    print(f"sample freq attempted to set to {ADC_SAMPLEFREQ}")
    current_sample_freq = int(read_from_file(f"{ADC}/in_voltage0-voltage1_sampling_frequency"))
    print(f"sample freq changed to {current_sample_freq}")

####
# for testing purposes only... artificially set Vtune away from expected value 
# write_to_file(f"{DAC}/out_voltage0_raw", str(5 * (1/DAC_VOLTAGE_SCALE)))
current = int(read_from_file(f"{DAC}/out_voltage0_raw")) * (1/DAC_VOLTAGE_SCALE)
print(f"Vtune: {current:.3f}")
# time.sleep(1)
#####

# Establishing target value (reference midpoint phase detector value, which should correspond to a phase angle of 90 degrees)
for i in range(1, 20):
    PHASEDET_REFRAW = int(read_from_file(f"{ADC}/in_voltage2-voltage3_raw"))
    PHASEDET_REFVOLT = PHASEDET_REFRAW * ADC_VOLTAGESCALE / 1
    PHASEDET_MIDVOLT = PHASEDET_REFVOLT / 2
    PHASEDET_SUMVOLT += PHASEDET_MIDVOLT
    PHASEDET_AVGVOLT = PHASEDET_SUMVOLT / i

coarse_tune = PID(0.6, 0.1, 0.01, setpoint=PHASEDET_AVGVOLT)
coarse_tune.output_limits = (-4000, 4000)
fine_tune = PID(0.01, 0, 0, setpoint=PHASEDET_AVGVOLT)
# change this on the fly soon
fine_tune.output_limits = (-500, 500)


correction_f = []
finecounter=0
correction_z = 0
j = 0
stable = True

phase_array = []

phase_voltage = int(read_from_file(f"{ADC}/in_voltage0-voltage1_raw")) * ADC_VOLTAGESCALE

# Run the PID control loop
while True:
    # Average phase voltage to avoid noisy signals
    phase_voltages = []
    for i in range (0, 20):
        phase_voltage_pt = int(read_from_file(f"{ADC}/in_voltage0-voltage1_raw")) * ADC_VOLTAGESCALE
        phase_voltages.append(phase_voltage_pt)
    phase_voltage = sum(phase_voltages) / len(phase_voltages)
    phase_array.append(phase_voltage)
    temperature = int(read_from_file(f"{MON}/temp1_input")) / 1000
    
    # Calculate the error to determine whether to use coarse correction or fine correction
    error = PHASEDET_AVGVOLT - phase_voltage
    
    stable = True
    if len(phase_array) > 10:
        last = phase_array[-10:]
        for voltage in last:
            if abs(PHASEDET_AVGVOLT - voltage) > 5:
                stable = False
                break
    else:
        stable = False
    
    
    if abs(error) > LIMIT or not stable:
        correction = VOLTAGE + ((coarse_tune(phase_voltage) / 1000) * VOLTAGE)
        write_to_file(f"{DAC}/out_voltage0_raw", str(correction))
        correction_f.append(correction)
        
        correction_z = correction
        
        # Print phase voltage and correction voltage
        print(f"PID_c: {PHASEDET_AVGVOLT:.3f}, {phase_voltage:.3f}, {correction * DAC_VOLTAGE_SCALE:.3f}, {phase_voltage - PHASEDET_AVGVOLT:.3f}, {stable}")
        time.sleep(0.1)

    else:
        sumof = 0
        for item in correction_f[-5:]:
            sumof += int(item)
        
        sumof = sumof / 5
        correction = correction_z + ((fine_tune(phase_voltage) / 1000) * VOLTAGE)
        write_to_file(f"{DAC}/out_voltage0_raw", str(correction * 1))
        print(f"PID_f: {PHASEDET_AVGVOLT:.3f}, {phase_voltage:.3f}, {correction * DAC_VOLTAGE_SCALE:.3f}, {phase_voltage - PHASEDET_AVGVOLT:.3f}, {temperature:.1f}C")
        
        time.sleep(5)
        
	



        
        
        
    """ time.sleep(0.1 * finecounter)
        if abs(error) < 2 and finecounter < 5:
            if not finecounter > 10:
                finecounter+=1
        if finecounter == 5 and abs(error) < 0.05:
            fine_tune.auto_mode = False
            time.sleep(15)
            fine_tune.set_auto_mode(True, last_output=PHASEDET_AVGVOLT)
	"""
