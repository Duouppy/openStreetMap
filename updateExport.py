import xml.etree.cElementTree as ET
from collections import defaultdict
import re
import pprint
import audit
import codecs
import json


osm = 'tampa.xml'


lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
street_types = re.compile(r'\b\S+\.?$', re.IGNORECASE)


CREATED = ["version", "changeset", "timestamp", "user", "uid"]
ATTRIB = ["id", "visible", "amenity", "cuisine", "name", "phone"]


expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road", 
            "Trail", "Parkway", "Commons", "Plaza", "Highway", "Circle", "North", "South", "East", "West", "Way", "Run"]


street_type_mapping = { "St": "Street",
                       "Ave": "Avenue",
                       "Blvd": "Boulevard",
                       "Rd": "Road",
                       "drive": "Drive",
                       "Dr": "Drive",
                       "Pl": "Place",
                       "Av": "Avenue",
                       "W": "West",
                       "Pky": "Parkway",
                       "Ct": "Court",
                       "Ave.": "Avenue",
                       "Hwy": "Highway",
                       "Boulvard": "Boulevard",
                       "Pkwy": "Parkway",
                       "dr": "Drive",
                       "Bldv.": "Boulevard",
                       "Bolevard": "Boulevard"
                      } 


#iterates through OSM file to identify correct and incorrect street mappings. This will return corrected values of street types. This is only used for validation. Won't be used in the shaping method.
def fix_street(osmfile):
    st_types = audit.audit(osmfile)
    for st_type, ways in st_types.items():
        for name in ways:
            if st_type in street_type_mapping:
                better_name = name.replace(st_type, street_type_mapping[st_type])
                print (name, "=>", better_name)
				
#updates the street names of values in key value pairs to match correct mappings. to be used in production/shape_element function.
def update_street_name(value):
    m = audit.street_type_re.search(value)
    if m:
        if m.group() in street_type_mapping:
            startpos = value.find(m.group())
            value = value[:startpos] + street_type_mapping[m.group()]
        return value
    else:
        return None


#runs an audit of the street types in kv pairs returned and returns an updated name. 
def audit_street_type(street_name):
    match = street_types.search(street_name)
    if match:
        street_type = match.group()
        if street_type not in expected:
            return update_street_name(street_name)


#validates that returned tags to be saved are streets.
def is_street_name(address_key):
    return address_key == 'addr:street'    
    

#updates the value of the street name if inconsistency is identified.                       
def update_value(value, key):
    if key == "addr:street":
        return update_street_name(value)
    else:
        return value



def shape_element(element):
    """
    Parse, validate and format node and way xml elements.
    Return list of dictionaries
    Keyword arguments:
    element -- element object from xml element tree iterparse
    """
    node = {}
    if element.tag == "node" or element.tag == "way" :
        node['type'] = element.tag
        #parse attributes
        for a in element.attrib:
            if a in CREATED:
                if 'created' not in node:
                    node['created'] = {}
                node['created'][a] = element.attrib[a]
            #adds position array for dictionary
            elif a in ['lat', 'lon']:
                if 'pos' not in node:
                    node['pos'] = [None, None]
                if a == 'lat':
                    node['pos'][0] = float(element.attrib[a])
                else:
                    node['pos'][1] = float(element.attrib[a])
            else:
                node[a] = element.attrib[a]
        #iterate tag children
        for tag in element.iter("tag"):
            k = tag.attrib['k']
            v = tag.attrib['v']
            #searches for problem characters & colons in address attributes
            if not problemchars.search(tag.attrib['k']):
                if lower_colon.search(tag.attrib['k']):
                    if tag.attrib['k'].find('addr') == 0:
                        if 'address' not in node:
                            node['address'] = {}
                        #validates and corrects street names to be exported and used for queries    
                        if is_street_name(k):
                            v = audit_street_type(v)
                        sub_attr = tag.attrib['k'].split(':', 1)
                        node['address'][sub_attr[1]] = tag.attrib['v']
                    #single colon attributes processed normally    
                    else:
                        node[tag.attrib['k']] = tag.attrib['v']
                elif tag.attrib['k'].find(':') == -1:
                    node[tag.attrib['k']] = tag.attrib['v']
            #iterate nd children        
            for nd in element.iter("nd"):
                if 'node_refs' not in node:
                    node['node_refs'] = []
                node['node_refs'].append(nd.attrib['ref'])    
        return node
    else:
        return None


'''this function utilizes the previously built functions to interate 
through the xml document and export the information, after correction, 
into a json document to be imported by mongoDB.'''
def process_map(file_in, pretty=False):
    file_out = "{0}.json".format(file_in)
    data = []
    with codecs.open(file_out, "w") as fo:
        for _, element in ET.iterparse(file_in):
            el = shape_element(element)
            if el:
                data.append(el)
                if pretty:
                    fo.write(json.dumps(el, indent=2) + "\n")
                else:
                    fo.write(json.dumps(el) + "\n")

    return data


#fix_street(osm)
#process_map(osm)