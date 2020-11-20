import zepben.cimbend as cim
from zepben.cimbend.streaming.connect import connect_async
import geopandas as gp
from zepben.cimbend import PowerTransformer
from tkinter import filedialog
from tkinter import *
import logging
import asyncio
import argparse
import pydash
import json

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_path(self):
    root = Tk()
    root.filename = filedialog.askopenfilename(initialdir="F:\\Data\\EssentialEnergy\\geojson", title="Select file",
                                               filetypes=(("jpeg files", "*.geojson"), ("all files", "*.*")))
    return root.filename


def read_mapping(path):
    # Opening JSON file
    file = open(path, "r")
    # returns JSON object as a dictionary
    return json.loads(file.read())["mappings"]


def add_list_to_net(l, net):
    return net


class Network:

    def __init__(self):
        # self.path = get_path()
        self.path = "F:\\Data\\EssentialEnergy\\geojson\\GOG3B2.geojson"
        self.mapping = read_mapping('nodes-config_ee.json')
        self.df = gp.read_file(self.path)
        self.ns = cim.NetworkService()
        self.ds = cim.DiagramService()
        self.diagram = self.add_diagram()
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
            eq.name = row["id"]
            eq.base_voltage = self.voltages.get(row['operating voltage'])
            eq.location = loc
            logger.info('Mapping Operating Voltage: ' + self.voltages.get(row['operating voltage'],
                                                                          self.voltages.get('UNKNOWN')).__str__())
            logger.info('Creating Equipment:' + ", mRID: " + eq.mrid.__str__())
        else:
            logger.error("GIS Class: " + row['class'] + ", is not mapped to any Evolve Profile class")
            eq = None
        return eq

    def create_network(self):
        for index, row in self.df.iterrows():
            loc = self.add_location(row)
            eq = self.create_equipment(row, loc)
            if eq is not None:
                self.ns.add(eq)
            else:
                logger.error("Equipment not mapped to a Evolve Profile class: " + row["id"])
                # TODO: Support creation of DiagramObjects and add to a Diagram Service such that the can be visualized in the Network Map
                # The cimbend libary is generating a error with self.diagram.add_object(do)
                # do = cim.DiagramObject(diagram=self.diagram, identified_object_mrid=tx.mrid,
                #                       style=cim.DiagramObjectStyle.DIST_TRANSFORMER)
                # self.diagram.add_object(do)
                # self.ds.add(do)
        return self.ns


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
    network = Network().create_network()
    # Connect to a local postbox instance using credentials if provided.
    async with connect_async(host=args.server, rpc_port=args.rpc_port, conf_address=args.conf_address,
                             client_id=client_id, client_secret=client_secret, pkey=key, cert=cert, ca=ca) as conn:
        # Send the network to the postbox instance.
        res = await conn.send([network])


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
