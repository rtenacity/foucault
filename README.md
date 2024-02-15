# Foucault

# Overview
Foucault is a disciplining algorithm for ultra low noise oscillators. It uses a PID controller to compare the oscillator to a GPS reference signal, and then adjusts the tuning voltage to keep the frequency and phase angle from drifting. 

# Diagram

# Implementation

## Theory

If the oscillator drifts from the reference frequency, the phase angle between them will change as a function of time. A phase detector can detect this phase angle and return it as a voltage. Therefore, a specific phase angle corresponds to a voltage emitted from the phase detector. The algorithm determines the voltage necessary for a 90 degree phase angle and uses a PID controller to keep the phase angle constant. It does this by returning the output the controller to the DAC, which changes the tuning voltage. This keeps the frequency and the phase angle constant, therefore removing the drift. 

## Program

1. Determine the base tuning voltage. 
    - The base tuning voltage is the voltage that should approximately keep the phase angle the same. It can be set to an abitrary value or to a specific value (in this case 650 mV) based on some experimentation.
2. Identify the target voltage for a 90 degree phase angle.
    - The target voltage is the average voltage inputted into the phase detector. This corresponds to a phase angle of 90 degrees. The program then gets the average voltage by sampling 20 input voltages from the phase detector via the ADC. 
3. Construct the PID controller and its constants
    - A PID controller is constructed using the `simple_pid` library, its constants defined in the constructor. The controller's output limits are also defined to prevent integral windup.
4. Run the control loop
    - The loop samples five values from the phase detector at 0.1 second intervals and gets the average. This is then fed into the PID controller, which returns a value that is computed to be the correction voltage. This correction voltage is then added to the base voltage of 650 mV to return the tuning voltage. The tuning voltage is then outputted to the DAC, which tunes the oscillator.

## Files

1. `monitor.py`: This program allows the user to monitor the values of the components (The ADC, DAC, and a reciprocal counter if it is wired) in the command line.
2. `foucault.py`: This is the main program where the PID controller is defined and executed.

# Demo