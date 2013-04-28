import uno
import unohelper
from com.sun.star.awt import XActionListener

class ImportClickListener( unohelper.Base, XActionListener ):
    def __init__(self, labelControl, prefix ):
        self.nCount = 0
        self.labelControl = labelControl
        self.prefix = prefix
        
    def actionPerformed(self, actionEvent):
        self.nCount = self.nCount + 1;
        self.labelControl.setText( self.prefix + str( self.nCount ) )

def createImportDialog(event):
    """Opens a dialog with a push button and a label, clicking the button increases the label counter."""
    try:
        ctx = uno.getComponentContext()
        smgr = ctx.ServiceManager

        dialogModel = smgr.createInstanceWithContext( 
            "com.sun.star.awt.UnoControlDialogModel", ctx)

        dialogModel.PositionX = 100
        dialogModel.PositionY = 100
        dialogModel.Width = 160 
        dialogModel.Height = 100
        dialogModel.Title = "Import City POIs"

        buttonModel = dialogModel.createInstance( 
            "com.sun.star.awt.UnoControlButtonModel" )

        buttonModel.PositionX = 37
        buttonModel.PositionY  = 66 
        buttonModel.Width = 80 
        buttonModel.Height = 25 
        buttonModel.Name = "bnImport" 
        buttonModel.TabIndex = 2         
        buttonModel.Label = "Import POI's" 

        labelModel = dialogModel.createInstance( 
            "com.sun.star.awt.UnoControlFixedTextModel" ); 

        labelModel.PositionX = 6 
        labelModel.PositionY = 10 
        labelModel.Width  = 35 
        labelModel.Height = 10 
        labelModel.Name = "lblCity" 
        labelModel.TabIndex = 1
        labelModel.Label = "Clicks "
        
        labelModel2 = dialogModel.createInstance( 
            "com.sun.star.awt.UnoControlFixedTextModel" ); 

        labelModel2.PositionX = 6 
        labelModel2.PositionY = 30 
        labelModel2.Width  = 40 
        labelModel2.Height = 10 
        labelModel2.Name = "lblKML" 
        labelModel2.TabIndex = 1
        labelModel2.Label = "Clicks "

        # insert the control models into the dialog model 
        dialogModel.insertByName( "bnImport", buttonModel); 
        dialogModel.insertByName( "lblCity", labelModel); 
        dialogModel.insertByName( "lblKML", labelModel2); 

        # create the dialog control and set the model 
        controlContainer = smgr.createInstanceWithContext( 
            "com.sun.star.awt.UnoControlDialog", ctx); 
        controlContainer.setModel(dialogModel); 

        # add the action listener
        controlContainer.getControl("bnImport").addActionListener(
            MyActionListener( controlContainer.getControl( "lblKML" ), labelModel2.Label ))

        # create a peer 
        toolkit = smgr.createInstanceWithContext( 
            "com.sun.star.awt.ExtToolkit", ctx);       

        controlContainer.setVisible(False);       
        controlContainer.createPeer(toolkit, None);

        # execute it
        controlContainer.execute()

        # dispose the dialog 
        controlContainer.dispose()
    except Exception,e:
        print str(e)
    
    return None

#g_exportedScripts = createImportDialog,
