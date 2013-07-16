from com.sun.star.awt import Rectangle
from com.sun.star.awt import WindowDescriptor

from com.sun.star.awt.WindowClass import MODALTOP
from com.sun.star.awt.VclWindowPeerAttribute import OK, OK_CANCEL, YES_NO, YES_NO_CANCEL, RETRY_CANCEL, DEF_OK, DEF_CANCEL, DEF_RETRY, DEF_YES, DEF_NO

from com.sun.star.awt import Size, Point as SWTPoint

import uno
import unohelper
from com.sun.star.awt import XActionListener
from com.sun.star.table.CellHoriJustify import CENTER
from com.sun.star.awt.FontWeight import BOLD
from com.sun.star.table import TableBorder, BorderLine

import xml.etree.ElementTree as etree
from math import cos,pi,sqrt,sin,atan2
import urllib.request as request
import urllib.parse as parse
from tempfile import NamedTemporaryFile
import json

########################### Internal stuff #############################
class Point:
	def __init__(self,name,lon,lat,desc=None):
		self.name=name
		self.lon=lon
		self.lat=lat
		self.desc=desc
		self.address = None
		self.city = None
		
	def __str__(self):
		return str(self.lat) + "," + str(self.lon)
	
	def toobj(self):
		if self.lat == None:
			return { "city" : self.city, "street" : street}
		return { "latLng" : { "lat": self.lat, "lng" : self.lon } }
		
	def getLat(self):
		return self.lat
	
	def setLat(self,lat):
		self.lat = lat
	
	def getLon(self):
		return self.lon
	
	def setLon(self,lon):
		self.lon = lon
	
	def getName(self):
		return self.name
	
	def getDescription(self):
		return self.desc
	
	def setAddress(self,address):
		self.address = address
	
	def getAddress(self):
		return self.address
		
	def setCity(self,city):
		self.city = city
	
	def distance(self,pt):
		"""
		Calculate distance in meters between two points
		"""
		r = 6378137
		toRad = lambda x : pi * x / 180.0
		dLat = toRad(self.lon - pt.lon)
		dLon = toRad(self.lat - pt.lat)
		lat1 = toRad(self.lon)
		lat2 = toRad(pt.lon)
		a = sin(dLat*0.5) * sin(dLat*0.5) + sin(dLon*0.5)*sin(dLon*0.5) * cos(self.lon) * lat1 * lat2
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
		dLon1 = 1000.  * cos(lons[0]) / 111111. # Western
		dLon2 = 1000.  * cos(lons[npts-1]) / 111111. # Eastern
		
		sw = Point("SW", lons[0] - dLon1, lats[0] - dLat)
		ne = Point("NE", lons[npts-1] + dLon2, lats[npts-1] + dLat)
		
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
	
	def reorder(self):
		
		self.points = self.dedup()
		
		
		base = "http://www.mapquestapi.com/directions/v1/optimizedroute?"
		key = "key=Fmjtd|luub2q0t2q%2Crn%3Do5-9u7s0u"
		unit = "&unit=k"
		routeType = "&routeType=multimodal"
		reversegeocode = "&doReverseGeocode=false"
		narrator = "&narrativeType=text"
		locale = "&locale=uk_UA"
		outformat="&outFormat=json"
		
		params = {}		
		params["options"] = { "unit" : "k", "routeType" : "pedestrian", "locale" : "uk_UA"}
		home = self.pickFirstPoint()
		path = self.points.copy()
		path.remove(home)
		
		params["locations"] = [home.toobj()] + [ pt.toobj() for pt in path ]
		
		jsonstr = "&" + parse.urlencode({"json":json.dumps(params)}) 
		
		handle = request.urlopen(base + key + jsonstr)
		
		jsonstr = "".join([line.decode("utf-8","strict") for line in handle.readlines()])
		
		handle.close()
		
		response = json.loads(jsonstr)
		
		route = response["route"]
		info = response["info"]
		
		self.bb = ( Point("UL",float(route["boundingBox"]["ul"]["lng"]),float(route["boundingBox"]["ul"]["lat"])), Point("LR",float(route["boundingBox"]["lr"]["lng"]),float(route["boundingBox"]["lr"]["lat"])))
		
		session = route["sessionId"]
		distance = float(route["distance"])
		travelTime = route["formattedTime"]
		
		locationSequence = route["locationSequence"]
		
		points = [self.points[idx] for idx in locationSequence]
		
		locations = route["locations"]
		
		for idx in range(0,len(locations)):
			points[idx].setAddress(locations[idx]["street"])
			points[idx].setLat(locations[idx]["latLng"]["lat"])
			points[idx].setLon(locations[idx]["latLng"]["lng"])
		
		self.points = points
		
		routes = []
		
		for leg in route["legs"]:
			step = {}
			step["distance"] = float(leg["distance"]) * 1000. # Convert to meters
			step["time"] = leg["formattedTime"]
			substeps = []
			for maneuver in leg["maneuvers"]:
				substep = {}
				substep["text"] = maneuver["narrative"]
				substep["icon"] = maneuver["iconUrl"]
				substep["distance"] = float(maneuver["distance"]) * 1000. # Convert to meters
				substep["time"] = maneuver["formattedTime"]
				#substep["map"] = maneuver["mapUrl"]
				substeps.append(substep)
			step["steps"] = substeps
			routes.append(step)
		
		return session,routes,distance,travelTime
	
	def sort(self):
		pt = self.pickFirstPoint()
		points = self.points.copy()
		points.remove(pt)
		path = [pt] + points
		#points = self.dedup() #self.points.copy()
		#points.remove(pt)
		
		#while len(points) != 0:
		#	distances = [pt.distance(point) for point in points]
		#	min_dist = min(distances)
		#	idx = distances.index(min_dist)
		#	pt = points.pop(idx)
		#	path.append(pt)
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

