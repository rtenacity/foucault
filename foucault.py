import adi
import time
from simple_pid import PID
import os
import subprocess

# Initialize ADC and DAC through the module
DAC = adi.ad579x(uri="ip:analog.local", device_name='ad5791')
ADC = adi.ad7124(uri = 'ip:analog.local')

# Define sampling rate and voltage scales
ADC.sample_rate = 411
dac_scale = DAC.channel[0].scale
adc_scale = ADC.channel[0].scale

# Function to clear noise from the ADC based on regression tests
def clear_noise(ADC) -> float:
    return float(ADC + (ADC * 0.0001539431268630207) + (-0.014096716462759368))

# Write a value (in mV) to the DAC
def write_to_dac(val) -> None:
    DAC.channel[0].raw = val / dac_scale

# Read the DAC (in mV)
def read_dac() -> float:
    return float(DAC.channel[0].raw * dac_scale)

# Read the ADC (in mV), with an option to read a different channel if needed
def read_adc(chn = 0) -> float:
    return clear_noise(float(ADC.channel[chn].raw * adc_scale))

# Calculate the target value
PHASEDET_SUMVOLT = 0
for i in range(1, 20):
    PHASEDET_REFVOLT = int(read_adc(1))
    PHASEDET_MIDVOLT = PHASEDET_REFVOLT / 2
    PHASEDET_SUMVOLT += PHASEDET_MIDVOLT
    PHASEDET_AVGVOLT = PHASEDET_SUMVOLT / i
    
print(PHASEDET_AVGVOLT)

# Define PID controllers for course and fine tuning
coarse_tune = PID(0.9, 0.1, 0.2, setpoint=PHASEDET_AVGVOLT)
coarse_tune.output_limits = (-4000, 4000)
fine_tune = PID(0.5, 0.1, 0.2, setpoint=PHASEDET_AVGVOLT)
# change this on the fly soon
fine_tune.output_limits = (-500, 500)

print(time.strftime("%Y-%m-%d %H:%M:%S"))

# Define computational variables
stable = True
limit = 100
voltage = 800
correction_course = voltage
phase_array = []
phase_voltage = read_adc()

while True:
    # Average phase voltage to avoid noisy signals
    phase_voltages = []
    for i in range (0, 10):
        phase_voltage_pt = read_adc()
        phase_voltages.append(phase_voltage_pt)
    phase_voltage = sum(phase_voltages) / len(phase_voltages)
    phase_array.append(phase_voltage)
    
    # Calculate the error to determine whether to use coarse correction or fine correction
    error = PHASEDET_AVGVOLT - phase_voltage
    
    stable = True
    if len(phase_array) > 10:
        last = phase_array[-5:]
        for volt in last:
            if abs(PHASEDET_AVGVOLT - phase_voltage) > 5:
                stable = False
                break
    else:
        stable = False
    
    # If the signal isn't stable our outside the limit implement course correction
    if abs(error) > limit or not stable:
        correction_course = voltage + ((coarse_tune(phase_voltage) / 1000) * voltage)
        write_to_dac(correction_course)
        print(f"PID_c: {PHASEDET_AVGVOLT:.3f}, {phase_voltage:.3f}, {correction_course:.3f}, {phase_voltage - PHASEDET_AVGVOLT:.3f}, {stable}")
        time.sleep(0.1)

    # If the signal is stable implement fine correction
    else:
        correction_fine = correction_course + ((fine_tune(phase_voltage) / 1000) * voltage)
        write_to_dac(correction_fine)
        print(f"PID_f: {PHASEDET_AVGVOLT:.3f}, {phase_voltage:.3f}, {correction_fine:.3f}, {phase_voltage - PHASEDET_AVGVOLT:.3f}, C")
        time.sleep(0.5)
        time.sleep(0.5)
