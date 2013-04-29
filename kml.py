#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  kml.py
#  
#  Copyright 2013 Unknown <SURC\m.borodin@m-borodin-l.surc.kiev.ua>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

import xml.etree.ElementTree as etree
from math import cos,pi,sqrt,sin,atan2
import urllib.request as request
import urllib.parse as parse
from tempfile import NamedTemporaryFile
import json

class Point:
	def __init__(self,name,lon,lat,desc=None):
		self.name=name
		self.lon=lon
		self.lat=lat
		self.desc=desc
		self.address = None
		
	def __str__(self):
		return str(self.lat) + "," + str(self.lon)
		
	def getLat(self):
		return self.lat
	
	def getLon(self):
		return self.lon
	
	def getName(self):
		return self.name
	
	def getDescription(self):
		return self.desc
		
	def setAddress(self,address):
		self.address = address
	
	def getAddress(self):
		return self.address
	
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
	
	def toobj(self):
		return { "latLng" : { "lat": self.lat, "lng" : self.lon } }
		
	def tojson(self):
		return json.dumps(self.toobj())

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
	
	def reorganize(self,date,time):
		
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
		#params["unit"] = "k"
		#params["routeType"] = "multimodal"
		#params["doReverseGeocode"] = "false"
		#params["narrativeType"] = "text"
		#params["locale"] = "uk_UA"
		
		params["options"] = { "unit" : "k", "routeType" : "pedestrian", "locale" : "uk_UA", "timeType":2, "dateType":0, "date" : date, "localTime" : time}
		
		class Params(dict):
			pass
		
		p=Params()
		p.unit = "k"
		p.routeType = "multimodal"
		p.doReverseGeocode = False
		p.narrativeType = "text"
		p.locale = "uk_UA"
		
		home = self.pickFirstPoint()
		#params["from"] = home.toobj()
		
		#p["from"] = home.toobj()
		
		path = self.points.copy()
		path.remove(home)
		
		params["locations"] = [home.toobj()] + [ pt.toobj() for pt in path ]
		
		#print("From: %s\nTo: %s" % (str(params["from"]),params["locations"]))
		
		
		#import sys
		#contentlength = sys.getsizeof(p)
		
		jsonstr = "&" + parse.urlencode({"json":json.dumps(params)}) 
		#"&json=" + json.dumps(params)
		
		#print(jsonstr)
		
		#req = request.Request(base + key + outformat, p, {"Content-Length" : contentlength})
		
		#print(base + key + jsonstr)
		
		handle = request.urlopen(base + key + jsonstr)
		
		jsonstr = "".join([line.decode("utf-8","strict") for line in handle.readlines()])
		
		response = json.loads(jsonstr)
		
		route = response["route"]
		info = response["info"]
		
		self.bb = ( Point("UL",float(route["boundingBox"]["ul"]["lng"]),float(route["boundingBox"]["ul"]["lat"])), Point("LR",float(route["boundingBox"]["lr"]["lng"]),float(route["boundingBox"]["lr"]["lat"])))
		
		session = route["sessionId"]
		distance = float(route["distance"])
		
		locationSequence = route["locationSequence"]
		
		points = [self.points[idx] for idx in locationSequence]
		
		locations = route["locations"]
		
		for idx in range(0,len(locations)):
			points[idx].setAddress(locations[idx]["street"])
		
		self.points = points
		
		return session,distance
		
	
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

def downloadMap(cluster, startIDX = 1, sessionID=None):

	points = cluster.sort()

	url = "http://open.mapquestapi.com/staticmap/v4/getmap?key=Fmjtd|luub2q0t2q%2Crn%3Do5-9u7s0u&size=2048,2048&type=map&imagetype=png"
	
	homept = findHome(points)
	home = ""
	if homept != None:
		points.remove(homept)
		home = "&xis=https://dl.dropboxusercontent.com/u/26599381/Home-icon.png,1,c," + str(homept) #+ parse.urlencode({"xis":"http://icons.iconarchive.com/icons/artua/mac/32/Home-icon.png"}) + ",1,C,"+str(home)

	se,nw = cluster.getBB()
	bestfit = "&bestfit=%7.5f,%7.5f,%7.5f,%7.5f" % (se.getLat(),se.getLon(),nw.getLat(),nw.getLon())


	idx=startIDX
	pois="&pois="
	for pt in points:
		pois = pois + "bluegreen_1-" + str(idx) + "," + str(pt) + "|"
		idx=idx+1
		
	pois = pois[:len(pois)-1]
	
	session = ""
	if sessionID != None:
		session = "&session=" + sessionID
	
	print(url + bestfit + pois + home + session)
	handle = request.urlopen(url + bestfit + pois + home + session)
	fout = NamedTemporaryFile(prefix="map-",suffix=".png",delete=False)
	
	content = handle.read(-1)
	fout.write(content)
	fout.close()
	handle.close()
	
	return len(points)
	
	

def main():
	
	pts = loadKML("AugustinerBrustuben.kml")

	clusters = buildClusters(pts)
	
	print(len(clusters))
	bb=clusters[0].getBB()
	print(str(bb[0]),str(bb[1]))
	
	print(pts[0])
	print(pts[1])
	
	print(pts[0].distance(pts[1]))
	
	print("===========================================================")
	
	#clusters[0].reorganize()
	
	idx = 1
	for cluster in clusters:
		session = None
		if cluster.getSize() > 2:
			session,distance = cluster.reorganize("06/25/2013","09:00")
		idx = idx + downloadMap(cluster,idx,session)
	
	#getDirections(path)
	
	return 0

if __name__ == '__main__':
	main()

