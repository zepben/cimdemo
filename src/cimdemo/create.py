"""
Copyright 2019 Zeppelin Bend Pty Ltd
This file is part of cimdemo.

cimdemo is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

cimdemo is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with cimdemo.  If not, see <https://www.gnu.org/licenses/>.
"""

import argparse
import asyncio
import logging

from zepben.cimbend import NetworkService, Breaker, Terminal, AcLineSegment, EnergySource, \
    EnergyConsumer, PerLengthSequenceImpedance, PhaseCode, EnergyConsumerPhase, SinglePhaseKind
from zepben.cimbend.streaming.connect import connect_async

logger = logging.getLogger(__name__)


def create_feeder():
    network = NetworkService()
    cn = network.add_connectivitynode('cn0')
    t0 = Terminal(mrid='fcb-t0', phases=PhaseCode.ABCN, connectivitynode=cn)
    network.add(t0)
    cn.add_terminal(t0)
    feeder_cn = network.add_connectivitynode('fcn')
    t1 = Terminal(mrid='fcb-t1', phases=PhaseCode.ABCN, connectivitynode=feeder_cn)
    network.add(t1)
    fcb = Breaker(mrid='fcb', terminals_=[t0, t1])
    network.add(fcb)

    t0 = Terminal(mrid='acls0-t0', phases=PhaseCode.ABCN, connectivitynode=feeder_cn)
    network.add(t0)
    cn = network.add_connectivitynode('cn1')
    t1 = Terminal(mrid='acls0-t1', phases=PhaseCode.ABCN, connectivitynode=cn)
    network.add(t1)
    acls0 = AcLineSegment(mrid='acls0', terminals_=[t0, t1])
    network.add(acls0)

    t0 = Terminal(mrid='es-t0', phases=PhaseCode.ABCN, connectivitynode=cn)
    network.add(t0)
    es = EnergySource(mrid='es', terminals_=[t0])
    network.add(es)

    t0 = Terminal(mrid='acls1-t0', phases=PhaseCode.ABCN, connectivitynode=feeder_cn)
    network.add(t0)
    cn = network.add_connectivitynode('cn2')
    t1 = Terminal(mrid='acls1-t1', phases=PhaseCode.ABCN, connectivitynode=cn)
    network.add(t1)
    plsi0 = PerLengthSequenceImpedance(mrid='1814', r=0.000151, x=0.003, r0=0, x0=0, bch=0)
    network.add(plsi0)
    acls1 = AcLineSegment(mrid='acls1', per_length_sequence_impedance=plsi0, terminals_=[t0, t1])
    network.add(acls1)

    t0 = Terminal(mrid='ec-t0', phases=PhaseCode.BN, connectivitynode=cn)
    network.add(t0)
    ecp_b = EnergyConsumerPhase(mrid='spkb', phase=SinglePhaseKind.B)
    network.add(ecp_b)
    ecp_n = EnergyConsumerPhase(mrid='spkn', phase=SinglePhaseKind.N)
    network.add(ecp_n)
    ec = EnergyConsumer(mrid='ec', energyconsumerphases=[ecp_b, ecp_n], terminals_=[t0])
    network.add(ec)

    return network


async def main():
    parser = argparse.ArgumentParser(description="Zepben cimbend demo")
    parser.add_argument('server', help='Host and port of grpc server', metavar="host:port", nargs="?", default="localhost:50051")
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

    network = create_feeder()

    async with connect_async(host="postbox.localdomain", conf_port=8080, client_id=client_id, client_secret=client_secret, pkey=key, cert=cert, ca=ca) as conn:
        res = await conn.send([network])
        # network = await conn.get_whole_network()
        # print(network['es'])


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
