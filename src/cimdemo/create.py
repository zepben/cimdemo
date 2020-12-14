#  Copyright 2020 Zeppelin Bend Pty Ltd
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at https://mozilla.org/MPL/2.0/.

import argparse
import asyncio
import logging

from zepben.evolve import NetworkService, DiagramService, Breaker, Terminal, AcLineSegment, EnergySource, EnergyConsumer, PerLengthSequenceImpedance, \
    PhaseCode, EnergyConsumerPhase, SinglePhaseKind, DiagramObject, Diagram, DiagramObjectPoint, DiagramObjectStyle, DiagramStyle, connect_async, ProducerClient

logger = logging.getLogger(__name__)


def create_feeder():
    network = NetworkService()
    diagram_service = DiagramService()

    cn = network.add_connectivitynode('cn0')
    fcb = Breaker(mrid='fcb')
    t0 = Terminal(mrid='fcb-t0', phases=PhaseCode.ABCN, connectivity_node=cn, conducting_equipment=fcb)
    network.add(t0)

    cn.add_terminal(t0)
    feeder_cn = network.add_connectivitynode('fcn')

    t1 = Terminal(mrid='fcb-t1', phases=PhaseCode.ABCN, connectivity_node=feeder_cn, conducting_equipment=fcb)
    fcb.add_terminal(t0)
    fcb.add_terminal(t1)

    network.add(t1)
    network.add(fcb)

    acls0 = AcLineSegment(mrid='acls0')
    t0 = Terminal(mrid='acls0-t0', phases=PhaseCode.ABCN, connectivity_node=feeder_cn, conducting_equipment=acls0)
    acls0.add_terminal(t0)
    network.add(t0)
    cn = network.add_connectivitynode('cn1')
    t1 = Terminal(mrid='acls0-t1', phases=PhaseCode.ABCN, connectivity_node=cn, conducting_equipment=acls0)
    acls0.add_terminal(t1)
    network.add(t1)
    network.add(acls0)

    es = EnergySource(mrid='es')
    t0 = Terminal(mrid='es-t0', phases=PhaseCode.ABCN, connectivity_node=cn, conducting_equipment=es)
    es.add_terminal(t0)
    network.add(t0)
    network.add(es)

    diagram = Diagram(mrid='diag', diagram_style=DiagramStyle.GEOGRAPHIC)
    do = DiagramObject(diagram=diagram, diagram_object_points=[DiagramObjectPoint(5.0, 10.0)], style=DiagramObjectStyle.ENERGY_SOURCE)
    diagram.add_object(do)
    diagram_service.add(diagram)
    diagram_service.add(do)

    plsi0 = PerLengthSequenceImpedance(mrid='1814', r=0.000151, x=0.003, r0=0, x0=0, bch=0)
    acls1 = AcLineSegment(mrid='acls1', per_length_sequence_impedance=plsi0)
    t0 = Terminal(mrid='acls1-t0', phases=PhaseCode.ABCN, connectivity_node=feeder_cn, conducting_equipment=acls1)
    network.add(t0)
    acls1.add_terminal(t0)
    cn = network.add_connectivitynode('cn2')
    t1 = Terminal(mrid='acls1-t1', phases=PhaseCode.ABCN, connectivity_node=cn, conducting_equipment=acls1)
    acls1.add_terminal(t1)
    network.add(t1)
    network.add(plsi0)
    network.add(acls1)

    ec = EnergyConsumer(mrid='ec')
    ecp_b = EnergyConsumerPhase(mrid='spkb', phase=SinglePhaseKind.B, energy_consumer=ec)
    ecp_n = EnergyConsumerPhase(mrid='spkn', phase=SinglePhaseKind.N, energy_consumer=ec)
    ec.add_phase(ecp_b)
    ec.add_phase(ecp_n)
    t0 = Terminal(mrid='ec-t0', phases=PhaseCode.BN, connectivity_node=cn, conducting_equipment=ec)
    ec.add_terminal(t0)
    network.add(t0)
    network.add(ecp_b)
    network.add(ecp_n)
    network.add(ec)

    return network, diagram_service


async def main():
    parser = argparse.ArgumentParser(description="Zepben cimbend demo")
    parser.add_argument('server', help='Host and port of grpc server', metavar="host:port", nargs="?", default="localhost")
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
        logger.warning(f"Using an insecure connection as at least one of (--ca, --token, --cert, --key) was not provided.")
    else:
        with open(args.key, 'rb') as f:
            key = f.read()
        with open(args.ca, 'rb') as f:
            ca = f.read()
        with open(args.cert, 'rb') as f:
            cert = f.read()
        client_secret = args.client_secret
        client_id = args.client_id

    services = create_feeder()

    async with connect_async(host=args.server, rpc_port=args.rpc_port, conf_address=args.conf_address,
                             client_id=client_id, client_secret=client_secret, pkey=key, cert=cert, ca=ca) as channel:
        client = ProducerClient(channel=channel)
        res = await client.send(services)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
