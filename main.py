import argparse
import os

import geopandas as gpd
import pandas as pd
from shapely.ops import substring


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


def extract_chainage_segments(merged_gdf):
    rows = []
    for _, row in merged_gdf.iterrows():
        line = row.geometry
        start = row['start']
        end = row['end']

        if pd.isna(start) or pd.isna(end):
            continue

        line_length = line.length
        # clamp to line bounds
        start = max(0.0, min(float(start), line_length))
        end = max(0.0, min(float(end), line_length))

        if start >= end:
            continue

        segment = substring(line, start, end)
        data = row.drop('geometry').to_dict()
        data['geometry'] = segment
        rows.append(data)

    if not rows:
        raise ValueError("No valid chainage segments could be created")

    return gpd.GeoDataFrame(rows, geometry='geometry', crs=merged_gdf.crs)


def save_output(gdf, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    out_path = os.path.join(output_folder, 'chainage_output.shp')
    gdf.to_file(out_path)
    print(f"Saved {len(gdf)} segments to: {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate chainage segments by merging a CSV with a shapefile on OBJECTID'
    )
    parser.add_argument('-s', '--shapefile', required=True,
                        help='Path to input shapefile (.shp) or GeoPackage (.gpkg)')
    parser.add_argument('-c', '--csv', required=True,
                        help='Path to CSV file containing OBJECTID, start, and end columns')
    parser.add_argument('-o', '--output', required=True,
                        help='Path to output folder where the result shapefile will be saved')
    args = parser.parse_args()

    print("Reading shapefile...")
    gdf = read_shapefile(args.shapefile)

    print("Reading CSV...")
    df = read_csv(args.csv)

    print("Merging on OBJECTID...")
    merged = merge_data(gdf, df)
    print(f"  {len(merged)} rows matched")

    print("Extracting chainage segments...")
    segments = extract_chainage_segments(merged)
    print(f"  {len(segments)} segments created")

    save_output(segments, args.output)


if __name__ == '__main__':
    main()
