
#  Copyright 2020 Zeppelin Bend Pty Ltd
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at https://mozilla.org/MPL/2.0/.

#### NOTE - THIS EXAMPLE IS CURRENTLY BROKEN ####

# import asyncio
# import argparse
# import contextlib
# import grpc
# import logging
# import plotly.graph_objects as go
# from zepben.cimbend import PowerTransformer
# from zepben.cimbend.streaming.connect import connect_async
# from zepben.cimbend.tracing import ConductingEquipmentToCores
# from zepben.cimbend.tracing import Traversal, SearchType, queue_next_equipment
# from zepben.cimbend.plot import extract_latlongs
# from zepben.cimbend.tracing import normal_downstream_trace
#
# logger = logging.getLogger(__name__)
# CA_CERT = None
# CERT = None
# KEY = None
#
#
# @contextlib.contextmanager
# def create_client_channel(addr, token, secure=False):
#     if secure:
#         call_credentials = grpc.access_token_call_credentials(token)
#         # Channel credential will be valid for the entire channel
#         channel_credentials = grpc.ssl_channel_credentials(CA_CERT, KEY, CERT)
#         # Combining channel credentials and call credentials together
#         composite_credentials = grpc.composite_channel_credentials(
#             channel_credentials,
#             call_credentials,
#         )
#         channel = grpc.secure_channel(addr, composite_credentials)
#     else:
#         channel = grpc.insecure_channel(addr)
#
#     yield channel
#
#
# async def count_customers(network):
#     customer_count = [0]
#
#     async def count_customer(item, _):
#         if item.is_metered():
#             customer_count[0] += 1
#
#     start_item = network.get_primary_sources()[0]
#     trace = Traversal(queue_next=queue_next_equipment, start_item=start_item, search_type=SearchType.DEPTH, step_actions=[count_customer])
#     await trace.trace()
#     print(f"Total Customers: {customer_count[0]}")
#     customer_count[0] = 0
#
#
# async def count_lengths(network):
#     length = [0]
#
#     async def count_length(item, _):
#         try:
#             length[0] += item.length
#         except AttributeError:
#             pass
#     start_item = network.get_primary_sources()[0]
#     trace = Traversal(queue_next=queue_next_equipment, start_item=start_item, search_type=SearchType.DEPTH, step_actions=[count_length])
#     await trace.trace()
#     print(f"Total length of the network: {length[0] / 1000.0:.3f}km")
#
#
# async def calc_connected_kva(start_point, end_point):
#     kva = [0]
#
#     async def count_kva(item, _):
#         try:
#             if isinstance(item.equipment, PowerTransformer):
#                 kva[0] += item.r
#         except AttributeError:
#             pass
#
#     async def stop_on(item):
#         if item.equipment is end_point:
#             return True
#         return False
#
#     trace = normal_downstream_trace()
#     trace.add_step_action(count_kva)
#     trace.add_stop_condition(stop_on)
#     await trace.trace(start_item=ConductingEquipmentToCores(start_point, from_count(start_point.num_cores)), can_stop_on_start_item=False)
#     print(f"Total kVA: {kva[0]}")
#
#
# async def plot(network):
#     latlongs = await extract_latlongs(network)
#     fig = go.Figure(go.Scattermapbox(
#         mode="markers+lines",
#         marker={'size':  3}))
#
#     fig.add_trace(go.Scattermapbox(
#         mode="markers+lines",
#         lon=[ll.long for ll in latlongs],
#         lat=[ll.lat for ll in latlongs],
#         marker={'size':  3}))
#
#     fig.update_layout(
#         margin={'l': 0, 't': 0, 'b': 0, 'r': 0},
#         mapbox={
#             'style':  "stamen-terrain",
#             'center':  {'lon': 145.263300, 'lat': -38.06088},
#             'zoom':  13})
#
#     fig.show()
#
#
# async def main():
#     parser = argparse.ArgumentParser(description="Zepben cimbend demo")
#     parser.add_argument('server', help='Host and port of grpc server', metavar="host:port", nargs="?", default="localhost:50051")
#     parser.add_argument('--client-id', help='Auth0 M2M client id', default="")
#     parser.add_argument('--client-secret', help='Auth0 M2M client secret', default="")
#     parser.add_argument('--ca', help='CA trust chain', default="")
#     parser.add_argument('--cert', help='Signed certificate for your client', default="")
#     parser.add_argument('--key', help='Private key for signed cert', default="")
#     args = parser.parse_args()
#     ca = cert = key = client_id = client_secret = None
#     if not args.client_id or not args.client_secret or not args.ca or not args.cert or not args.key:
#         logger.warning(f"Using an insecure connection as at least one of (--ca, --token, --cert, --key) was not provided.")
#     else:
#         with open(args.key, 'rb') as f:
#             key = f.read()
#         with open(args.ca, 'rb') as f:
#             ca = f.read()
#         with open(args.cert, 'rb') as f:
#             cert = f.read()
#         client_secret = args.client_secret
#         client_id = args.client_id
#
#     async with connect_async(host="postbox.localdomain", conf_port=8080, client_id=client_id, client_secret=client_secret, pkey=key, cert=cert, ca=ca) as conn:
#         network = await conn.get_whole_network()
#         await network.set_phases()
#         await count_customers(network)
#         await count_lengths(network)
#         await calc_connected_kva(network["1"], network["7512"])
#         await plot(network)
#
#
# if __name__ == "__main__":
#     loop = asyncio.get_event_loop()
#     loop.run_until_complete(main())
