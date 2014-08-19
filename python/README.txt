This directory contains all the necessary files for the python implementation of the popular emokit library.

PREPARATION
The ‘requirements.txt’ file ensures that the OS-independent requirements are installed.  These are gevent and pycrypto.  While those dependencies will be installed automatically, there may be additional dependencies, based on your system.  You need to install ctypes to use the mouse_control module.  For the USB communication, you must install pywinusb for Windows, cython-hidapi for Mac, and pyusb for Linux.

INSTALLATION
After installing the appropriate USB library for your system (and, optionally, ctypes), you may run “python setup.py install” directly.  Alternatively, if make is installed, you may use “make install”.  Either way, the source files in ‘emokit’ will be relocated to python’s site-packages directory, and the remaining dependencies listed in ‘requirements.txt’ will be installed.

USAGE
Using the emokit python library is very easy.  The included example python script renders the sensor data and streams it via a UDP server.