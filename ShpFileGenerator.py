# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ShpFileGenerator
                                 A QGIS plugin
 Generates SHP file from an image or tiff file
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2022-11-07
        git sha              : $Format:%H$
        copyright            : (C) 2022 by Vanshika
        email                : vanshikav.kumar@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import  QgsProject, QgsCoordinateReferenceSystem, QgsLayerTree, QgsLayerTreeNode, QgsPointXY, QgsVectorLayer,QgsRasterLayer, QgsMapLayer, QgsWkbTypes, QgsVectorFileWriter, QgsCoordinateTransform, QgsField, QgsDefaultValue, QgsRectangle, QgsFeatureIterator,QgsFeature, QgsGeometry, QgsTolerance, QgsMapSettings, QgsUnitTypes,QgsFeatureRequest,QgsAbstractGeometry,QgsPoint

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .ShpFileGenerator_dialog import ShpFileGeneratorDialog
import os.path
from qgis.PyQt.QtWidgets import QAction,QFileDialog
import tensorflow as tf
import segmentation_models as sm
from tensorflow.keras.preprocessing import image
from keras.models import load_model 
import numpy as np
import cv2
from matplotlib import pyplot as plt
import os
from pathlib import Path

import fiona
class ShpFileGenerator:
    """QGIS Plugin Implementation."""
    currentFile=''
    layerList=[]
    l=[]
    modelPath=r'C:\Users\hp\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\shpfilegenerator\classifier.tflite'

    finalPath=''
    seed=24

    batch_size= 16
    n_classes=4
    BACKBONE = 'resnet34'
    img_height = 256
    img_width  = 256
    img_channels =3

    IMG_HEIGHT = 256
    IMG_WIDTH  = 256
    IMG_CHANNELS =3
    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'ShpFileGenerator_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&ShpFileGenerator')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('ShpFileGenerator', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/ShpFileGenerator/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u''),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&ShpFileGenerator'),action)
            self.iface.removeToolBarIcon(action)

    def load_image(self,img_path):
    	img = image.load_img(img_path, target_size=(self.img_height, self.img_width))
    	img_tensor = image.img_to_array(img)                    # (height, width, channels)
    	#img_tensor = np.expand_dims(img_tensor, axis=0)         # (1, height, width, channels), add a dimension because the model expects this shape: (batch_size, height, width, channels)
    	img_tensor /= 255.                                      # imshow expects values in the range [0, 1]
    	return img_tensor
    def on_layer_changed(self, value):
    	self.currentFile=self.layersList[value]	


    def create_model(self):
        model = sm.Unet(self.BACKBONE, encoder_weights='imagenet', input_shape=(self.IMG_HEIGHT, self.IMG_WIDTH, self.IMG_CHANNELS),classes=self.n_classes, activation='softmax')
        model.compile('Adam', loss=sm.losses.categorical_focal_jaccard_loss, metrics=[sm.metrics.iou_score])
        return model
    def createSHP(self):
        if(self.dlg.lineEdit.text()==''or self.dlg.lineEdit.text()=='Select output adress'):
            self.dlg.lineEdit.setText('Select output adress')
            return
        
        interpreter=tf.lite.Interpreter(model_path=self.modelPath)
        interpreter.allocate_tensors()
        input_details=interpreter.get_input_details()
        output_details=interpreter.get_output_details()
        img=self.load_image(self.currentFile.dataProvider().dataSourceUri())
        interpreter.set_tensor(input_details[0]['index'],[img])
        interpreter.invoke()
        output_data=interpreter.get_tensor(output_details[0]['index'])
        pred = np.argmax(output_data, axis=3)
        output=pred[0]
        h_flip = cv2.flip(pred[0], 0)
        plt.imsave(self.finalPath+'boundary.jpg',h_flip)
        img=cv2.imread(self.finalPath+'boundary.jpg',1)
        edges=cv2.Canny(img,100,200)

        plt.imsave(self.finalPath+'edges.jpg',edges)
        lines=cv2.HoughLinesP(image=edges,lines=np.array([]),rho=1,theta=np.pi/180,threshold=2,minLineLength=0,maxLineGap=0)
        i=0
        for points in lines:
            list=[]
            k=[]
            k.append(points[0][0])
            k.append(points[0][1])
            a=tuple(k)
            list.append(a)
            k=[]
            k.append(points[0][2])
            k.append(points[0][3])
            a=tuple(k)
            list.append(a)
            schema = {
    'geometry':'LineString',
    'properties':[('Name','int')]
}
            mode='a'
            shpFile=Path(self.finalPath+'shpFile.shp')
            if(shpFile.is_file()==False):
                mode='w'
            lineShp=fiona.open(self.finalPath+'shpFile.shp',mode= mode,crs='EPSG:4326',driver='ESRI Shapefile', schema=schema)
            rowName='line'+(str)(i)
            i+=1
            self.dlg.label.setText(rowName)
            rowDict = {
'geometry' : {'type':'LineString',
                 'coordinates': list},
                 'id':i,
'properties': {'Name' : i},
}
            lineShp.write(rowDict)
            lineShp.close()
        vlayer = QgsVectorLayer(self.finalPath+'shpFile.shp', "SHP_layer", "ogr")
        QgsProject.instance().addMapLayer(vlayer)
        self.dlg.close()
    
    def select_output_file(self):
        filename=QFileDialog.getExistingDirectory(self.dlg,caption='Select a folder')
        #=QFileDialog.getSaveFolderName(self.dlg,"Select output file","","*shp")
        self.dlg.lineEdit.setText(filename)
        self.finalPath=filename+'/'
    
    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = ShpFileGeneratorDialog()
        self.dlg.pushButton.clicked.connect(self.select_output_file)
        self.dlg.label.setText('select the file')
        layers=self.iface.mapCanvas().layers()
        self.l=[]
        self.layersList=[]
        for layer in layers:
        	if layer.type()==QgsMapLayer.RasterLayer:
        		self.l.append(layer.name())
        		self.layersList.append(layer)

        self.dlg.AllFiles.clear()
        self.dlg.AllFiles.addItems(self.l)
        if(len(self.layersList)>0):
        	self.currentFile=self.layersList[0]
        self.dlg.AllFiles.currentIndexChanged.connect(self.on_layer_changed)
        # show the dialog
        self.dlg.show()
        self.dlg.createButton.clicked.connect(self.createSHP)
        # Run the dialog event loop
        result = self.dlg.exec_()
        