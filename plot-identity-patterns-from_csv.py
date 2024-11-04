import json
import analyze_utils as util
import os
import sys
import progressbar
import pandas as pd
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
 
dataset_path = config['DEFAULT']['all_dataset_path'] 
limit = int(float(config['DEFAULT']['limit']))

identity_types = {
    "Corporate Domains": {},
    "Educational Institutions": {},
    "Email Providers": {},
    "Cloud Providers": {},
    "Government": {},
    "Personal Domains": {},
    "Other": {},
}

top_email_providers = [
    "gmail.com",
    "outlook.com",
    "hotmail.com",
    "yahoo.com",
    "icloud.com",
    "protonmail.com",
    "proton.me",
    "zoho.com",
    "aol.com",
]
service_accounts = ['.iam.gserviceaccount.com']

def categorize_domain(domain):
    domain = domain.lower()

    if domain in top_email_providers:
        return "Email Providers"
    elif any(domain.endswith(suffix) for suffix in service_accounts):
        return "Cloud Providers"
    elif any(keyword in domain for keyword in [".com", ".dev", ".org", ".io", ".net", ".ai", ".de", ".ca", ".fr", ".jp", ".it",".uk"]):
        return "Corporate Domains"
    elif any(keyword in domain for keyword in ["gov"]):
        return "Government"
    elif any(keyword in domain for keyword in ["edu", "ac", "usp.br"]):
        return "Educational Institutions"
    # elif any(keyword in domain for keyword in ["test", "example"]):
    #     return "Testing/Dummy Domains"
    else:
        return "Personal Domains"


print("Reading entries...", end='')
sys.stdout.flush()

ci_cd_identity = 0
no_identity = 0
email_not_found = 0
email_as_publickey = 0


df = pd.read_csv('csv_data/all_rekor_entries.csv')
print("done")

def plot_identity_types(df):
    length = len(df['identity'])
    for identity in df['identity']:
        if pd.isna(identity):
            no_identity += 1
            continue

        if identity == "not-found":
            email_not_found += 1
            continue

        if len(identity) > 200 or identity.endswith('='):
            email_as_publickey += 1
            continue
        
        if identity.startswith("http"):
            ci_cd_identity += 1
            if not identity.startswith("https://github.com") and not identity.startswith("https://gitlab"):
                print(f"Not CI/CD Identity starts with: {identity}")
                continue
            # print(f"Identity starts with: {identity}")
            continue
        
        domain = identity.split('@')[-1] if '@' in identity else None
        if domain:
            category = categorize_domain(domain)

            if domain not in identity_types[category]:
                identity_types[category][domain] = 0
            identity_types[category][domain] += 1
        else:
            sys.stdout.flush()
            if identity not in identity_types['Other']:
                # print(f"The author without domain: {identity}\n", flush=True)
                identity_types['Other'][identity] = 0
            identity_types['Other'][identity] += 1

    total_count = 0

    for category, domains in identity_types.items():
        print(f"\n{category}:")
        for domain, count in domains.items():
            print(f"  {domain}: {count}")
            total_count += count

    print(f"\nTotal count of all identities: {total_count}")
    print(f"\nTotal count of no_identity recorded: {no_identity}")
    print(f"\nTotal count of email_not_found: {email_not_found}")
    print(f"\nTotal count of email_as_publickey: {email_as_publickey}")
    print(f"\nTotal count of ci_cd_identity: {ci_cd_identity}")
    print(f"\nTotal identity entries: {total_count + no_identity + email_as_publickey + email_as_publickey + ci_cd_identity}")
    print(f"\nTotal identity def: {length}")


    import matplotlib.pyplot as plt

    category_counts = {category: sum(domains.values()) for category, domains in identity_types.items() if category != "Other"}
    sorted_categories = sorted(category_counts.items(), key=lambda item: item[1], reverse=True)
    categories, counts = zip(*sorted_categories)

    plt.figure(figsize=(10, 6))
    plt.bar(categories, counts, color='skyblue')
    plt.ylabel('Count')
    plt.title('Total Count of Identity Types by Category')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('results/patterns/identity_types.png')

def find_invalid_signatures(df):
    print("Starting_____________")
    invalid_signature_entries = df[df['signature_validity'] == "False"]

    invalid_signature_entries.to_csv('results/signed_with_expired_cert.csv', index=False)
    
    # invalid_sign_identities = invalid_signature_entries['identity'].tolist()

    # print("Identities with invalid signatures:")
    # for identity in invalid_sign_identities:
    #     print(identity)
