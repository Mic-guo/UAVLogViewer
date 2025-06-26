from pymavlink import mavutil
import json
import numpy as np
import gzip

logfile = "arenaTest.bin"
m = mavutil.mavlink_connection(logfile)

data_by_type = {}

def make_json_safe(obj):
    if isinstance(obj, bytes):
        return obj.decode(errors="ignore")
    elif isinstance(obj, (list, tuple)):
        return [make_json_safe(i) for i in obj]
    elif isinstance(obj, dict):
        return {k.lower(): make_json_safe(v) for k, v in obj.items()}
    elif hasattr(obj, 'tolist'):
        return obj.tolist()
    elif isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    return obj

while True:
    msg = m.recv_match(blocking=False)
    if msg is None:
        break
    msg_dict = make_json_safe(msg.to_dict())
    msg_type = msg.get_type().lower()
    if msg_type not in data_by_type:
        data_by_type[msg_type] = []
    data_by_type[msg_type].append(msg_dict)

with gzip.open("parsed_arenaTest.json.gz", "wt", encoding="utf-8") as f:
    json.dump(data_by_type, f, indent=2)
