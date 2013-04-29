from com.sun.star.awt import Rectangle
from com.sun.star.awt import WindowDescriptor

from com.sun.star.awt.WindowClass import MODALTOP
from com.sun.star.awt.VclWindowPeerAttribute import OK, OK_CANCEL, YES_NO, YES_NO_CANCEL, RETRY_CANCEL, DEF_OK, DEF_CANCEL, DEF_RETRY, DEF_YES, DEF_NO

import uno
import unohelper
from com.sun.star.awt import XActionListener
from com.sun.star.table.CellHoriJustify import CENTER
from com.sun.star.awt.FontWeight import BOLD

import xml.etree.ElementTree as etree
from math import cos,pi,sqrt,sin,atan2
import urllib.request as request
from tempfile import NamedTemporaryFile
import json

########################### Internal stuff #############################
class Point:
	def __init__(self,name,lat,lon,desc=None):
		self.name=name
		self.lon=lon
		self.lat=lat
		self.desc=desc
		
	def __str__(self):
		return str(self.lon) + "," + str(self.lat)
		
	def getLat(self):
		return self.lat
	
	def getLon(self):
		return self.lon
	
	def getName(self):
		return self.name
	
	def getDescription(self):
		return self.desc
	
	def distance(self,pt):
		"""
		Calculate distance in meters between two points
		"""
		r = 6378137
		toRad = lambda x : pi * x / 180.0
		dLat = toRad(self.lat - pt.lat)
		dLon = toRad(self.lon - pt.lon)
		lat1 = toRad(self.lat)
		lat2 = toRad(pt.lat)
		a = sin(dLat*0.5) * sin(dLat*0.5) + sin(dLon*0.5)*sin(dLon*0.5) * cos(self.lat) * lat1 * lat2
		c = 2.0 * atan2(sqrt(a),sqrt(1.0 - a))
		return r*c

class Cluster:
	def __init__(self):
		self.points = []
		self.bb = None
		
	def tryAdd(self,pt):
		if len(self.points) == 0:
			self.points.append(pt)
			return True
		for point in self.points:
			if point.distance(pt) > 10000.:
				return False
		self.points.append(pt)
		return True
	
	def calculateBB(self):
		lats = []
		lons = []
		for pt in self.points:
			lats.append(pt.getLat())
			lons.append(pt.getLon())
		lats.sort()
		lons.sort()
		
		npts = len(lats)
		dLat = 1000. / 111111.
		dLon1 = 1000.  * cos(lats[0]) / 111111. # Western
		dLon2 = 1000.  * cos(lats[npts-1]) / 111111. # Eastern
		
		sw = Point("SW", lats[0] - dLat, lons[0] - dLon1)
		ne = Point("NE", lats[npts-1] + dLat, lons[npts-1] + dLon2)
		
		self.bb = (sw,ne)
	
	def getBB(self):
		if self.bb == None:
			self.calculateBB()
		return self.bb
	
	def pickFirstPoint(self):
		for pt in self.points:
			if pt.getName()=="Home":
				return pt
		return self.points[0]
	
	def dedup(self):
		pts = []
		
		for pt in self.points:
			try:
				for pt2 in pts:
					if pt.distance(pt2) < 10.0: # Drop all points with distance < 10 m
						raise ValueError
				pts.append(pt)
			except ValueError:
				pass
		
		return pts
	
	def sort(self):
		pt = self.pickFirstPoint()
		path = [pt]
		points = self.dedup() #self.points.copy()
		points.remove(pt)
		
		while len(points) != 0:
			distances = [pt.distance(point) for point in points]
			min_dist = min(distances)
			idx = distances.index(min_dist)
			pt = points.pop(idx)
			path.append(pt)
		return path
	
	def dijkstra(self,start = None):
		if start == None:
			start = self.pickFirstPoint()
		Q = self.points.copy()
		
		Inf = 1000000.0
		dist = [Inf]*len(Q) # Initialize distances with 1000 km == Inf
		previous = [None] * len(Q)
		
		idx = Q.index(start)
		dist[idx] = 0.0 # Distance from source to source is 0
		
		while len(Q) > 0:
			idx = dist.index(min(dist))
			u = Q.pop(idx)
			
			if dist[idx] == Inf:
				break 
			
			for v in Q:
				alt = dist[idx] + u.distance(v)
				idxv = self.points.index(v) # We need to maintain correct index numbers
				d
				if alt < dist[idxv]:
					dist[idxv] = alt
					previous[idxv] = u
		
		path = []
		
		try:
			pt = start
			path.append(self.points.index(pt))
			while True:
				idx = previous.index(pt)
				path.append(idx)
				pt = self.points[idx]
		except ValueError:
			pass
		
		print(path)
		
		
	
	def getSize(self):
		return len(self.points)
		
	