def downloadMap(cluster, startIDX = 1, sessionID=None, progressCallback = None):

	points = cluster.sort()

	url = "http://open.mapquestapi.com/staticmap/v4/getmap?key=Fmjtd|luub2q0t2q%2Crn%3Do5-9u7s0u&size=1454,2048&type=map&imagetype=png"
	
	homept = findHome(points)
	home = ""
	if homept != None:
		points.remove(homept)
		home = "&xis=https://dl.dropboxusercontent.com/u/26599381/Home-icon.png,1,c," + str(homept) #+ parse.urlencode({"xis":"http://icons.iconarchive.com/icons/artua/mac/32/Home-icon.png"}) + ",1,C,"+str(home)

	se,nw = cluster.getBB()
	#bestfit = "&bestfit=%7.5f,%7.5f,%7.5f,%7.5f" % (se.getLat(),se.getLon(),nw.getLat(),nw.getLon())
	bestfit = "&bestfit=%s,%s" % (str(se),str(nw))

	idx=startIDX
	pois="&pois="
	for pt in points:
		pois = pois + "bluegreen_1-" + str(idx) + "," + str(pt) + "|"
		idx=idx+1
		
	pois = pois[:len(pois)-1]
	
	session = ""
	if sessionID != None:
		session = "&session=" + sessionID
	
	handle = request.urlopen(url + bestfit + pois + home + session)
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

def addBorderToRegion(region):
	RGB = lambda r,g,b: r*256*256 + g*256 + b
	#line = BorderLine()
	#line.Color = RGB(127,127,127)
	#line.InnerLineWidth = 0
	#line.OuterLineWidth = 0
	
	border = region.TopBorder #TableBorder()
	border.OuterLineWidth = 1.75
	border.Color = 0
	#border.TopLine = line
	#border.IsTopLineValid = True
	#border.BottomLine = line
	#border.IsBottomLineValid = True
	#border.LeftLine = line
	#border.IsLeftLineValid = True
	#border.RightLine = line
	#border.IsRightLineValid = True
	#border.HorizontalLine = line
	#border.IsHorizontalLineValid = True
	#border.VerticalLine = line
	#border.IsVerticalLineValid = True
	
	region.TopBorder = border
	region.BottomBorder = border
	region.LeftBorder = border
	region.RightBorder = border

def createCitySheet(name):
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
	obj.Width = 6840
	
	obj = sheet.getColumns().getByName("E")
	obj.Width = 6840
	
	obj = sheet.getRows().getByIndex(0)
	obj.Height = 210
	
	obj = sheet.getRows().getByIndex(1)
	obj.Height = 1400
	
	obj = sheet.getCellRangeByName("B2:E2")
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
	obj.String = "Address"
	obj = sheet.getCellByPosition(4,2)
	obj.String = "Comment"

	
	obj = sheet.getCellRangeByName("B3:E3")
	
	RGB = lambda r,g,b: r*256*256 + g*256 + b
	
	obj.CellBackColor = RGB(128,128,128)
	obj.CharWeight = BOLD
	
	return sheet

