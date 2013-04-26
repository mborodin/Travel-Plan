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
#import urllib.request

def main():
	
	fin = open("/tmp/my.kml","r")
	tree = etree.parse(fin)
	root = tree.getroot()
	
	bb_lat_arr = []
	bb_lon_arr = []
	
	for element in root.findall("{http://earth.google.com/kml/2.2}Document/{http://earth.google.com/kml/2.2}Placemark"):
		name = element.findtext("{http://earth.google.com/kml/2.2}name")
		coordinates = element.findtext("{http://earth.google.com/kml/2.2}Point/{http://earth.google.com/kml/2.2}coordinates")
		coords_s = coordinates.split(",")
		coords = (float(coords_s[0]),float(coords_s[1]))
		bb_lat_arr.append(coords[0])
		bb_lon_arr.append(coords[1])
	
	bb_lat_arr.sort()
	bb_lon_arr.sort()
	
	api = "http://api06.dev.openstreetmap.org/api/0.6/map?bbox=" + str(bb_lon_arr[0]) + "," + str(bb_lat_arr[0]) + "," + str(bb_lon_arr[len(bb_lon_arr)-1]) + "," + str(bb_lat_arr[len(bb_lat_arr)-1])
	print(api)
	
	center = (0.5*(bb_lat_arr[len(bb_lat_arr)-1]+bb_lat_arr[0]),0.5*(bb_lon_arr[len(bb_lon_arr)-1]+bb_lon_arr[0]))
	dist = (bb_lat_arr[len(bb_lat_arr)-1]-bb_lat_arr[0],bb_lon_arr[len(bb_lon_arr)-1]-bb_lon_arr[0])
	
	print(center)
	print(dist)
	
	return 0

if __name__ == '__main__':
	main()

