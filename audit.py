import xml.etree.cElementTree as ET
from collections import defaultdict
import re
import pprint


osm = 'tampa.xml'


street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
street_types = defaultdict(set)


expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road", 
            "Trail", "Parkway", "Commons", "Plaza", "Highway", "Circle", "North", "South", "East", "West", "Way", "Run"]


def audit_street_type(street_types, street_name):
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected:
            street_types[street_type].add(street_name)

#used to return elements that are verified to be street types in xml document tree
def is_street_name(elem):
    return (elem.attrib['k'] == "addr:street")


#used to iterate through xml document and create a dictionary of addresses that do not use uniform expected street types.
def audit(osmfile):
    osm_file = open(osmfile, "rb")
    for event, elem in ET.iterparse(osm_file, events=("start",)):
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_street_name(tag):
                    audit_street_type(street_types, tag.attrib['v'])
    osm_file.close()
    return street_types


#print(audit(osm))