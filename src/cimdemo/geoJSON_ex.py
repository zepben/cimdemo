import zepben.cimbend as cim
from zepben.cimbend.streaming.connect import connect_async
import geopandas as gp
from zepben.cimbend import PowerTransformer
from tkinter import filedialog
from tkinter import *
import logging
import asyncio
import argparse

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_path(self):
    root = Tk()
    root.filename = filedialog.askopenfilename(initialdir="F:\\Data\\EssentialEnergy\\geojson", title="Select file",
                                               filetypes=(("jpeg files", "*.geojson"), ("all files", "*.*")))
    return root.filename


def add_list_to_net(l, net):
    return net


class Network:

    def __init__(self):
        # self.path = get_path()
        self.path = "F:\\Data\\EssentialEnergy\\geojson\\GOG3B2.geojson"
        self.df = gp.read_file(self.path)
        self.ns = cim.NetworkService()
        self.ds = cim.DiagramService()
        self.diagram = self.add_diagram()
        self.voltages = self.add_base_voltages()
        self.add_equipments()
        # self.ds.add(self.diagram)

    def add_diagram(self):
        diagram = cim.Diagram(mrid='diag', diagram_style=cim.DiagramStyle.GEOGRAPHIC)
        # self.ds.add(diagram)
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
        voltages = {'Service': cim.BaseVoltage(nominal_voltage=11000, name='11kV'),
                    'LV': cim.BaseVoltage(nominal_voltage=440, name='440V'),
                    '11KV': cim.BaseVoltage(nominal_voltage=440, name='440V'),
                    'UNKNOWN': cim.BaseVoltage(name='UNKNOWN')}
        for e in voltages.values():
            self.ns.add(e)
        return voltages

    def add_equipments(self):
        for index, row in self.df.iterrows():
            loc = self.add_location(row)
            if row['class'] == 'cable':
                acls = cim.AcLineSegment(name=row["id"], description=row["name"], length=row["length"], location=loc)
                logger.info('Mapping Operating Voltage: ' + self.voltages.get(row['operating voltage'],
                                                                              self.voltages.get('UNKNOWN')).__str__())
                logger.info('Creating ACLS: ' + acls.mrid.__str__())
                self.ns.add(acls)
            if row['class'] == 'transformer':
                tx = PowerTransformer(name=row["id"], description=row["name"], location=loc)
                logger.info('Creating PowerTranformer: ' + tx.mrid.__str__())
                self.ns.add(tx)
                do = cim.DiagramObject(diagram=self.diagram, identified_object_mrid=tx.mrid,
                                       style=cim.DiagramObjectStyle.DIST_TRANSFORMER)
                self.diagram.add_object(do)
                self.ds.add(do)


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
    feeder = Network()
    services = feeder.ns, feeder.ds

    # Connect to a local postbox instance using credentials if provided.
    async with connect_async(host=args.server, rpc_port=args.rpc_port, conf_address=args.conf_address,
                             client_id=client_id, client_secret=client_secret, pkey=key, cert=cert, ca=ca) as conn:
        # Send the network to the postbox instance.
        res = await conn.send(services)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