def buildClusters(points):
	clusters = []
	pts = points.copy()
	while len(pts) != 0:
		cluster = Cluster()
		newpts = []
		for i in range(0,len(pts)):
			pt = pts.pop(0)
			if not cluster.tryAdd(pt):
				newpts.append(pt)
		cluster.calculateBB()
		clusters.append(cluster)
		pts = newpts
	return clusters

def loadKML(path):
	fin = open(path,"r")
	tree = etree.parse(fin)
	root = tree.getroot()

	pts = []
	
	for element in root.findall("{http://earth.google.com/kml/2.2}Document/{http://earth.google.com/kml/2.2}Placemark"):
		name = element.findtext("{http://earth.google.com/kml/2.2}name")
		desc = element.findtext("{http://earth.google.com/kml/2.2}description")
		coordinates = element.findtext("{http://earth.google.com/kml/2.2}Point/{http://earth.google.com/kml/2.2}coordinates")
		coords_s = coordinates.split(",")
		coords = (float(coords_s[0]),float(coords_s[1]))
		pt = Point(name, coords[0], coords[1], desc)
		pts.append(pt)
	return pts

def buildURL(path):
	points = path.copy()
	urls=[]
	origin = points.pop(0)
	url = "http://maps.googleapis.com/maps/api/directions/json?sensor=false&mode=walking&origin=" + str(origin) + "&waypoints=optimize:true"
	
	idx = 0
	while len(points) != 0 and idx != 8:
		pt = points.pop(0)
		idx = idx + 1
		url = url + "|" + str(pt)
	
	if len(points) > 0:
		pt = points[0]
		url = url + "&destination=" + str(pt)
		urls = urls + buildURL(points)
	
	urls.append(url)
	
	return urls

def getDirections(path):
	urls = buildURL(path)
	routes = []
	for url in urls:
		handle = request.urlopen(url)
		lines = handle.readlines()
		handle.close()
		content = "".join([line.decode("utf-8","strict") for line in lines])
		fout = open("file.json","w")
		fout.writelines([line.decode("utf-8","strict") for line in lines])
		fout.close()
		routes.append(json.loads(content))
	print("Routes found: %i" % len(routes))

def findHome(path):
	for point in path:
		if point.getName() == "Home":
			return point
	return None

def downloadMap(cluster, startIDX = 1, routes=None, progressCallback = None):

	points = cluster.sort()

	url = "http://open.mapquestapi.com/staticmap/v4/getmap?key=Fmjtd|luub2q0t2q%2Crn%3Do5-9u7s0u&size=2048,2048&type=map&imagetype=png"
	
	homept = findHome(points)
	home = ""
	if homept != None:
		points.remove(homept)
		home = ""

	se,nw = cluster.getBB()
	bestfit = "&bestfit=%7.5f,%7.5f,%7.5f,%7.5f" % (se.getLon(),se.getLat(),nw.getLon(),nw.getLat())

	idx=startIDX
	pois="&pois="
	for pt in points:
		pois = pois + "bluegreen_1-" + str(idx) + "," + str(pt) + "|"
		idx=idx+1
		
	pois = pois[:len(pois)-1]
	
	handle = request.urlopen(url + bestfit + pois + home)
	fout = NamedTemporaryFile(prefix="map-",suffix=".png",delete=False)
	mapfile = fout.name
	
	#meta = handle.info()
	fileSize = handle.length #int(meta.getheaders("Content-Length")[0])
	
	file_size_dl = 0
	block_sz = 8192
	while True:
		inbuffer = handle.read(block_sz)
		if not inbuffer:
			break

		file_size_dl += len(inbuffer)
		fout.write(inbuffer)
		
		if progressCallback != None:
			progressCallback(file_size_dl / fileSize)
	
	#content = handle.read(-1)
	#fout.write(content)
	fout.close()
	handle.close()
	
	return len(points),mapfile

