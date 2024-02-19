# Foucault

# Overview
Foucault is a disciplining algorithm for ultra low noise oscillators. It uses two PID controllers to compare the oscillator to a GPS reference signal, and then adjusts the tuning voltage to keep the frequency and phase angle from drifting. 

# Diagram
![Foucault-Diagram-Updated](https://github.com/rtenacity/foucault/assets/50297222/f2f4c226-a27c-4bde-a583-c817f5ca2132)

# Implementation

## Theory

If the oscillator drifts from the reference frequency, the phase angle between them will change as a function of time. A phase detector can detect this phase angle and return it as a voltage. Therefore, a specific phase angle corresponds to a voltage emitted from the phase detector. The algorithm determines the voltage necessary for a 90 degree phase angle and uses two PID controllers to keep the phase angle constant. It does this by returning the output of the controller to the DAC, which changes the tuning voltage. This keeps the frequency and the phase angle constant, therefore removing the drift. 

## Program

1. Determine the base tuning voltage. 
    - The base tuning voltage is the voltage that should approximately keep the phase angle the same. It can be set to an abitrary value or to a specific value (in this case 650 mV) based on some experimentation.
2. Identify the target voltage for a 90 degree phase angle.
    - The target voltage is the average voltage inputted into the phase detector. This corresponds to a phase angle of 90 degrees. The program then gets the average voltage by sampling 20 input voltages from the phase detector via the ADC. 
3. Construct the PID controllers and their constants
    - A PID controller is constructed using the `simple_pid` library, its constants defined in the constructor. The controller's output limits are also defined to prevent integral windup. One PID controller is created to roughly get the oscillator in the desired area, and one controller is created to fine-tune the oscillator.
4. Run the control loop
    - The loop samples five values from the phase detector at 0.1 second intervals and gets the average. This is then used to determine whether to fine-tune or roughly correct the oscillator. This then runs the specified PID controller, which returns a value that is computed to be the correction voltage. This correction voltage is then added to the base voltage of 650 mV to return the tuning voltage. The tuning voltage is then outputted to the DAC, which tunes the oscillator.

## Files

1. `monitor.py`: This program allows the user to monitor the values of the components (The ADC, DAC, and a reciprocal counter if it is wired) in the command line.
2. `foucault.py`: This is the main program where the PID controllers are defined and executed.

# Demo

https://github.com/rtenacity/foucault/assets/50297222/5dd416c3-6daa-4331-b738-9e31de7b2182

