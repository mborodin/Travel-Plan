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
#import urllib.request

class Point:
	def __init__(self,name,lat,lon,desc=None):
		self.name=name
		self.lon=lon
		self.lat=lat
		self.desc=desc
		
	def __str__(self):
		return self.name + " is @ Lon: " + str(self.lon) + " Lat: " + str(self.lat)
		
	def getLat(self):
		return self.lat
	
	def getLon(self):
		return self.lon
	
	def getName(self):
		return self.name
	
	def getDescription(self):
		return self.desc
	
	def distance(self,pt):
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



def main():
	
	fin = open("AugustinerBrustuben.kml","r")
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

	clusters = buildClusters(pts)
	
	print(len(clusters))
	bb=clusters[0].getBB()
	print(str(bb[0]),str(bb[1]))
	
	print(pts[0])
	print(pts[1])
	
	print(pts[0].distance(pts[1]))
	
	return 0

if __name__ == '__main__':
	main()

