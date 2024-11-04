import json
import analyze_utils as util
import os
import sys
import progressbar
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

email_not_found = 0
email_as_publickey = 0
total_entries = len(os.listdir(dataset_path))
widgets = [
    'Processed: ', progressbar.Percentage(), 
    ' (', progressbar.FormatLabel('%(value)d / {} lines'.format(total_entries)), 
    ' in: ', progressbar.ETA(), ')'
]
pbar = progressbar.ProgressBar(widgets=widgets, maxval=len(os.listdir(dataset_path)))

for entry in pbar(os.listdir(dataset_path)):
    res = util.get_entry(os.path.join(dataset_path, entry))
    element = util.RekorEntry(res)

    if element.author:
        if element.author == "not-found":
            email_not_found += 1
            continue
        if len(element.author) > 200 or element.author.endswith('='):
            email_as_publickey += 1
            continue

        
        domain = element.author.split('@')[-1] if '@' in element.author else None

        if domain:
            category = categorize_domain(domain)

            
            if domain not in identity_types[category]:
                identity_types[category][domain] = 0 
            identity_types[category][domain] += 1  
        else:
            # Authors without a domain
            sys.stdout.flush()
            if element.author not in identity_types['Other']:
                print(f"The author without domain: {element.author}\n", flush=True)
                identity_types['Other'][element.author] = 0
            identity_types['Other'][element.author] += 1


total_count = 0 

for category, domains in identity_types.items():
    print(f"\n{category}:")
    for domain, count in domains.items():
        print(f"  {domain}: {count}")
        total_count += count 

print(f"\nTotal count of all identities: {total_count}")



category_counts = {category: sum(domains.values()) for category, domains in identity_types.items()}

sorted_categories = sorted(category_counts.items(), key=lambda item: item[1], reverse=True)
categories, counts = zip(*sorted_categories) 

import matplotlib.pyplot as plt
import numpy as np

plt.figure(figsize=(10, 6))
plt.bar(categories, counts, color='skyblue')
plt.ylabel('Count')
plt.title('Total Count of Identity Types by Category')
plt.xticks(rotation=45)
plt.tight_layout() 
# plt.show()
plt.savefig('identity_types.png')



# # Shows the Email Providers with a stacked bar chart
# email_providers = identity_types["Email Providers"]
# email_domains = list(email_providers.keys())
# email_counts = list(email_providers.values())


# plt.figure(figsize=(10, 6))
# bar_width = 0.4
# index = np.arange(len(categories))
# plt.bar(index, counts, color='skyblue', label='Total Counts')

# if "Email Providers" in categories:
#     email_index = categories.index("Email Providers")
#     bottom_count = counts[email_index]
    
#     for i, (domain, count) in enumerate(zip(email_domains, email_counts)):
#         plt.bar(email_index, count, bottom=bottom_count - count, label=domain)

# plt.ylabel('Count')
# plt.title('Total Count of Identity Types by Category (Email Providers Stacked)')
# plt.xticks(index, categories, rotation=45)
# plt.legend(title='Email Domains', loc='upper left', bbox_to_anchor=(1, 1))
# plt.tight_layout() 
# # plt.show()
# plt.savefig('identity_types_stacked.png')