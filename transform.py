#!/usr/bin/env python
import json
import os
from urllib.parse import quote

import pandas as pd
from diskcache import Index
from feedgen.feed import FeedGenerator
from geopy.exc import GeocoderTimedOut
from geopy.geocoders import GoogleV3
from geopy.point import Point


def iri_to_uri(iri):
    """
    Convert an Internationalized Resource Identifier (IRI) portion to a URI
    portion that is suitable for inclusion in a URL.

    This is the algorithm from section 3.1 of RFC 3987, slightly simplified
    since the input is assumed to be a string rather than an arbitrary byte
    stream.

    Take an IRI (string or UTF-8 bytes, e.g. '/I ♥ Django/' or
    b'/I \xe2\x99\xa5 Django/') and return a string containing the encoded
    result with ASCII chars only (e.g. '/I%20%E2%99%A5%20Django/').

    Copyright (c) Django Software Foundation and individual contributors.
    All rights reserved.
    """
    # The list of safe characters here is constructed from the "reserved" and
    # "unreserved" characters specified in sections 2.2 and 2.3 of RFC 3986:
    #     reserved    = gen-delims / sub-delims
    #     gen-delims  = ":" / "/" / "?" / "#" / "[" / "]" / "@"
    #     sub-delims  = "!" / "$" / "&" / "'" / "(" / ")"
    #                   / "*" / "+" / "," / ";" / "="
    #     unreserved  = ALPHA / DIGIT / "-" / "." / "_" / "~"
    # Of the unreserved characters, urllib.parse.quote() already considers all
    # but the ~ safe.
    # The % character is also added to the list of safe characters here, as the
    # end of section 3.1 of RFC 3987 specifically mentions that % must not be
    # converted.
    if iri is None:
        return iri
    return quote(iri, safe="/#%[]=:;$&()+,!?*@'~")


feed = {
    "id": "https://jezdez.github.io/snsz/",
    "title": "Schulschließungen oder eingeschränktem Regelbetrieb in Sachsen",
    "link": "https://jezdez.github.io/snsz/",
    "language": "de",
    "description": "Schulschließungen oder eingeschränktem Regelbetrieb in Sachsen",
    "rights": "Sächsisches Staatsministerium für Kultus, https://www.smk.sachsen.de/rechtliche-hinweise.html",
}

# the bbox for making sure the geocoder does the right thing
saxony_bbox = (
    Point(11.8723081683, 50.1715419914),
    Point(15.0377433357, 51.6831408995),
)
google_geocoder = GoogleV3(api_key=os.environ["GOOGLE_GEOCODE_API_KEY"])

# the file disk cache for the geocoder
cache_path = os.path.join(os.path.dirname(__file__), "cache", "geocodes")
os.makedirs(cache_path, exist_ok=True)
geocodes = Index(cache_path)


def to_feed(df):
    """Generate and return a feed item for the given data frame"""
    fg = FeedGenerator()
    fg.id(feed["id"])
    fg.title(feed["title"])
    fg.link(href=feed["link"], rel="self")
    fg.language(feed["language"])
    fg.description(feed["description"])
    fg.generator("SNSZ")
    fg.rights(feed["rights"])

    for i, row in df.iterrows():
        if not row["name"]:
            continue
        url = iri_to_uri(row["url"])
        fe = fg.add_entry(order="append")
        fe.id(url)
        fe.title(row["name"])
        fe.rights(feed["rights"])
        fe.content(
            f"""
Status: {row["status"]}
Gültig: {row["validity"]}
"""
        )
        fe.published(row["published_at"].tz_localize("utc"))
        fe.link({"href": url, "title": row["name"]})
        if url and url.endswith(".pdf"):
            fe.enclosure(url, 0, "application/pdf")
    return fg


def to_atom(df, atom_path):
    """Create an ATOM file for the given data frame"""
    fg = to_feed(df)
    fg.atom_file(atom_path, pretty=True)


def to_rss(df, rss_path):
    """Create an RSS file for the given data frame"""
    fg = to_feed(df)
    fg.rss_file(rss_path, pretty=True)


def to_geojson(json_file, geojson_path):
    """Create a GeoJSON file for the given data frame"""
    with open(json_file) as input:
        data = json.load(input)

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [item["longitude"], item["latitude"]],
                },
                "properties": item,
            }
            for item in data
        ],
    }

    with open(geojson_path, "w") as geojson_file:
        json.dump(geojson, geojson_file)


@geocodes.memoize()
def geocode(address, language="de", region="de", timeout=5):
    """
    Geocode an address using the Google Maps v3 API
    https://developers.google.com/maps/documentation/geocoding/
    """
    # https://stackoverflow.com/questions/27914648/geopy-catch-timeout-error
    try:
        location = google_geocoder.geocode(
            f"{address} sachsen",
            exactly_one=True,
            timeout=timeout,
            language=language,
            region=region,
            bounds=saxony_bbox,
        )
    except GeocoderTimedOut as err:
        print(
            f"GeocoderTimedOut: geocode timedout on input {address} with message {err.msg}"
        )
    except AttributeError as err:
        print(
            f"AttributeError: geocode failed on input {address} with message {err.msg}"
        )
    if location:
        return location
    print(f"Couldn't geocode the address: {address}")


df = pd.read_json("raw.json", orient="records")

results = []
for index, row in df.iterrows():
    try:
        name = row.loc["name"]
        to_geocode = name.lower().strip()
        location = geocode(to_geocode)
        if location is not None:
            data = {
                "index": index,
                "address": location.address,
                "latitude": location.latitude,
                "longitude": location.longitude,
            }
            if data["address"] is not None:
                results.append(data)
                print(data)
    except:
        print(row)
        continue

geo = pd.DataFrame(results)
geo.set_index("index", inplace=True)

df_geo = df.merge(geo, how="inner", left_index=True, right_index=True)

# export data frame to some files
df_geo.to_csv("website/data/schools.csv", index=False)
df_geo.to_json("website/data/schools.json", orient="records")
to_geojson("website/data/schools.json", "website/data/schools.geojson")
to_atom(df_geo, "website/data/schools.atom")
to_rss(df_geo, "website/data/schools.rss")
