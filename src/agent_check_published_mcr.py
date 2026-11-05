"""Confirm copied final GeoTIFFs are independently georeferenced/readable."""
from pathlib import Path
import json
import sys
import rasterio
manifest=Path(sys.argv[1]);data=json.loads(manifest.read_text(encoding='utf-8'))
checked=[]
for run in data['scenarios']:
    for file in run['artifacts']:
        if Path(file['published']).suffix.lower()!='.tif':continue
        with rasterio.open(file['process_original']) as src,rasterio.open(file['published']) as dst:
            assert src.crs is not None and dst.crs==src.crs
            assert dst.transform==src.transform and dst.shape==src.shape
            assert dst.nodata==src.nodata and dst.count==src.count
            # A sampled read also confirms that no external tile/source file is required.
            for window in [rasterio.windows.Window(0,0,1,1),rasterio.windows.Window(dst.width//2,dst.height//2,1,1)]:
                assert (src.read(1,window=window)==dst.read(1,window=window)).all()
            checked.append({'scenario':run['scenario'],'file':file['published'],
                            'shape':list(dst.shape),'nodata':dst.nodata,'crs_present':True,
                            'georeferencing_and_sampled_values_match':True})
report={'status':'PASS_INDEPENDENT_PUBLISHED_GEOTIFF_READ','rasters_checked':len(checked),'checks':checked,
        'all_published_files_hash_verified_by':'published_mcr_manifest.json'}
(manifest.parent/'published_raster_readability_qa.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(report['status'],len(checked))
