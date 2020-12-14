#  Copyright 2020 Zeppelin Bend Pty Ltd
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at https://mozilla.org/MPL/2.0/.

import asyncio
import argparse
import logging

from zepben.evolve import Pole, Streetlight, StreetlightLampKind, NetworkService, connect_async, ProducerClient

logger = logging.getLogger(__name__)


def create_lightpoles() -> NetworkService:
    """
    Create a few poles with streetlights attached
    :return: NetworkService with a few poles/streetlights, no connectivity model though.
    """
    network = NetworkService()

    pole1 = Pole(mrid="pole1")
    streetlight1 = Streetlight(mrid="streetlight1", light_rating=10, lamp_kind=StreetlightLampKind.HIGH_PRESSURE_SODIUM, pole=pole1)
    pole1.add_streetlight(streetlight1)

    network.add(pole1)
    network.add(streetlight1)

    multi_light_pole = Pole(mrid="pole2")
    streetlight2 = Streetlight(mrid="streetlight2", light_rating=10, lamp_kind=StreetlightLampKind.HIGH_PRESSURE_SODIUM, pole=multi_light_pole)
    streetlight3 = Streetlight(mrid="streetlight3", light_rating=20, lamp_kind=StreetlightLampKind.MERCURY_VAPOR, pole=multi_light_pole)
    streetlight4 = Streetlight(mrid="streetlight4", light_rating=5, lamp_kind=StreetlightLampKind.UNKNOWN, pole=multi_light_pole)
    multi_light_pole.add_streetlight(streetlight2)
    multi_light_pole.add_streetlight(streetlight3)
    multi_light_pole.add_streetlight(streetlight4)
    network.add(multi_light_pole)
    network.add(streetlight2)
    network.add(streetlight3)
    network.add(streetlight4)

    return network


async def main():
    parser = argparse.ArgumentParser(description="Zepben cimbend demo for the IEEE European LV Test feeder")
    parser.add_argument('server', help='Host and port of grpc server', metavar="host:port", nargs="?",
                        default="localhost")
    parser.add_argument('--rpc-port', help="The gRPC port for the server", default="50051")
    parser.add_argument('--conf-address', help="The address to retrieve auth configuration from", default="http://localhost/auth")
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
    network = create_lightpoles()

    # Connect to a local postbox instance using credentials if provided.
    async with connect_async(host=args.server, rpc_port=args.rpc_port, conf_address=args.conf_address, client_id=client_id, client_secret=client_secret, pkey=key, cert=cert, ca=ca) as channel:
        client = ProducerClient(channel=channel)
        res = await client.send([network])



if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
