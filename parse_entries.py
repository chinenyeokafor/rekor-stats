import json
import analyze_utils as util
import os
import sys
import progressbar
import pandas as pd
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
 
dataset_path = config['DEFAULT']['error_dataset_path'] 
limit = int(float(config['DEFAULT']['limit']))


print("Reading entries...", end='')
sys.stdout.flush()

total_entries = len(os.listdir(dataset_path))
widgets = [
    'Processed: ', progressbar.Percentage(), 
    ' (', progressbar.FormatLabel('%(value)d / {} lines'.format(total_entries)), 
    ' in: ', progressbar.ETA(), ')'
]
pbar = progressbar.ProgressBar(widgets=widgets, maxval=total_entries)

entries = [] 

for entry in pbar(os.listdir(dataset_path)):
    res = util.get_entry(os.path.join(dataset_path, entry))
    rekor_entry = util.RekorEntry(res)
    entries.append({
        'type': rekor_entry._type,
        'identity': rekor_entry.identity,
        'oidc_issuer': rekor_entry.oidc_issuer,
        'not_before': rekor_entry.not_before,
        'not_after': rekor_entry.not_after,
        'signature_validity': rekor_entry.signature_validity,
        'artifact_id': rekor_entry.artifact_id,
        'timestamp': rekor_entry.timestamp,
        'log_index': rekor_entry.log_index,
    })

df = pd.DataFrame(entries)


df.to_csv('results/error_rekor_entries.csv', index=False)

