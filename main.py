import geopandas as gpd
import pandas as pd

def read_file(file):
    if file.lower().endswith(('.shp', '.gpkg')):
        return gpd.read_file(file)
    else:
        raise ValueError("Please enter .shp or .gpkg file")
