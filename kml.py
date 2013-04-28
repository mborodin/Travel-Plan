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
from tempfile import NamedTemporaryFile
import json

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

def downloadMap(cluster, startIDX = 1, routes=None):

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
	print("[DEBUG] Temp file name is %s" % fout.name)
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
	idx = 1
	for cluster in clusters:
		idx = idx + downloadMap(cluster)
	
	#getDirections(path)
	
	return 0

if __name__ == '__main__':
	main()

