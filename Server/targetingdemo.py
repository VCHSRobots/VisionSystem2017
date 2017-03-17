import cv2, socket, sys, threading, time, traceback
from subprocess import call
import numpy as np
#import evsslogger

#logger = evsslogger.getLogger()

#Demonstation variable

Demo = True

#Targeting variables

Hue = [90.0, 125.0]
Saturation = [80.0, 255.0]
Luminance = [10.0, 125.0]
MinArea = 150.0
MinPerimeter = 30.0
MinWidth = 0.0
MaxWidth = 500.0
MinHeight = 10.0
MaxHeight = 1000.0
Solidity = [35.07194244604317, 100.0]
MaxVertices = 150.0
MinVertices = 4.0
MinRatio = 1.00
MaxRatio = 4.00
MaxVerticalOffset = 50
MinVerticalOffset = 0
MaxHorizontalOffset = 25
MinHorizontalOffset = 0

PegHue = [90.0, 175.0]
PegSaturation = [90.0, 255.0]
PegLuminance = [20.0, 125.0]
PegMinArea = 550.0
PegMinPerimeter = 0.0
PegMinWidth = 0.0
PegMaxWidth = 1000.0
PegMinHeight = 25.0
PegMaxHeight = 50.0
PegSolidity = [0.0, 100.0]
PegMaxVertices = 40.0
PegMinVertices = 0.0
PegMinRatio = 0.4
PegMaxRatio = 0.7
PegMaxVerticalOffset = 5000
PegMinVerticalOffset = 0
PegMaxHorizontalOffset = 2500
PegMinHorizontalOffset = 0

