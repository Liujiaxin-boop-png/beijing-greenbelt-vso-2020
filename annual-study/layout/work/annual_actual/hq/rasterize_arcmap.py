# -*- coding: ascii -*-
from __future__ import print_function
import arcpy, sys, os
shp,snap,out=sys.argv[1:4]
r=arcpy.Raster(snap)
arcpy.env.overwriteOutput=False
arcpy.env.outputCoordinateSystem=r.spatialReference
arcpy.env.extent=r.extent
arcpy.env.snapRaster=snap
arcpy.env.cellSize=snap
arcpy.env.pyramid='NONE'
arcpy.PolylineToRaster_conversion(shp,'roadval',out,'MAXIMUM_LENGTH','NONE',30)
print(arcpy.GetInstallInfo()['Version'],arcpy.GetMessages())
