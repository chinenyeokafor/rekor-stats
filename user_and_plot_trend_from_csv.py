import json
import analyze_utils as util
import os
import sys
import progressbar
import re
import pandas as pd
import matplotlib.pyplot as plt
import configparser
from tqdm import tqdm
import requests, time

config = configparser.ConfigParser()
config.read('config.ini')
 
dataset_path = config['DEFAULT']['all_dataset_path'] 
limit = int(float(config['DEFAULT']['limit']))

# Set global font properties
plt.rcParams['font.size'] = 14  # Set default font size
plt.rcParams['axes.titlesize'] = 18  # Set title font size
plt.rcParams['axes.labelsize'] = 16  # Set axis label font size
plt.rcParams['xtick.labelsize'] = 14  # Set x-tick label font size
plt.rcParams['ytick.labelsize'] = 14  # Set y-tick label font size
plt.rcParams['legend.fontsize'] = 14  # Set legend font size

def get_unique_repos_with_trends(df):
    github_repos = {}
    gitlab_repos = {}
    archlinux_repos = {}
    other_repos = {}

    for _, row in pbar(df.iterrows()):
        identity = row['identity']
        timestamp = row['timestamp']
        if pd.isna(identity) or pd.isna(timestamp):
            continue

        if identity.startswith("https://github.com/"):
            match = re.search(r"github\.com/([^/]+)/", identity)
            if match:
                repo = match.group(1)
                if repo not in github_repos or timestamp < github_repos[repo]:
                    github_repos[repo] = timestamp

        elif identity.startswith("https://gitlab.com/"):
            match = re.search(r"gitlab\.com/([^/]+)/", identity)
            if match:
                repo = match.group(1)
                if repo not in gitlab_repos or timestamp < gitlab_repos[repo]:
                    gitlab_repos[repo] = timestamp

        elif identity.startswith("https://gitlab.archlinux.org/"):
            match = re.search(r"archlinux\.org/([^/]+)/", identity)
            if match:
                repo = match.group(1)
                if repo not in archlinux_repos or timestamp < archlinux_repos[repo]:
                    archlinux_repos[repo] = timestamp

        else:
            match = re.search(r"https?://([^/]+)/", identity)
            if match:
                repo = match.group(1)
                if repo not in other_repos or timestamp < other_repos[repo]:
                    other_repos[repo] = timestamp

    github_df = pd.DataFrame(github_repos.items(), columns=["Repo", "First Signed"])
    gitlab_df = pd.DataFrame(gitlab_repos.items(), columns=["Repo", "First Signed"])
    archlinux_df = pd.DataFrame(archlinux_repos.items(), columns=["Repo", "First Signed"])
    other_df = pd.DataFrame(other_repos.items(), columns=["Repo", "First Signed"])


    os.makedirs('results', exist_ok=True)
    github_df.to_csv('results/unique_github_repos_with_dates.csv', index=False)
    gitlab_df.to_csv('results/unique_gitlab_repos_with_dates.csv', index=False)
    archlinux_df.to_csv('results/unique_archlinux_repos_with_dates.csv', index=False)
    other_df.to_csv('results/unique_other_repos_with_dates.csv', index=False)


def plot_single_repo_trends():
    github_df = pd.read_csv('results/unique_github_repos_with_dates.csv')
    # gitlab_df = pd.read_csv('results/unique_gitlab_repos_with_dates.csv')
    # archlinux_df = pd.read_csv('results/unique_archlinux_repos_with_dates.csv')
    # other_df = pd.read_csv('results/unique_other_repos_with_dates.csv')

    def plot_trend(dataframe, title):
        dataframe['First Signed'] = pd.to_datetime(dataframe['First Signed'], unit='s')
        
        monthly_trend = dataframe.groupby(dataframe['First Signed'].dt.to_period("M")).size()    
        
        plt.figure(figsize=(12, 6))
        monthly_trend.plot(kind='bar', color='skyblue', width=0.8) 
        plt.title(title)
        plt.xlabel("Timestamp", fontsize=14)
        plt.ylabel("Count of New Orgs", fontsize=14)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig("results/github_orgs_monthly_adoption.png")
        # plt.show()

    print("Visualizing trends...")
    plot_trend(github_df, "New Github Organization Stats")
    # plot_trend(gitlab_df, "GitLab Repos")
    # plot_trend(archlinux_df, "Arch Linux Repos")
    # plot_trend(other_df, "Other Repos")