def createSheet(name):
	oDoc = XSCRIPTCONTEXT.getDocument()
	sheet = oDoc.Sheets.insertNewByName(name,oDoc.Sheets.getCount())
	sheet = oDoc.Sheets.getByName(name)
	
	obj = sheet.getColumns().getByName("A")
	obj.Width = 270
	
	obj = sheet.getColumns().getByName("B")
	obj.Width = 540
	
	obj = sheet.getColumns().getByName("C")
	obj.Width = 5550
	
	obj = sheet.getColumns().getByName("D")
	obj.Width = 2560
	
	obj = sheet.getColumns().getByName("E")
	obj.Width = 6840
	
	obj = sheet.getColumns().getByName("F")
	obj.Width = 6840
	
	obj = sheet.getRows().getByIndex(0)
	obj.Height = 210
	
	obj = sheet.getRows().getByIndex(1)
	obj.Height = 1400
	
	obj = sheet.getCellRangeByName("B2:F2")
	obj.merge(True)
	
	obj = sheet.getCellByPosition(1,1)
	obj.String = name
	obj.HoriJustify = CENTER
	obj.CharFontName = "Tahoma"
	obj.CharHeight = 33
	
	obj = sheet.getCellByPosition(1,2)
	obj.String = "#"
	obj = sheet.getCellByPosition(2,2)
	obj.String = "Name"
	obj = sheet.getCellByPosition(3,2)
	obj.String = "Picture"
	obj = sheet.getCellByPosition(4,2)
	obj.String = "Description"
	obj = sheet.getCellByPosition(5,2)
	obj.String = "Comment"
	
	obj = sheet.getCellRangeByName("B3:F3")
	
	RGB = lambda r,g,b: r*256*256 + g*256 + b
	
	obj.CellBackColor = RGB(128,128,128)
	obj.CharWeight = BOLD
	
	return sheet

########################################################################

def TestMessageBox():
	doc = XSCRIPTCONTEXT.getDocument()
	parentwin = doc.CurrentController.Frame.ContainerWindow
	
	s = "This is a test"
	t = "Test"
	res = MessageBox(parentwin, s, t, "querybox", YES_NO_CANCEL + DEF_NO)
	
	s = res
	MessageBox(parentwin, s, t, "infobox")



# Show a message box with the UNO based toolkit
def MessageBox(ParentWin, MsgText, MsgTitle, MsgType="messbox", MsgButtons=OK):
	
	MsgType = MsgType.lower()
	
	#available msg types
	MsgTypes = ("messbox", "infobox", "errorbox", "warningbox", "querybox")
	
	if not ( MsgType in MsgTypes ):
		MsgType = "messbox"
	
	#describe window properties.
	aDescriptor = WindowDescriptor()
	aDescriptor.Type = MODALTOP
	aDescriptor.WindowServiceName = MsgType
	aDescriptor.ParentIndex = -1
	aDescriptor.Parent = ParentWin
	#aDescriptor.Bounds = Rectangle()
	aDescriptor.WindowAttributes = MsgButtons
	
	tk = ParentWin.getToolkit()
	msgbox = tk.createWindow(aDescriptor)
	
	msgbox.setMessageText(MsgText)
	if MsgTitle :
		msgbox.setCaptionText(MsgTitle)
		
	return msgbox.execute()