class TargetingManager(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
#		self.Conn = Conn
#		self.Addr = Addr
		self.Cam = None
		self.TargetIndex = -1
		self.TargetNewIndex = 0
		self.TargetSwitchLock = threading.Lock()

	def setTarget(self, targetindex):
		self.TargetSwitchLock.acquire()
		self.TargetNewIndex = targetindex
		self.TargetSwitchLock.release()

	def killTarget(self):
		if self.Cam is not None:
			try:
				self.Cam.release()
			except:
				print("Unable to release Cam %d" % self.TargetIndex)
		self.Cam = None
		self.TargetIndex = -1

	def setTargetForReal(self, targetindex):
		print("Target %d Selected" % targetindex)
		self.killTarget()
		self.TargetIndex = targetindex
		if self.TargetIndex >= 0:
			try:
				self.Cam = cv2.VideoCapture(0)
			except:
				print("Unable to setup Cam %d for capture" % self.TargetIndex)
				self.Cam = None
			if self.TargetIndex == 0:
				call(["v4l2-ctl", "-c", "exposure_auto=1"])
				call(["v4l2-ctl", "-c", "exposure_absolute=5"])
				call(["v4l2-ctl", "-c", "brightness=30"])

	def run(self):
		print("TargetingThread started!")
		self.TargetIndex = int(sys.argv[1])
		print("User requested target \"" + sys.argv[1] + "\".")
		self.setTargetForReal(int(sys.argv[1]))
		haveErr = False
		FramesGrabbed = 0
		FPS = 0
		BenchmarkTimes = [] #StartGrabTime, StartColorTime, StartEncodeTime, StartSendTime, EndTime
		AverageTimes = [] #Array containing several copies of BenchmarkTime (s)
		while True:
			StartTime = time.time()
			err = ""
			BenchmarkTimes.append(time.time())
			self.TargetSwitchLock.acquire()
			newindex = int(sys.argv[1])
			self.TargetSwitchLock.release()
			if newindex != self.TargetIndex:
				self.setTargetForReal(newindex)
			haveFrame = False
			if self.Cam is not None:
				try:
					ret, Frame = self.Cam.read()
					haveFrame = True
					haveErr = False
				except:
					if not haveErr:
						print("Unable to take image from Cam %d" % self.TargetIndex)
						err = "Cam Error at Jetson"
					haveErr = True
					haveFrame = False
			if not haveFrame:
				Frame = np.zeros((480,640,3), np.uint8)
			try:
				ImHLS = cv2.cvtColor(Frame, cv2.COLOR_BGR2HLS)
				if self.TargetIndex == 0:
					Out = cv2.inRange(ImHLS, (Hue[0], Luminance[0], Saturation[0]), (Hue[1], Luminance[1], Saturation[1]))
					_, OkContours, _ = cv2.findContours(Out, mode=cv2.RETR_LIST, method=cv2.CHAIN_APPROX_SIMPLE)
					BetterContours = []
					for Contour in OkContours:
						x, y, w, h = cv2.boundingRect(Contour)
						if w > MinWidth and w < MaxWidth:
							if h > MinHeight and h < MaxHeight:
								Area = cv2.contourArea(Contour)
								if Area > MinArea:
									if cv2.arcLength(Contour, True) > MinPerimeter:
										Hull = cv2.convexHull(Contour)
										Solid = 100 * Area / cv2.contourArea(Hull)
										if Solid > Solidity[0] and Solid < Solidity[1]:
											if len(Contour) > MinVertices and len(Contour) < MaxVertices:
												Ratio = (float)(w) / h
												if Ratio > MinRatio and Ratio < MaxRatio:
													BetterContours.append(Contour)
					BetterContours = sorted(BetterContours, key=cv2.contourArea, reverse=True)[:2] #Keep 2 largest
					cv2.drawContours(Frame, BetterContours, -1, (0, 200, 0), 2)
					Centers = []
					Height, Width, Channels = Frame.shape
					cv2.line(Frame, (Width / 2, (Height / 2) - 10), (Width / 2, (Height / 2) + 10), (255, 255, 255), 1) #Crosshair Y
					cv2.line(Frame, ((Width / 2) - 10, Height / 2), ((Width / 2) + 10, Height / 2), (255, 255, 255), 1) #Crosshair X
					CenterImage = ((Width / 2, Height / 2))
					if len(BetterContours) == 2:
						for Contour in BetterContours:
							M = cv2.moments(Contour)
							cX = int(M["m10"] / M["m00"])
							cY = int(M["m01"] / M["m00"])
							Centers.append((cX, cY))
						XDistance = abs(Centers[0][0] - Centers[1][0])
						YDistance = abs(Centers[0][1] - Centers[1][1])
						if XDistance < MaxHorizontalOffset and XDistance > MinHorizontalOffset and YDistance < MaxVerticalOffset and YDistance > MinVerticalOffset:
							LinePoints = [(Centers[0][0], 0), (Centers[1][0], Height)]
							cv2.line(Frame, (Centers[0][0], 0), (Centers[1][0], Height), (255, 255, 255), 1) #Line through center of target Y
							cv2.line(Frame, (0, (Centers[0][1] + Centers[1][1]) / 2), (Width, (Centers[0][1] + Centers[1][1]) / 2), (255, 255, 255), 1) #Line through center of target X
							CenterTarget = (((Centers[0][0] + Centers[1][0]) / 2), (Centers[0][1] + Centers[1][1]) / 2)
#							cv2.line(Frame, CenterTarget, (255, 255, 255), 1) #Line connecting center of target and center of image
#							cv2.line(Frame, CenterTarget, ((Width / 2), (Height / 2)), (255, 255, 255), 1) #Line connecting center of target and center of image
							OffsetX = CenterTarget[0] - (Width / 2)
							OffsetY = CenterTarget[1] - (Height / 2)
							Offset = str(OffsetX) + "," + str(OffsetY)
						else:
							Offset = "?,?"
					else:
						Offset = "?,?"
					cv2.putText(Frame, Offset, (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
					if Demo == True:
						cv2.imshow("Processed image output (Boiler):", Frame)
						cv2.waitKey(1)
#					try:
#						self.Conn.sendall(Offset)
#					except:
#						print("Unable to send offset to client.")
#						traceback.print_exc()
				elif self.TargetIndex == 1:
					Out = cv2.inRange(ImHLS, (PegHue[0], PegLuminance[0], PegSaturation[0]), (PegHue[1], PegLuminance[1], PegSaturation[1]))
					_, OkContours, _ = cv2.findContours(Out, mode=cv2.RETR_LIST, method=cv2.CHAIN_APPROX_SIMPLE)
					BetterContours = []
					for Contour in OkContours:
						x, y, w, h = cv2.boundingRect(Contour)
						if w > PegMinWidth and w < PegMaxWidth:
							if h > PegMinHeight and h < PegMaxHeight:
								Area = cv2.contourArea(Contour)
								if Area > PegMinArea:
									if cv2.arcLength(Contour, True) > PegMinPerimeter:
										Hull = cv2.convexHull(Contour)
										Solid = 100 * Area / cv2.contourArea(Hull)
										if Solid > PegSolidity[0] and Solid < PegSolidity[1]:
											if len(Contour) > PegMinVertices and len(Contour) < PegMaxVertices:
												Ratio = (float)(w) / h
												if Ratio > PegMinRatio and Ratio < PegMaxRatio:
													BetterContours.append(Contour)
					BetterContours = sorted(BetterContours, key=cv2.contourArea, reverse=True)[:2] #Keep 2 largest
#					cv2.drawContours(Frame, BetterContours, -1, (0, 200, 0), 2)
					Centers = []
					Height, Width, Channels = Frame.shape
					cv2.line(Frame, (Width / 2, (Height / 2) - 10), (Width / 2, (Height / 2) + 10), (255, 255, 255), 1) #Crosshair Y
					cv2.line(Frame, ((Width / 2) - 10, Height / 2), ((Width / 2) + 10, Height / 2), (255, 255, 255), 1) #Crosshair X
					CenterImage = ((Width / 2, Height / 2))
					if len(BetterContours) == 2:
						for Contour in BetterContours:
							M = cv2.moments(Contour)
							cX = int(M["m10"] / M["m00"])
							cY = int(M["m01"] / M["m00"])
							Centers.append((cX, cY))
						XDistance = abs(Centers[0][0] - Centers[1][0])
						YDistance = abs(Centers[0][1] - Centers[1][1])
						if XDistance < PegMaxHorizontalOffset and XDistance > PegMinHorizontalOffset and YDistance < PegMaxVerticalOffset and YDistance > PegMinVerticalOffset:
							LinePoints = [(Centers[0][0], 0), (Centers[1][0], Height)]
							cv2.line(Frame, (Centers[0][0], 0), (Centers[1][0], Height), (255, 255, 255), 1) #Line through center of target Y
							cv2.line(Frame, (0, (Centers[0][1] + Centers[1][1]) / 2), (Width, (Centers[0][1] + Centers[1][1]) / 2), (255, 255, 255), 1) #Line through center of target X
							CenterTarget = (((Centers[0][0] + Centers[1][0]) / 2), (Centers[0][1] + Centers[1][1]) / 2)
#							cv2.line(Frame, CenterTarget, (255, 255, 255), 1) #Line connecting center of target and center of image
#							cv2.line(Frame, CenterTarget, ((Width / 2), (Height / 2)), (255, 255, 255), 1) #Line connecting center of target and center of image
							OffsetX = CenterTarget[0] - (Width / 2)
							OffsetY = CenterTarget[1] - (Height / 2)
							Offset = str(OffsetX) + "," + str(OffsetY)
						else:
							Offset = "?,?"
					else:
						Offset = "?,?"
					cv2.putText(Frame, Offset, (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
					if Demo == True:
						cv2.imshow("Processed image output (Peg):", Frame)
						cv2.waitKey(1)
#					try:
#						self.Conn.sendall(Offset)
#					except:
#						print("Unable to send offset to client.")
#						traceback.print_exc()
				else:
					print("ERROR! Unknown target number in command input. Valid numbers are \"0\", or \"1\"!")
					sys.exit()
			except Exception as e:
				print("Error autoaiming! " + str(e))
				traceback.print_exc()
Targeter = TargetingManager()
Targeter.daemon = True
Targeter.start()

while True:
	time.sleep(1) #ALL PRAISE SPAGHETTI CODE