def plot_combined_repo_trends():
    # github_df = pd.read_csv('results/unique_github_repos_with_dates.csv')
    github_df = pd.read_csv('results/github_organizations.csv')
    gitlab_df = pd.read_csv('results/unique_gitlab_repos_with_dates.csv')
    archlinux_df = pd.read_csv('results/unique_archlinux_repos_with_dates.csv')
    other_df = pd.read_csv('results/unique_other_repos_with_dates.csv')

    def get_monthly_trend(dataframe):
        dataframe['First Signed'] = pd.to_datetime(dataframe['First Signed'], unit='s')
        return dataframe.groupby(dataframe['First Signed'].dt.to_period("M")).size()

    github_trend = get_monthly_trend(github_df)
    gitlab_trend = get_monthly_trend(gitlab_df)
    archlinux_trend = get_monthly_trend(archlinux_df)
    other_trend = get_monthly_trend(other_df)

    combined_trend = pd.DataFrame({
        'GitHub': github_trend,
        'GitLab': gitlab_trend,
        'Arch Linux GitLab': archlinux_trend
    })

    # Plot the combined trend
    combined_trend.plot(kind='bar', stacked=False, color=['skyblue', 'lightgreen', 'salmon', 'gold'], figsize=(12, 6), width=0.8)
    
    plt.title("Monthly Adoption: New Org/User Stats")
    plt.xlabel("Timestamp")
    plt.ylabel("# of Unique Owners")
    plt.xticks(rotation=45)
    plt.legend(title='Platform')
    plt.tight_layout()
    plt.savefig('results/unique_repo_trend.png')
    # plt.show()

def process_github_repositories():
    github_df = pd.read_csv('results/unique_github_repos_with_dates.csv')
    total_entries = len(github_df)
    widgets = [
    'Processed: ', progressbar.Percentage(), 
    ' (', progressbar.FormatLabel('%(value)d / {} lines'.format(total_entries)), 
    ' in: ', progressbar.ETA(), ')'
    ]
    pbar = progressbar.ProgressBar(widgets=widgets, maxval=len(github_df))

    user_file_path = 'results/github_users.csv'
    org_file_path = 'results/github_organizations.csv'

    # Load existing users and organizations from files if they exist
    existing_users = set()
    existing_orgs = set()

    if os.path.exists(user_file_path):
        existing_users_df = pd.read_csv(user_file_path)
        existing_users = set(existing_users_df['Repo'])
    
    if os.path.exists(org_file_path):
        existing_orgs_df = pd.read_csv(org_file_path)
        existing_orgs = set(existing_orgs_df['Repo'])

    users = []
    orgs = []
    
    wait_time = 3600  # 1 hour

    # increases reate
    # add TOKN here fot auth
    # Function to check GitHub account type
    def check_github_account_type(username):
        url = f"https://api.github.com/users/{username}"
        headers = {"Authorization": f"token {token}"}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            account_info = response.json()
            return account_info.get('type')  # Returns 'User' or 'Organization'
        elif response.status_code == 404:
            return None  # Username not found
        elif response.status_code == 403:
            raise Exception("Rate limit exceeded. Waiting required.")  # Rate limit reached
        else:
            raise Exception(f"Error fetching data for {username}: {response.status_code}")

    print("Getting Github Account Type.............")
    for index, row in pbar(github_df.iterrows()):
        username = row['Repo']
        
        if username in existing_users or username in existing_orgs:
            continue
        
        try:
            account_type = check_github_account_type(username)
            
            if account_type == 'User':
                users.append({'Repo': username, 'First Signed': row['First Signed']})
            elif account_type == 'Organization':
                orgs.append({'Repo': username, 'First Signed': row['First Signed']})

        except Exception as e:
            if str(e) == "Rate limit exceeded. Waiting required.":
                print(f"\nLength of Org so far: {len(orgs)}")
                print(f"Length of User so far: {len(users)}")
                
                if users:
                    pd.DataFrame(users).to_csv(user_file_path, mode='a', header=not os.path.exists(user_file_path), index=False)
                    users = [] 

                if orgs:
                    pd.DataFrame(orgs).to_csv(org_file_path, mode='a', header=not os.path.exists(org_file_path), index=False)
                    orgs = []  

                print(e)  
                print("Waiting for 1 hour due to rate limit...")
                time.sleep(wait_time) 
            else:
                print(e) 

    # Append any remaining
    if users:
        pd.DataFrame(users).to_csv(user_file_path, mode='a', header=not os.path.exists(user_file_path), index=False)
    if orgs:
        pd.DataFrame(orgs).to_csv(org_file_path, mode='a', header=not os.path.exists(org_file_path), index=False)

    print("Users and organizations have been saved to their respective files.")

if __name__ == "__main__":

    print("Reading entries...", end='')
    sys.stdout.flush()

    df = pd.read_csv('csv_data/all_rekor_entries_old.csv')
    print("done")
    total_entries = len(df)
    widgets = [
    'Processed: ', progressbar.Percentage(), 
    ' (', progressbar.FormatLabel('%(value)d / {} lines'.format(total_entries)), 
    ' in: ', progressbar.ETA(), ')'
    ]
    pbar = progressbar.ProgressBar(widgets=widgets, maxval=total_entries)


    get_unique_repos_with_trends(df)
    plot_combined_repo_trends()
    plot_single_repo_trends()
    # process_github_repositories()
