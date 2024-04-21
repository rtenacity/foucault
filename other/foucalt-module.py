import adi
import time
from simple_pid import PID

DAC = adi.ad579x(uri="ip:analog.local", device_name='ad5791')
ADC = adi.ad7124(uri = 'ip:analog.local')
ADC.sample_rate = 711
dac_scale = DAC.channel[0].scale
adc_scale = ADC.channel[0].scale

def write_to_dac(val) -> None:
    DAC.channel[0].raw = val / dac_scale
    
def read_dac() -> float:
    return float(DAC.channel[0].raw * dac_scale)

def read_adc(chn=0) -> float:
    return float(ADC.channel[chn].raw * adc_scale)

def clear_noise(ADC) -> float:
    return float(ADC + (ADC * 0.0001539431268630207) + (-0.014096716462759368))

def read_from_file(file_path):
    with open(file_path, 'r') as file:
        return file.read().strip()

PHASEDET_SUMVOLT = 0
    
for i in range(1, 20):
    PHASEDET_REFVOLT = int(read_adc(1))
    PHASEDET_MIDVOLT = PHASEDET_REFVOLT / 2
    PHASEDET_SUMVOLT += PHASEDET_MIDVOLT
    PHASEDET_AVGVOLT = PHASEDET_SUMVOLT / i
    
print(PHASEDET_AVGVOLT)

coarse_tune = PID(0.6, 0.1, 0.01, setpoint=PHASEDET_AVGVOLT)
coarse_tune.output_limits = (-4000, 4000)
fine_tune = PID(0.6, 0.1, 0.05, setpoint=PHASEDET_AVGVOLT)
fine_tune.output_limits = (-500, 500)

print(time.strftime("%Y-%m-%d %H:%M:%S"))

correction_course = 0
stable = True
LIMIT = 100
VOLTAGE = 800

phase_array = []
phase_voltage = read_adc()


while True:
    # Average phase voltage to avoid noisy signals
    phase_voltages = []
    for i in range (0, 20):
        phase_voltage_pt = read_adc()
        phase_voltages.append(phase_voltage_pt)
    phase_voltage = sum(phase_voltages) / len(phase_voltages)
    phase_array.append(phase_voltage)
    
    # Calculate the error to determine whether to use coarse correction or fine correction
    error = PHASEDET_AVGVOLT - phase_voltage
    
    stable = True
    if len(phase_array) > 10:
        last = phase_array[-5:]
        for voltage in last:
            if abs(PHASEDET_AVGVOLT - voltage) > 5:
                stable = False
                break
    else:
        stable = False
    
    
    if abs(error) > LIMIT or not stable:
        correction_course = VOLTAGE + ((coarse_tune(phase_voltage) / 1000) * VOLTAGE)
        write_to_dac(correction_course)
        # Print phase voltage and correction voltage
        print(f"PID_c: {PHASEDET_AVGVOLT:.3f}, {phase_voltage:.3f}, {correction_course}, {phase_voltage - PHASEDET_AVGVOLT:.3f}, {stable}")
        time.sleep(0.1)

    else:
        
        correction_fine = correction_course + ((fine_tune(phase_voltage) / 1000) * VOLTAGE)
        write_to_dac(correction_fine)
        print(f"PID_f: {PHASEDET_AVGVOLT:.3f}, {phase_voltage:.3f}, {correction_fine:.3f}, {phase_voltage - PHASEDET_AVGVOLT:.3f}, C")
        
        time.sleep(1)

