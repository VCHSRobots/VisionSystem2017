# -------------------------------------------------------
# mousereader.py -- program to read mouse locations
#
# 01/27/17 DLB Created
# -------------------------------------------------------
import threading

xloc = 0.0          #  X location in inches
yloc = 0.0          #  Y location in inches
fmsefile = 0        #  file handle for the mouse device
msescale = 1000.0   #  pixels per inch

def sumMovement(x, y):
    global xloc, yloc
    x_ord = ord(x)
    y_ord = ord(y)
    if x_ord >= 128:
        x_ord = x_ord - 256
    if y_ord >= 128:
        y_ord = y_ord - 256
    xloc += float(x_ord) / msescale
    yloc += float(y_ord) / msescale

def readMsePosition():
    global fmsefile, xloc, yloc
    c = fmsefile.read(3)
    n = len(c)
    if n != 3:
        print('Mouse Read Error! Missed Bytes.')
	xloc, yloc = -1, -1
        return xloc, yloc
    sumMovement(c[1], c[2])
    return xloc, yloc

def runmseread():
    while True:
        readMsePosition()

def initMouseTrack():
    global fmsefile, xloc, yloc
    xloc = 0
    yloc = 0
    fmsefile = open("/dev/input/by-path/platform-tegra-xhci-usb-0:3.4.3:1.0-event-mouse", "rb")
    t = threading.Thread(target=runmseread)
    t.start()

def getMousePosition():
    global xloc, yloc
    return xloc, yloc

if __name__ == "__main__":
	initMouseTrack()
	while True:
		x, y = readMsePosition()
		print ("x, y = %d, %d" % (x, y))
