import os
import json
import pandas as pd
from tqdm import tqdm
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
 
base_directory = config['DEFAULT']['malicious_packages_path'] 


def extract_sha256_from_json_files(base_directory):
    data = []
    for package_manager in tqdm(os.listdir(base_directory), total=len(os.listdir(base_directory))):
        package_manager_path = os.path.join(base_directory, package_manager)

        # Ensure it's a directory
        if os.path.isdir(package_manager_path):

            print(f"Checking {package_manager} package managers......")
            for package_name in os.listdir(package_manager_path):
                package_name_path = os.path.join(package_manager_path, package_name)

                # Check if it's a directory
                if os.path.isdir(package_name_path):

                    print(f"Checking packages {package_name} in ......")
                    for filename in os.listdir(package_name_path):
                        if filename.endswith('.json'):
                            file_path = os.path.join(package_name_path, filename)

                            with open(file_path, 'r', encoding='utf-8') as file:
                                try:
                                    json_data = json.load(file)
                                    
                                    origins = json_data.get('database_specific', {}).get('malicious-packages-origins')
                                    if origins and 'sha256' in origins[0]:
                                        sha256 = origins[0]['sha256']
                                    else:
                                        continue
                                    
                                    data.append({
                                        'package-manager': package_manager,
                                        'package-name': package_name,
                                        'sha256': sha256
                                    })
                                except (json.JSONDecodeError, KeyError) as e:
                                    print(f"Error reading {file_path}: {e}")
                                    import pdb; pdb.set_trace()

    df = pd.DataFrame(data)
    df.to_csv('malicious_packages_sha256.csv', index=False)


extract_sha256_from_json_files(base_directory)