class ImportKMLDialog( unohelper.Base, XActionListener ):
	def __init__(self,ctx,psm):
		dialogModel = psm.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel",ctx)
		dialogModel.PositionX = 100
		dialogModel.PositionY = 100
		dialogModel.Width = 155 
		dialogModel.Height = 80
		dialogModel.Title = "Import City POIs"
    
		mdlLabelCity = dialogModel.createInstance("com.sun.star.awt.UnoControlFixedTextModel")
		mdlLabelCity.PositionX = 5
		mdlLabelCity.PositionY = 12
		mdlLabelCity.Width = 35 
		mdlLabelCity.Height = 10
		mdlLabelCity.Label = "City Name:"
		dialogModel.insertByName("lblCity",mdlLabelCity)

		mdlLabelKML = dialogModel.createInstance("com.sun.star.awt.UnoControlFixedTextModel")
		mdlLabelKML.PositionX = 5
		mdlLabelKML.PositionY = 30
		mdlLabelKML.Width = 40 
		mdlLabelKML.Height = 10
		mdlLabelKML.Label = "KML with POIs:"
		dialogModel.insertByName("lblKML",mdlLabelKML)
    
		mdlInCity = dialogModel.createInstance("com.sun.star.awt.UnoControlEditModel")
		mdlInCity.PositionX = 50
		mdlInCity.PositionY = 8
		mdlInCity.Width = 100 
		mdlInCity.Height = 15
		dialogModel.insertByName("inCity",mdlInCity)
    
		mdlInKML = dialogModel.createInstance("com.sun.star.awt.UnoControlFileControlModel")
		mdlInKML.PositionX = 50
		mdlInKML.PositionY = 25
		mdlInKML.Width = 100 
		mdlInKML.Height = 15
		dialogModel.insertByName("inKML",mdlInKML)
    
		mdlProgress = dialogModel.createInstance("com.sun.star.awt.UnoControlProgressBarModel")
		mdlProgress.PositionX = 5
		mdlProgress.PositionY = 45
		mdlProgress.Width = 145 
		mdlProgress.Height = 10
		mdlProgress.ProgressValueMax = 300 # 50 for init, 50 - parse, 200 - load
		dialogModel.insertByName("progress",mdlProgress)
    
		mdlBtnImport = dialogModel.createInstance("com.sun.star.awt.UnoControlButtonModel")
		mdlBtnImport.PositionX = 50
		mdlBtnImport.PositionY = 60
		mdlBtnImport.Width = 60 
		mdlBtnImport.Height = 15
		mdlBtnImport.Label = "Import POIs"
		dialogModel.insertByName("btnImport",mdlBtnImport)
    
		self.dlg = psm.createInstanceWithContext("com.sun.star.awt.UnoControlDialog", ctx)
		self.dlg.setModel(dialogModel)
		self.toolkit = psm.createInstanceWithContext("com.sun.star.awt.ExtToolkit", ctx)
		
		self.cityname = self.dlg.getControl("inCity")
		self.kmlfile = self.dlg.getControl("inKML")
		self.progress = self.dlg.getControl("progress")
		self.btn = self.dlg.getControl("btnImport")
		
		self.btn.addActionListener(self)
	
	def show(self):
		self.dlg.setVisible(False)
		self.dlg.createPeer(self.toolkit, None)
		self.dlg.execute()
	
	def actionPerformed(self, actionEvent):
		doc = XSCRIPTCONTEXT.getDocument()
		parentwin = doc.CurrentController.Frame.ContainerWindow
		#MessageBox(parentwin,self.cityname.getText(),"DEBUG")
		
		try:
			self.progress.setValue(0)
		
			pts = loadKML(self.kmlfile.getText()) # Parse KML
		
			self.progress.setValue(25)
		
			clusters = buildClusters(pts) # Clusterize
		
			self.progress.setValue(50)
		
			sheet = createSheet(self.cityname.getText())
		
			partProgress = 250. / float(len(clusters))
			startProgress = 50
			callback = lambda p: self.progress.setValue(startProgress + int(partProgress*p))
		
			idx = 1
			mapfiles = []
		
			ptidx = 1
		
			for cluster in clusters:
				points = cluster.sort()
				for point in points:
					obj = sheet.getCellByPosition(1,2 + ptidx)
					obj.String = str(ptidx)
					obj = sheet.getCellByPosition(2,2 + ptidx)
					obj.String = point.getName()
#					obj = sheet.getCellByPosition(3,2 + ptidx)
#					obj.String = "Picture"			
					desc = point.getDescription()
					if desc != None:
						obj = sheet.getCellByPosition(4,2 + ptidx)
						obj.String = desc
					ptidx = ptidx + 1
				npoints,mapfile = downloadMap(cluster,idx,None,callback)		
				idx = idx + npoints
				mapfiles.append(mapfile)
				startProgress = startProgress + int(partProgress)
				
			#self.progress.setValue(250)
			
			# Row height if picture is present: 1790
			
			self.progress.setValue(300)
		
		except BaseException as e:
				MessageBox(parentwin,"Exception: %s" % str(e),"DEBUG")
				
		self.dlg.endDialog()
		self.dlg.dispose()

def showImportKMLDialog(event):
    Doc = XSCRIPTCONTEXT.getDocument() 
    ctx = uno.getComponentContext()
    psm = ctx.ServiceManager
    dialog = ImportKMLDialog(ctx,psm)
    dialog.show()
    #dp = psm.createInstance("com.sun.star.awt.DialogProvider")
    #dlg = dp.createDialog("vnd.sun.star.script:Standard.AddCity") 
    
    return None

g_exportedScripts = TestMessageBox,showImportKMLDialog,