def createDirectionsSheet(city):
	oDoc = XSCRIPTCONTEXT.getDocument()
	name = city + " Directions"
	sheet = oDoc.Sheets.insertNewByName(name,oDoc.Sheets.getCount())
	sheet = oDoc.Sheets.getByName(name)
	
	obj = sheet.getColumns().getByName("A")
	obj.Width = 270
	
	obj = sheet.getColumns().getByName("B")
	obj.Width = 540
	
	obj = sheet.getColumns().getByName("C")
	obj.Width = 780
	
	#obj = sheet.getColumns().getByName("D")
	#obj.Width = 6840
	
	#obj = sheet.getColumns().getByName("E")
	#obj.Width = 6840
	
	obj = sheet.getColumns().getByName("G")
	obj.Width = 6270
	# Image height 4250
	# Width of noramll cell is 2240
	# Height - 470
	
	obj = sheet.getRows().getByIndex(0)
	obj.Height = 210
	
	#obj = sheet.getRows().getByIndex(1)
	#obj.Height = 1400
	
	obj = sheet.getCellRangeByName("B2:G2")
	obj.merge(True)
	
	obj = sheet.getCellByPosition(1,1)
	obj.String = name
	obj.HoriJustify = CENTER
	obj.CharFontName = "Tahoma"
	obj.CharHeight = 33
	
	obj = sheet.getCellByPosition(1,2)
	obj.String = "#"
	obj = sheet.getCellByPosition(2,2)
	obj.String = "Icon"
	obj = sheet.getCellByPosition(3,2)
	obj.String = "Step"
	obj = sheet.getCellByPosition(4,2)
	obj.String = "Distance"
	obj = sheet.getCellByPosition(5,2)
	obj.String = "Time"
	obj = sheet.getCellByPosition(6,2)
	obj.String = "Map"

	
	obj = sheet.getCellRangeByName("B3:G3")
	
	RGB = lambda r,g,b: r*256*256 + g*256 + b
	
	obj.CellBackColor = RGB(128,128,128)
	obj.CharWeight = BOLD
	
	return sheet

def useEmbeddedImage(sheet,url, x, y, w, h):
	size = Size()
	coord = SWTPoint()
	coord.X = x
	coord.Y = y
	size.Width = w
	size.Height = h
	
	oDoc = XSCRIPTCONTEXT.getDocument()
	oGraph = oDoc.createInstance("com.sun.star.drawing.GraphicObjectShape")
	oGraph.GraphicURL = url
	oGraph.Size = size
	oGraph.Position = coord
			
	drawPage = sheet.DrawPage
	drawPage.add(oGraph)

def embedImage(filename, intname):
		fpath = "file://" + filename
		
		oDoc = XSCRIPTCONTEXT.getDocument()
		
		bitmaps = oDoc.createInstance( "com.sun.star.drawing.BitmapTable" )
		bitmaps.insertByName(intname,fpath)
		url = bitmaps.getByName(intname)
		return url

def lookupEmbeddedImage(intname):
	oDoc = XSCRIPTCONTEXT.getDocument()
	bitmaps = oDoc.createInstance( "com.sun.star.drawing.BitmapTable" )
	url = bitmaps.getByName(intname)
	return url	

def insertImageOnSheet(sheet,filename, intname, x, y, w, h):
	url = embedImage(filename, intname)
	useEmbeddedImage(sheet,url,x,y,w,h)

def insertInternalImageOnSheet(sheet, intname, x, y, w, h):
	url = lookupEmbeddedImage(intname)
	useEmbeddedImage(sheet,url,x,y,w,h)

