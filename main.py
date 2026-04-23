import os

import geopandas as gpd
import pandas as pd
from shapely.ops import substring, linemerge
from shapely.geometry import MultiLineString


def read_shapefile(path):
    if not path.lower().endswith(('.shp', '.gpkg')):
        raise ValueError("Shapefile must be a .shp or .gpkg file")
    return gpd.read_file(path)


def read_csv(path):
    if not path.lower().endswith('.csv'):
        raise ValueError("CSV file must have a .csv extension")
    df = pd.read_csv(path)
    if 'OBJECTID' not in df.columns:
        raise ValueError("CSV must contain an 'OBJECTID' column")
    if 'start' not in df.columns or 'end' not in df.columns:
        raise ValueError("CSV must contain 'start' and 'end' columns")
    df['OBJECTID'] = df['OBJECTID'].astype(int)
    df['start'] = pd.to_numeric(df['start'], errors='coerce')
    df['end'] = pd.to_numeric(df['end'], errors='coerce')
    return df


def merge_data(gdf, df):
    gdf = gdf.copy()
    gdf['OBJECTID'] = gdf['OBJECTID'].astype(int)
    merged = df.merge(gdf[['OBJECTID', 'geometry']], on='OBJECTID', how='inner')
    if merged.empty:
        raise ValueError("No matching OBJECTID values found between shapefile and CSV")
    return gpd.GeoDataFrame(merged, geometry='geometry', crs=gdf.crs)


def to_linestring(geom):
    if isinstance(geom, MultiLineString):
        merged = linemerge(geom)
        return merged
    return geom


def extract_chainage_segments(merged_gdf):
    rows = []
    skipped = 0
    for _, row in merged_gdf.iterrows():
        line = to_linestring(row.geometry)
        start = row['start']
        end = row['end']

        if pd.isna(start) or pd.isna(end):
            skipped += 1
            continue

        if isinstance(line, MultiLineString):
            print(f"  Warning: OBJECTID {row.get('OBJECTID', '?')} has disconnected line parts — skipping")
            skipped += 1
            continue

        line_length = line.length
        start = max(0.0, min(float(start), line_length))
        end = max(0.0, min(float(end), line_length))

        if start >= end:
            skipped += 1
            continue

        segment = substring(line, start, end)
        data = row.drop('geometry').to_dict()
        data['geometry'] = segment
        rows.append(data)

    if skipped:
        print(f"  {skipped} rows skipped (disconnected geometry, invalid start/end, or NaN values)")

    if not rows:
        raise ValueError("No valid chainage segments could be created")

    return gpd.GeoDataFrame(rows, geometry='geometry', crs=merged_gdf.crs)


def save_output(gdf, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    out_path = os.path.join(output_folder, 'chainage_output.shp')
    gdf.to_file(out_path)
    print(f"Saved {len(gdf)} segments to: {out_path}")


def main():
    shapefile_path = input("Enter the path to the shapefile or GeoPackage (.shp / .gpkg): ").strip()
    csv_path = input("Enter the path to the CSV file: ").strip()
    output_folder = input("Enter the output folder path: ").strip()

    print("\nReading shapefile...")
    gdf = read_shapefile(shapefile_path)

    print("Reading CSV...")
    df = read_csv(csv_path)

    print("Merging on OBJECTID...")
    merged = merge_data(gdf, df)
    print(f"  {len(merged)} rows matched")

    print("Extracting chainage segments...")
    segments = extract_chainage_segments(merged)
    print(f"  {len(segments)} segments created")

    save_output(segments, output_folder)


if __name__ == '__main__':
    main()
