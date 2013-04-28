from com.sun.star.awt import Rectangle
from com.sun.star.awt import WindowDescriptor

from com.sun.star.awt.WindowClass import MODALTOP
from com.sun.star.awt.VclWindowPeerAttribute import OK, OK_CANCEL, YES_NO, YES_NO_CANCEL, RETRY_CANCEL, DEF_OK, DEF_CANCEL, DEF_RETRY, DEF_YES, DEF_NO

import uno
import unohelper
from com.sun.star.awt import XActionListener

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
		mdlLabelKML.Label = "City Name:"
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
		
		self.dlg.getControl("btnImport").addActionListener(self)
	
	def show(self):
		self.dlg.setVisible(False)
		self.dlg.createPeer(self.toolkit, None)
		self.dlg.execute()
	
	def actionPerformed(self, actionEvent):
		doc = XSCRIPTCONTEXT.getDocument()
		parentwin = doc.CurrentController.Frame.ContainerWindow
		MessageBox(parentwin,self.cityname.getText(),"DEBUG")
		
		self.progress.setValue(0)
		
		
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
