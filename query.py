"""Query and store rekor's full database in JSON files.

Uses caching to avoid re-downloading records.

Usage from command line:
>>> python query.py
"""

# import concurrent.futures
from multiprocessing import Pool
import os
import subprocess
import time

# folder name for storing dataset
BASENAME = "dataset"
DOWNLOADED = "downloaded_entry.txt"
# number of simultaneous processes to use
NUM_PROCESSES = 10
RATE_LIMIT_DELAY = 2


def detect_filenames(max_height,min_height, downloaded=DOWNLOADED):
    """Find records not yet downloaded.

    Args:
        max_height (int): number of records in rekor database
        downloaded (str): file containing downloaded entries

    Returns:
        target (set) - entries not yet downloaded
    """

    # range is NOT inclusive
    target = set(range(min_height, max_height + 1))

    try:
      with open(downloaded, 'r') as f:
          indexes = [int(line.strip()) for line in f]
      for index in indexes:
          if min_height <= index <= max_height:
              target.remove(index)
    except FileNotFoundError:
        # If the file doesn't exist, assume no entries have been downloaded
        pass

    return target


def fetch_record_with_rate_limit(index, basename=BASENAME):
    """Retrieve desired record from rekor database with rate limiting.

    Args:
        index (int): record index
        basename (str): folder containing records

    Returns:
        record (json) - Rekor record in json blob
        filename (str)
    """
    filename = os.path.join(basename, f"rekor_obj-{index}.json")
    print("filename", filename)
    print(f"Getting entry {index}...")

        # Use rekor-cli to query database with rate limiting
    attempt = 0
    while attempt < 4:
        try:
            record = subprocess.check_output(
                ["rekor-cli", "--format", "json", "get", "--log-index", str(index)]
            )
            break  # Break out of the loop if request succeeds
        except Exception as e:
            print(index, f"failed! Exception: {e}")
            attempt += 1
            time.sleep(RATE_LIMIT_DELAY)  # Add delay between requests
    else:
        print(f"Failed to retrieve record for index {index}")
        record = ""

    return record, filename


def store_record(record, filename):
    """Store record from rekor database.

    Args:
        record(json): json blob containing record
        filename (str): record index

    Returns:
        None
    """
    with open(filename, "wt") as fp:
        fp.write(record.decode("utf-8"))

    # TODO: Is this sleep necessary?
    time.sleep(0.001)


def process_record(index, basename=BASENAME):
    """Retrieve and store a Rekor record.

    Args:
        index (int): record index
        basename (str): folder containing records

    Returns:
        None
    """
    record, filename = fetch_record_with_rate_limit(index, basename)
    if record != "":
        store_record(record, filename)


if __name__ == "__main__":

    if not os.path.exists(BASENAME):
        os.mkdir(BASENAME)

    # determine total number of records currently in database
    # output = subprocess.check_output(["rekor-cli", "loginfo"])
    # TODO: make parsing less brittle
    # height = int(output.decode("utf-8").split("\n")[1].split()[3].strip())
    max_height = 65000000 
    min_height = 45000001
    print(f"log height: {max_height}")

    # check cache and print count of records requiring download
    print("Identifying locally-cached entries...", end="")
    need_to_download = detect_filenames(max_height, min_height)
    print("done")
    print(f"There are {len(need_to_download)} entries to download")

    # use multiprocessing to speed up download
    with Pool(NUM_PROCESSES) as p:
        p.map(process_record, need_to_download)
    print("Download Completed")

    # alternative method of speeding up download
    # TODO: Will require some rewriting to use
    # with concurrent.futures.ProcessPoolExecutor(max_workers=100) as executor:
    #     print("setting up process pool...", end='')
    #     futures = executor.map(fetch_obj, to_download, chunksize=64)
    #     print("done")
