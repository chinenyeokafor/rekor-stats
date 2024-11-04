import pandas as pd
from tqdm import tqdm


tqdm.pandas()


malicious_df = pd.read_csv('csv_data/malicious_packages_sha256.csv')
rekor_df = pd.read_csv('csv_data/all_rekor_entries.csv')

# for faster lookup
rekor_artifact_ids = set(rekor_df['artifact_id'])
print(len(rekor_artifact_ids))
print(len(malicious_df))

malicious_df['is_match'] = malicious_df['sha256'].progress_apply(lambda x: x in rekor_artifact_ids)

matched_df = malicious_df[malicious_df['is_match']].drop(columns=['is_match'])

if not matched_df.empty:
    matched_df.to_csv('csv_data/matching_sha256_entries.csv', index=False)
    print("Matching entries found!!")
else:
    print("No matching entries were found.")
