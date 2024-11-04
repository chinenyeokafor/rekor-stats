import json
import analyze_utils as util
import os
import sys
import progressbar
import pandas as pd
import configparser
import os
import pandas as pd
from multiprocessing import Pool
from tqdm import tqdm


config = configparser.ConfigParser()
config.read('config.ini')
 
dataset_path = config['DEFAULT']['all_dataset_path'] 
limit = int(float(config['DEFAULT']['limit']))
NUM_PROCESSES = 20
write_to = 'results/all_rekor_dataset_test.csv'


def process_entries(entry, dataset_path=dataset_path):
    """Retrieve and parse it using REkorEntry class."""
    if int(entry.split('-')[1].split('.')[0]) <= 119000000:
        res = util.get_entry(os.path.join(dataset_path, entry))
        rekor_entry = util.RekorEntry(res)
        result = {
            'type': rekor_entry._type,
            'identity': rekor_entry.identity,
            'oidc_issuer': rekor_entry.oidc_issuer,
            'not_before': rekor_entry.not_before,
            'not_after': rekor_entry.not_after,
            'signature_validity': rekor_entry.signature_validity,
            'artifact_id': rekor_entry.artifact_id,
            'timestamp': rekor_entry.timestamp,
            'log_index': rekor_entry.log_index,
        }
        if result:
            store_record(result)
    # return result  # Return the result for each entry

def store_record(result, write_to=write_to):
    """Store record to CSV directly."""
    df = pd.DataFrame([result])  # Create a DataFrame from the single result
    df.to_csv(write_to, index=False, header=not os.path.exists(write_to), mode='a')


def split_list_into_chunks(lst, num_chunks):
    length = len(lst)
    chunk_size = length // num_chunks
    chunks = []
    for i in range(0, length, chunk_size):
        chunks.append(lst[i:i + chunk_size])
    return chunks

if __name__ == "__main__":

    # Reset the file at the start
    if os.path.exists(write_to):
        os.remove(write_to)

    print("Reading entries...", end='')
    sys.stdout.flush()

    # Gather file names
    all_entries = [entry.path for entry in os.scandir(dataset_path) if entry.is_file()]
    batches = split_list_into_chunks(all_entries, 4)
    for batch in batches:
        with Pool(NUM_PROCESSES) as p:
            p.map(process_entries, batch, chunksize=1000) 
            # p.map(process_entries, all_entries, chunksize=len(all_entries)//NUM_PROCESSES) 

    print("Parse Entries Completed")
