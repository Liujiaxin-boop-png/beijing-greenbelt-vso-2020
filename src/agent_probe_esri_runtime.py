"""Read-only licensed runtime probe; makes no system/licence changes."""
from __future__ import print_function
import sys
import json
import os
if sys.version_info[0]==2:
    import arcinfo
import arcpy
print('PYTHON',sys.executable);sys.stdout.flush()
print('INSTALL',json.dumps(arcpy.GetInstallInfo()));sys.stdout.flush()
print('PRODUCT',arcpy.ProductInfo());sys.stdout.flush()
print('EXTENSION',arcpy.CheckExtension('Spatial'));sys.stdout.flush()
print('BEFORE_CHECKOUT');sys.stdout.flush()
print('CHECKOUT',arcpy.CheckOutExtension('Spatial'));sys.stdout.flush()
print('BEFORE_CHECKIN');sys.stdout.flush()
print('CHECKIN',arcpy.CheckInExtension('Spatial'));sys.stdout.flush()
print('AFTER_CHECKIN');sys.stdout.flush()
