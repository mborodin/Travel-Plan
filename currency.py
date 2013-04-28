import uno
import xml.etree.ElementTree as etree
import urllib.request

def findItem(root,name):
	found = None
	for item in root.getchildren():
		if item.findtext("char3") == name:
			found = item
			break
	return found

def updateCurrency(event):
	oDoc = XSCRIPTCONTEXT.getDocument()
	sheet = oDoc.Sheets.getByName("Summary")
	currencyRange = sheet.getCellRangeByName("Currencies")
	data = currencyRange.DataArray
	tmp = []
	
	handle=urllib.request.urlopen("http://bank-ua.com/export/currrate.xml")
	tree=etree.parse(handle)
	root=tree.getroot()
	
	for row in data:
		item = findItem(root,row[0])
		if item != None:
			val = float(item.findtext("rate"))/float(item.findtext("size"))
			tmp.append((row[0],val))
		else:
			tmp.append(('',''))
	
	currencyRange.DataArray = tuple(tmp)
	
	handle.close()
	return None

g_exportedScripts = updateCurrency,
