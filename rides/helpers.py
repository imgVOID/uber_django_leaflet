def transform_points_to_linestring(feature_collection):
    """
    Перетворює FeatureCollection з Point у FeatureCollection з одним LineString
    """
    features = feature_collection.get("features", [])
    if not features:
        return feature_collection

    # Витягуємо всі координати з точок
    coordinates = [f["geometry"]["coordinates"] for f in features if f["geometry"]["type"] == "Point"]
    
    # Створюємо нову структуру
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates
            },
            "properties": {"total_points": len(coordinates)}
        }]
    }