def populateRoute(sheet, route, idx, ridx):

	# XXX: Handle this on config sheet
	cache = {}
	cache["http://content.mapquest.com/mqsite/turnsigns/icon-dirs-start_sm.gif"] 	= { "name" : "8a2d083690e0f279be9b06edfdfaf7f3c3b6a7ab" , "width" : 780, "height" : 340}
	cache["http://content.mapquest.com/mqsite/turnsigns/rs_left_sm.gif"] 			= { "name" : "6c98e14609dd3b0a8babb467ea00ecf22410a41c" , "width" : 610, "height" : 580}
	cache["http://content.mapquest.com/mqsite/turnsigns/rs_straight_sm.gif"] 		= { "name" : "14840649f7f088875128ca11388234a68f23f98d" , "width" : 610, "height" : 580}
	cache["http://content.mapquest.com/mqsite/turnsigns/rs_right_sm.gif"] 			= { "name" : "2717998d91c8baf79ba8c5489d85d0d1744d9541" , "width" : 610, "height" : 580}
	cache["http://content.mapquest.com/mqsite/turnsigns/icon-dirs-end_sm.gif"] 		= { "name" : "954a6bed01d49a845f34802ee1013647140ef27f" , "width" : 780, "height" : 340}
	cache["http://content.mapquest.com/mqsite/turnsigns/rs_fork_left2_sm.gif"] 		= { "name" : "0bc1ade732d84e58934428e7a6e5235254e219fe" , "width" : 610, "height" : 580}
	cache["http://content.mapquest.com/mqsite/turnsigns/rs_fork_right2_sm.gif"] 	= { "name" : "a57257819899785cbc5e771cbb6dca32b28655ec" , "width" : 610, "height" : 580}
	cache["http://content.mapquest.com/mqsite/turnsigns/rs_slight_left_sm.gif"] 	= { "name" : "e5b14ddfed6aa803b87f7a9ecfa6b75862101f8d" , "width" : 610, "height" : 580}
	cache["http://content.mapquest.com/mqsite/turnsigns/rs_slight_right_sm.gif"] 	= { "name" : "53ba36dff04ba46398a085126166f23e2c1e0eae" , "width" : 610, "height" : 580}
	
	steps = route["steps"]
	startRow = str(ridx + 1) # Row numerations starts from 0
	endRow = ridx + len(steps) + 1 # Additional row for totals
	
	obj = sheet.getCellRangeByName("B"+startRow + ":B" + str(endRow) )
	obj.merge(True)
	obj = sheet.getCellByPosition(1,ridx)
	obj.String = str(idx)
	
	for i in range(ridx, ridx + len(steps)):
		obj = sheet.getRows().getByIndex(i)
		obj.Height = 4250
	
	obj = sheet.getCellRangeByName("D"+startRow + ":F" + str(endRow-1) ) # Exclude summary row
	tmp = []
	shiftX = 810
	shiftY = 2040
	for step in steps:
		tmp.append((step["text"],step["distance"],step["time"]))
		icon = step["icon"]
		iconOBJ = cache[icon]
		insertInternalImageOnSheet(sheet,iconOBJ["name"],shiftX + (780 - iconOBJ["width"])/2,shiftY,iconOBJ["width"],iconOBJ["height"])
		shiftY = shiftY + 4250
		# Should insert graphics here
	obj.DataArray = tuple(tmp)
	obj = sheet.getCellRangeByName("C"+ str(endRow-1) + ":D" + str(endRow-1) )
	obj.merge(True)
	obj = sheet.getCellByPosition(2,endRow-1)
	obj.String = str(idx)
	obj = sheet.getCellByPosition(4,endRow-1)
	obj.String = route["distance"]
	obj = sheet.getCellByPosition(5,endRow-1)
	obj.String = route["time"]
	return endRow + 1
	

def loadJSON(url):
	handle = request.urlopen(url)
	obj = json.loads("".join([line.decode("utf-8","strict") for line in handle.readlines()]))
	handle.close()
	return obj

