import xml.etree.ElementTree as etree
import urllib.request
import uno

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



def invokeVBScript(script,_object,param = None):
	psm = uno.getComponentContext().ServiceManager
	scriptProvider = psm.createInstance("com.sun.star.script.provider.MasterScriptProviderFactory").createScriptProvider("")
	xscript = scriptProvider.getScript("vnd.sun.star.script:Standard.Trip."+script+"?language=Basic&location=application")
	ret = None
	if param != None:
		ret = xscript.invoke((_object,),param)
	else:
		ret = xscript.invoke((_object,))
	return ret

def btnClick(event):
	oDoc = XSCRIPTCONTEXT.getDocument()
	sheet = oDoc.Sheets.getByName("Summary")
	r = invokeVBScript("showAlertMessage",sheet)
	invokeVBScript("showAlertMessageP",sheet,r)
	return None

######################### Global exports ###############################
g_exportedScripts = updateCurrency,btnClick,