def fulcio_to_otherCA_ratio(df):
    """Calculates the ratio of Fulcio-issued certificates to other CA-issued certificates."""
    from tqdm import tqdm
    ignore_list = ("not_keyless", "not-found", "None")
    
    # Counters for Fulcio and other CAs
    fulcio_count = 0
    other_ca_count = 0
    total_cert_count = len(df)
    
    for _, row in tqdm(df.iterrows(), total=total_cert_count):
        if pd.isna(row['identity']) or row['identity'] in ignore_list:
            continue
        
        #another CA (starts with "unknown_")
        elif row['identity'].startswith("unknown_"):
            other_ca_count += 1
        
        # Otherwise, consider it Fulcio
        else:
            fulcio_count += 1

    # Calculate the ratio (avoid division by zero)
    ratio = (fulcio_count / other_ca_count) if other_ca_count else float('inf')

    # Output the results
    print(f"Fulcio-issued certificates: {fulcio_count}")
    print(f"Other CA-issued certificates: {other_ca_count}")
    print(f"Fulcio to Other CA ratio: {ratio:.2f}")
            

def is_fulcio_cert_incomplete_identity(df):
    """Checks for Fulcio-issued certificates missing either an identity or an issuer and reports counts."""
    from tqdm import tqdm
    ignore_list = ("not_keyless", "not-found", "No_Issuer", "None")
    
    # Counters for incomplete identity stats
    missing_issuer_count = 0
    missing_identity_count = 0
    total_cert_count = len(df)
    
    for _, row in tqdm(df.iterrows(), total=total_cert_count):
        # identity without issuer
        if not pd.isna(row['identity']) and row['oidc_issuer'] == "No_Issuer":
            missing_issuer_count += 1

        # issuer without identity
        if (
            not pd.isna(row['oidc_issuer']) and 
            row['oidc_issuer'] not in ignore_list and
            pd.isna(row['identity'])
        ):
            missing_identity_count += 1

    print(f"Total certificates checked: {total_cert_count}")
    print(f"Certificates missing issuer: {missing_issuer_count}")
    print(f"Certificates missing identity: {missing_identity_count}")
    
    # return {
    #     "total_cert_count": total_cert_count,
    #     "missing_issuer_count": missing_issuer_count,
    #     "missing_identity_count": missing_identity_count
    # }


def non_ephemeral_cert_percent(df):
    """Calculates the percentage of Fulcio-issued certificates that are not ephemeral (lasting over 10 minutes)."""
    
    from tqdm import tqdm
    
    ignore_list = ("not_keyless", "not-found", "No_Issuer", "None")
    non_ephemeral_count = 0
    valid_cert_count = 0 
    
    for _, row in tqdm(df.iterrows(), total=len(df)):
        if (
            not pd.isna(row['identity']) and
            not pd.isna(row['oidc_issuer']) and
            row['oidc_issuer'] not in ignore_list and
            row['identity'] not in ignore_list and
            not row['identity'].startswith("unknown_") and
            not pd.isna(row['not_before']) and
            not pd.isna(row['not_after'])
        ):
            valid_cert_count += 1
            not_before = pd.to_datetime(row['not_before'])
            not_after = pd.to_datetime(row['not_after'])

            # Calculate duration in minutes
            duration_minutes = (not_after - not_before).total_seconds() / 60
            if duration_minutes > 10:
                non_ephemeral_count += 1

                print(f"not_before: {not_before}")
                print(f"not_after: {not_after}")
                print(f"duration_minutes: {duration_minutes}")
                print(f"Entry cert for logIndex {row['log_index']} with identity {row['identity']} not ephemeral")
    
    
    non_ephemeral_percentage = (non_ephemeral_count / valid_cert_count) * 100 if valid_cert_count else 0
    print(f"The % of non-ephemeral certificates among valid certificates is {non_ephemeral_percentage}%")

total_entries = len(df)
widgets = [
'Processed: ', progressbar.Percentage(), 
' (', progressbar.FormatLabel('%(value)d / {} lines'.format(total_entries)), 
' in: ', progressbar.ETA(), ')'
]
pbar = progressbar.ProgressBar(widgets=widgets, maxval=total_entries)

# find_invalid_signatures(df)
# non_ephemeral_cert_percent(df)
# is_fulcio_cert_incomplete_identity(df)
fulcio_to_otherCA_ratio(df)