def findHomeInCity(city):
	oDoc = XSCRIPTCONTEXT.getDocument()
	sheet = oDoc.Sheets.getByName("Accommodation")
	
	obj = sheet.getCellRangeByName("B4:B50")
	data = obj.DataArray
	
	idx = 0
	# TODO Fool check should be here
	for row in data:
		if row[0] == city:
			break
		idx = idx + 1
	obj = sheet.getCellByPosition(6,3+idx) # $G4+idx == Home address
	address = obj.String
	
	tmp = address.split(",")
	if len(tmp) > 1:
		city = tmp[1].strip()
	
	url = "https://translate.yandex.net/api/v1.5/tr.json/detect?key=trnsl.1.1.20130429T215441Z.6f616164f163020b.8fb0093ebd7d15e7330a32a8c6269f04bf4814e7&text=" + parse.quote(city)
	obj = loadJSON(url)
	lang = obj["lang"]
	
	cityen = city
	if lang != "en":
		url = "https://translate.yandex.net/api/v1.5/tr.json/translate?key=trnsl.1.1.20130429T215441Z.6f616164f163020b.8fb0093ebd7d15e7330a32a8c6269f04bf4814e7&lang=" + lang +"-en&text=" + parse.quote(city)
		obj = loadJSON(url)
		cityen = obj["text"][0]
	
	url = "http://open.mapquestapi.com/geocoding/v1/address?key=Fmjtd|luub2q0t2q%2Crn%3Do5-9u7s0u&inFormat=kvp&outFormat=json&thumbMaps=false&maxResults=1&location=" + parse.quote(address) +","+parse.quote(cityen)
	obj = loadJSON(url)
	
	lon = obj["results"][0]["locations"][0]["latLng"]["lng"]
	lat = obj["results"][0]["locations"][0]["latLng"]["lat"]
	
	home = Point("Home",lon,lat)
	#home.setCity(city)
	#home.setAddress(address)
	return home

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
		
		self.psm = psm
		
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
		self.dlg.dispose()
	
	def actionPerformed(self, actionEvent):
		doc = XSCRIPTCONTEXT.getDocument()
		parentwin = doc.CurrentController.Frame.ContainerWindow
		#MessageBox(parentwin,self.cityname.getText(),"DEBUG")
		
		try:
			self.progress.setValue(0)

			cityname = self.cityname.getText()
			sheet = createCitySheet(cityname)
			
			#routeSheet = createDirectionsSheet(cityname)
			
			homept = findHomeInCity(cityname)
			#MessageBox(parentwin,url,"DEBUG")
			pts = [homept] + loadKML(self.kmlfile.getText()) # Parse KML
		
			self.progress.setValue(25)
		
			clusters = buildClusters(pts) # Clusterize
		
			self.progress.setValue(50)
		
		
			partProgress = 250. / float(len(clusters))
			startProgress = 50
			callback = lambda p: self.progress.setValue(startProgress + int(partProgress*p))
		
			idx = 1
			mapfiles = []
		
			ptidx = 0
			
			ridx = 3
			sidx = 1
			
			n = 0
			baseX = 20130
			baseY = 2000
			baseW = 11005
			baseH = 15500
			baseStrip = 50
		
			for cluster in clusters:
				session = None
				if cluster.getSize() > 2:
					session, routes, distance, travelTime = cluster.reorder()
				points = cluster.sort()
				for point in points:
					obj = sheet.getCellByPosition(1,3 + ptidx)
					obj.String = str(ptidx)
					obj = sheet.getCellByPosition(2,3 + ptidx)
					obj.String = point.getName()		
					desc = point.getAddress()
					if desc != None:
						obj = sheet.getCellByPosition(3,3 + ptidx)
						obj.String = desc
					ptidx = ptidx + 1
				npoints,mapfile = downloadMap(cluster,idx,session,callback)		
				idx = idx + npoints
				insertImageOnSheet(sheet, mapfile,cityname+"-"+str(n), baseX, baseY + (baseH+baseStrip)*n, baseW, baseH)
				
				if session != None:
					for route in routes:
						#ridx = populateRoute(routeSheet,route, sidx, ridx)
						sidx = sidx + 1
				startProgress = startProgress + int(partProgress)
				n = n + 1				
			
			# Row height if picture is present: 1790
			
			
			addBorderToRegion(sheet.getCellRangeByName("B3:E"+str(3+ptidx)))
			
			self.progress.setValue(300)
			
			MessageBox(parentwin,"Import success","Done")
			oDoc = XSCRIPTCONTEXT.getDocument()
			oDoc.CurrentController.ActiveSheet = sheet
			oDoc.CurrentController.setPropertyValue( "ShowGrid",  False ) 
		
		except BaseException as e:
				from traceback import format_exc
				MessageBox(parentwin,"Exception: %s\n%s" % (str(e),format_exc()),"DEBUG")
				
		self.dlg.endExecute()

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
