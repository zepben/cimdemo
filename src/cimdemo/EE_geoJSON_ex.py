# This example illustates how to ingest and send to the cimcap server a network from a .geojon file.
import zepben.cimbend as cim
from zepben.cimbend.streaming.connect import connect_async
import geopandas as gp
from tkinter import filedialog
from tkinter import *
import logging
import asyncio
import argparse
import pydash
import json
import os

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def get_path():
    root = Tk()
    root.filename = filedialog.askopenfilename(initialdir="F:\\Data\\EssentialEnergy\\geojson", title="Select file",
                                               filetypes=(("jpeg files", "*.geojson"), ("all files", "*.*")))
    return root.filename


def read_mapping(path):
    # Opening JSON file
    file = open(path, "r")
    # returns JSON object as a dictionary
    return json.loads(file.read())["mappings"]


def read_json_file(path):
    # Opening JSON file
    file = open(path, "r")
    # returns JSON object as a dictionary
    return json.loads(file.read())


def add_list_to_net(l, net):
    return net


class Network:

    def __init__(self):
        #self.path = get_path()
        self.path = "F:\\Data\\EssentialEnergy\\geojson\\GOG3B2.geojson"
        self.geojson_file = read_json_file(self.path)
        self.mapping = read_mapping('nodes-config_ee.json')
        self.feeder_name = os.path.basename(self.path)
        self.gdf = gp.read_file(self.path)
        self.ns = cim.NetworkService()
        self.ds = cim.DiagramService()

        self.voltages = self.add_base_voltages()

    def get_cim_class(self, gis_class):
        matched_mapping = pydash.collections.find(self.mapping, lambda mapping: mapping["gisClass"] == gis_class)
        if matched_mapping is not None:
            return matched_mapping["cimClass"]

    def add_diagram(self):
        diagram = cim.Diagram(diagram_style=cim.DiagramStyle.GEOGRAPHIC)
        self.ds.add(diagram)
        return diagram

    def add_location(self, row):
        loc = cim.Location()
        for coord in row["geometry"].coords:
            logger.info("Creating coordinates: " + coord.__str__())
            loc.add_point(cim.PositionPoint(coord[0], coord[1]))
            logger.info('Add Location to Network Service')
            self.ns.add(loc)
        return loc

    def add_base_voltages(self):
        voltages = {'Service': cim.BaseVoltage(nominal_voltage=415, name='415V'),
                    'LV': cim.BaseVoltage(nominal_voltage=415, name='415V'),
                    '11kV': cim.BaseVoltage(nominal_voltage=11000, name='11kV'),
                    'UNKNOWN': cim.BaseVoltage(name='UNKNOWN')}
        for e in voltages.values():
            self.ns.add(e)
        return voltages

    def create_equipment(self, row, loc):
        class_name = self.get_cim_class(row['class'])
        if class_name is not None:
            logger.info("Creating CIM Class: " + class_name)
            class_ = getattr(cim, class_name)
            eq = class_()
            logger.info('Mapping Operating Voltage: ' + self.voltages.get(row['operating voltage'],
                                                                          self.voltages.get('UNKNOWN')).__str__())
            logger.info('Creating Equipment:' + ", mRID: " + eq.mrid.__str__())
            eq.mrid = row["id"]
            eq.name = row["name"]
            eq.base_voltage = self.voltages.get(row['operating voltage'])
            eq.location = loc
        else:
            logger.error("GIS Class: " + row['class'] + ", is not mapped to any Evolve Profile class")
            eq = None
        return eq

    def add_feeder(self):
        fdr = cim.Feeder(name=self.feeder_name)
        for index, row in self.gdf.iterrows():
            loc = self.add_location(row)
            eq = self.create_equipment(row, loc)
            if eq is not None:
                self.ns.add(eq)
                fdr.add_equipment(eq)
            else:
                logger.error("Equipment not mapped to a Evolve Profile class: " + row["id"])
        self.connect_equipment()
        self.ns.add(fdr)
        return self.ns

    def connect_equipment(self):
        gdf_b = self.gdf[self.gdf['geometry'].apply(lambda x: x.type == 'LineString')]
        for index, row in gdf_b.iterrows():
            if row['fromNode'] is not None:
                logger.info("Connecting: " + self.ns.get(mrid=row['id']).__str__() + " to " + self.ns.get(mrid=row["fromNode"]).__str__())
                logger.info("Connecting: " + row['id'] + " to " + self.ns.get(mrid=row['toNode']).__str__())
                eq0 = self.ns.get(mrid=row['id'])
                t01 = cim.Terminal(conducting_equipment=eq0)
                t02 = cim.Terminal(conducting_equipment=eq0)
                eq0.add_terminal(t01)
                eq0.add_terminal(t02)
                eq1 = self.ns.get(mrid=row["fromNode"])
                t11 = cim.Terminal(conducting_equipment=eq1)
                eq1.add_terminal(t11)
                eq2 = self.ns.get(mrid=row["toNode"])
                t21 = cim.Terminal(conducting_equipment=eq2)
                eq2.add_terminal(t21)
                self.ns.add(t01)
                self.ns.add(t11)
                self.ns.add(t02)
                self.ns.add(t21)
                self.ns.connect_terminals(t01,t11)
                self.ns.connect_terminals(t02,t21)




async def main():
    parser = argparse.ArgumentParser(description="Zepben cimbend demo for geoJSON ingestion")
    parser.add_argument('server', help='Host and port of grpc server', metavar="host:port", nargs="?",
                        default="localhost")
    parser.add_argument('--rpc-port', help="The gRPC port for the server", default="50051")
    parser.add_argument('--conf-address', help="The address to retrieve auth configuration from",
                        default="http://localhost/auth")
    parser.add_argument('--client-id', help='Auth0 M2M client id', default="")
    parser.add_argument('--client-secret', help='Auth0 M2M client secret', default="")
    parser.add_argument('--ca', help='CA trust chain', default="")
    parser.add_argument('--cert', help='Signed certificate for your client', default="")
    parser.add_argument('--key', help='Private key for signed cert', default="")
    args = parser.parse_args()
    ca = cert = key = client_id = client_secret = None
    if not args.client_id or not args.client_secret or not args.ca or not args.cert or not args.key:
        logger.warning(
            f"Using an insecure connection as at least one of (--ca, --token, --cert, --key) was not provided.")
    else:
        with open(args.key, 'rb') as f:
            key = f.read()
        with open(args.ca, 'rb') as f:
            ca = f.read()
        with open(args.cert, 'rb') as f:
            cert = f.read()
        client_secret = args.client_secret
        client_id = args.client_id
    # Creates a Network
    network = Network().add_feeder()

    # Connect to a local postbox instance using credentials if provided.
    async with connect_async(host=args.server, rpc_port=args.rpc_port, conf_address=args.conf_address,
                             client_id=client_id, client_secret=client_secret, pkey=key, cert=cert, ca=ca) as conn:
        # Send the network to the postbox instance.
        res = await conn.send([network])


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
