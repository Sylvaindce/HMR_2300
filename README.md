# Honeywell HMR 2300 Magnetometer

Python3 software 

Python code allowing the communication between a PC and a magnetometer through communication port


Usage:

python3 hmr_2300.py


Specific parameters: 

 - Timed, do acquisition for specific time interval
ex: mag.init_acquisition(5, -1) where 5 the time parameter in minute.


 - Continuous, do continuous acquisition
ex: mag.init_acquisition(0, -1)


 - No-Interaction, do acquisition without asking the com port
ex: mag.init_acquisition(0, 1) where 1 is the first com port available to communicate.


Bonus:

 - Write CSV
 - Send CSV by mail
