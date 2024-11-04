import json
import os
from base64 import b64decode as b64d
from cryptography import x509
from cryptography.x509.oid import ExtensionOID
import re, base64
import progressbar
import binascii
from cryptography.hazmat.primitives import serialization

from collections import Counter
import configparser
import subprocess
from cryptography.x509.oid import NameOID

config = configparser.ConfigParser()
config.read('config.ini')


unknown_Obj_path = config['DEFAULT']['unknown_Obj_path']
none_type_path = config['DEFAULT']['none_type_path']
wrong_ascii_filepath = config['DEFAULT']['wrong_ascii_filepath']
dataset_path = config['DEFAULT']['all_dataset_path']

signature_without_cert = 0

unknown_Obj_type = set()

def is_json(s):
    try:
        json.loads(s)
        return True
    except json.JSONDecodeError:
        return False

def is_base64(s):
    # Adjust padding if needed
    s += '=' * (-len(s) % 4)
    try:
        base64.b64decode(s, validate=True)
        return True
    except (binascii.Error, ValueError):
        return False

def view_certificate(cert_content):
    try:
        # Decode the byte content to string before passing it to OpenSSL
        cert_str = cert_content.decode('utf-8')

        result = subprocess.run(
            ["openssl", "x509", "-text", "-noout"],
            input=cert_str, 
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            log(result.stdout)  
        else:
            log(f"Error: {result.stderr}")
    
    except Exception as e:
        log(f"An error occurred: {e}")


def extract_cert_info(self,payload):
    def format_url(build_signer_url):
        url_start = build_signer_url.find(b'http')

        # Check if "http" was found
        if url_start != -1:  
            url_bytes = build_signer_url[url_start:] 
            
            try:
                build_signer_url_str = url_bytes.decode('utf-8')
                return build_signer_url_str
            except UnicodeDecodeError as e:
                log("Decoding failed:", e)

    pub_key_delimiters = "-----BEGIN PUBLIC KEY-----", "-----BEGIN PGP", "---BEGIN SSH", "---BEGIN PGP", "---BEGIN PKCS7", "---BEGIN PGP", "ssh-rsa",
    exempt_type = "jar", "rpm", "alpine", "ssh",
    try:
        if self._type in exempt_type:
            author = self.author
            try:
                author = b64d(self.author)
            except:
                pass
        else:
            author = b64d(self.author)
        if author.decode('utf-8').startswith("-----BEGIN CERTIFICATE"):
            cert = x509.load_pem_x509_certificate(author)
            signature_time = payload['IntegratedTime']
            not_before = cert.not_valid_before
            not_after = cert.not_valid_after
            
            attributes = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
            cert_ca = attributes[0].value if attributes else None
            # log(f"Issuer1 is {cert_ca}")

            if cert_ca == "sigstore-intermediate" or cert_ca == "sigstore":
                try:
                    # workflow
                    try:
                        # oidc_issuer v2
                        oidc_issuer = cert.extensions.get_extension_for_oid(
                            x509.ObjectIdentifier("1.3.6.1.4.1.57264.1.8")
                        ).value.value
                        oidc_issuer = format_url(oidc_issuer)
                    except:
                        oidc_issuer =cert.extensions.get_extension_for_oid(
                            x509.ObjectIdentifier("1.3.6.1.4.1.57264.1.1")
                        ).value.value
                        oidc_issuer = format_url(oidc_issuer)
                    # log(f"CI/CD oidc_issuer is {oidc_issuer}")
                    try:
                        build_signer_url = cert.extensions.get_extension_for_oid(
                            x509.ObjectIdentifier("1.3.6.1.4.1.57264.1.9")
                        ).value.value
                        build_signer_url = format_url(build_signer_url)
                        identity = build_signer_url

                    # log(f"build_signer_url is {build_signer_url}")
                    # source_repo_uri = cert.extensions.get_extension_for_oid(
                    #     x509.ObjectIdentifier("1.3.6.1.4.1.57264.1.12")
                    # ).value.value
                    # source_repo_uri = format_url(source_repo_uri)
                    # log(f"source_repo_uri_str is {source_repo_uri}")
                    except:
                        pass
                except:
                    # human accounts, service accounts
                    try:
                        # oidc_issuer v2
                        oidc_issuer = cert.extensions.get_extension_for_oid(
                            x509.ObjectIdentifier("1.3.6.1.4.1.57264.1.8")
                        ).value.value
                        oidc_issuer = format_url(oidc_issuer)
                    except:
                        try:
                            oidc_issuer =cert.extensions.get_extension_for_oid(
                                x509.ObjectIdentifier("1.3.6.1.4.1.57264.1.1")
                            ).value.value
                            oidc_issuer = format_url(oidc_issuer)
                        except:
                            # some have email but no issuer
                            oidc_issuer = "No_Issuer"
                            pass
                    # log(f" oidc_issuer is {oidc_issuer}")
                    try:

                        san_extension = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME) 
                        self.repo = san_extension.value.get_values_for_type(x509.GeneralName)
                        email_values = san_extension.value.get_values_for_type(x509.RFC822Name)

                        if email_values:
                            identity = email_values[0]
                            # log(f"Email is {identity}")
                            # TODO: Does this generalize? find better way to handle
                        elif san_extension.value.get_values_for_type(x509.UniformResourceIdentifier):
                            identity = san_extension.value.get_values_for_type(x509.UniformResourceIdentifier)[0]
                    except:
                        if cert_ca == "sigstore-intermediate" or cert_ca == "sigstore" and self._type == 'JAR':
                            self.identity = "not_keyless"
                            self.oidc_issuer = "not_keyless"
                            self.not_before = not_before
                            self.not_after = not_after
                            self.signature_validity = is_signature_within_validity(signature_time, not_before, not_after)

                        # import pdb; pdb.set_trace()
                        # pass

            
            elif cert_ca is not None:
                try:
                    other_ca = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value

                    if other_ca not in iss_set:
                    #     view_certificate(author)
                        iss_set.add(other_ca)
                        write_to_file((f"{payload['LogIndex']} + {other_ca}"), 'issues_folder/weird_CAs.txt')
                    identity = f"unknown_{other_ca}"
                        # import pdb; pdb.set_trace()
                except:
                    other_ca =cert.issuer.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[0].value
                    if other_ca not in iss_set:
                    #     view_certificate(author)
                        iss_set.add(other_ca)
                        write_to_file((f"{payload['LogIndex']} + {other_ca}"), 'issues_folder/weird_CAs.txt')
                    identity = f"unknown_{other_ca}"
                        # import pdb; pdb.set_trace()
                        
            elif cert_ca is None:
                    # No point parsing empty issuer
                    oidc_issuer = "None"
                    identity = f"unknown_Empty Issuer"
                # try:
                #     source_repo_uri = 'NA'
                #     oidc_issuer = "None"
                #     identity = f"unknown_Empty Issuer"
                #     san_extension = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME) 
                #     self.repo = san_extension.value.get_values_for_type(x509.GeneralName)
                #     email_values = san_extension.value.get_values_for_type(x509.RFC822Name)


                #     if email_values:
                #         identity = email_values[0]

                #     oidc_issuer = cert.extensions.get_extension_for_oid(
                #         x509.ObjectIdentifier("1.3.6.1.4.1.57264.1.8")
                #     ).value.value
                #     oidc_issuer = format_url(oidc_issuer)
                #     # log(f" oidc_issuer is {oidc_issuer}")
                # except:
                #     pass1221720
            # if self._type == "minisign":
            #     import pdb; pdb.set_trace()

            self.identity = identity
            self.oidc_issuer = oidc_issuer
            self.not_before = not_before
            self.not_after = not_after
            self.signature_validity = is_signature_within_validity(signature_time, not_before, not_after)

        elif author.decode('utf-8').startswith(pub_key_delimiters):
            self.identity = 'not_keyless'
            self.oidc_issuer = 'not_keyless'
            self.not_before = 'not_keyless'
            self.not_after = 'not_keyless'
            self.signature_validity = 'not_keyless'

        elif self._type == "minisign":
            self.identity = 'not_keyless'
            self.oidc_issuer = 'not_keyless'
            self.not_before = 'not_keyless'
            self.not_after = 'not_keyless'
            self.signature_validity = 'not_keyless'
            
    except:
        # import pdb; pdb.set_trace()
        # sample_index = [35473462, 9169368, 9105283, 9510006, 337, 693292, 699114, 2427822, 1196362, 3755199, 3755199]
        # log(payload)
        # if payload['LogIndex'] in sample_index:
        #     if self.author == 'invalid_type_in-toto':
        #         pass
        #     else:
        #         log(f"LogIndex is {payload['LogIndex']}, type is {self._type}")
        #         import pdb; pdb.set_trace()
        pass

def is_signature_within_validity(signature_time, not_before, not_after):
    from datetime import datetime, timezone

    not_before = not_before.replace(tzinfo=timezone.utc)
    not_after = not_after.replace(tzinfo=timezone.utc)
    signature_time = datetime.fromtimestamp(signature_time, tz=timezone.utc)
    return not_before <= signature_time <= not_after

iss_set = set()

def extract_cert_info_1(self, payload):
    global signature_without_cert
    try:
        # Decode the public key
        author = b64d(self.author)
        if author.decode('utf-8').startswith("-----BEGIN CERTIFICATE"):
            cert = x509.load_pem_x509_certificate(author)
            email = "not-found"
            provider_oid = x509.ObjectIdentifier("1.3.6.1.4.1.57264.1.1")

            try:
                # import pdb; pdb.set_trace()
                san_extension = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME) 
                self.repo = san_extension.value.get_values_for_type(x509.GeneralName)
                email_values = san_extension.value.get_values_for_type(x509.RFC822Name)
                if email_values:
                    email = email_values[0]
                    # log(f"{payload['LogIndex']} email is {email} \n Repo is {self.repo}")
                
            except Exception as e:
                # log(f"Error retrieving SAN: {e}")
                try:
                    iss = cert.issuer.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[0].value
                    # if iss not in iss_set:
                    #     view_certificate(author)
                    #     log()
                    #     log(cert.issuer.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[0].value)
                    #     iss_set.add(iss)
                    # import pdb; pdb.set_trace()
                    write_to_file(payload['LogIndex'], 'issues_folder/weird_CAs.txt')
                    
                    email = f"unknown_{iss}"
                except:
                        pass 
                
            # Attempt to retrieve provider OID
            try:
                oicd = cert.extensions.get_extension_for_oid(provider_oid).value.value.decode("utf-8")
            except Exception as e:
                # log(f"Error retrieving provider OID: {e}")
                # import pdb; pdb.set_trace()
                oicd = "self"

            self.author =  email
            self.provider = oicd
        elif author.decode('utf-8').startswith("-----BEGIN PGP"):
            self.author = "PGP"
            self.provider = "PGP"
        else:
            #key
            signature_without_cert += 1
    except Exception as e:
        log(f"Error extracting certificate info: {e}")
        # import pdb; pdb.set_trace()

    # return None


def parse_rekord(self, payload): 
    self._type = payload['Body']['RekordObj']['signature']['format']
    self.artifact_id = payload['Body']['RekordObj']['data']['hash']['value']
    self.provider = None
    try:
        self.author = payload['Body']['RekordObj']['signature']['publicKey']['content']
        extract_cert_info(self, payload)
    except Exception as e:
        log(e)
        # import pdb; pdb.set_trace()
        
def parse_in_toto(self, payload): 
    global signature_without_cert
    try:
        self._type = "in-toto"
        if is_json(payload['Attestation']):
            attestation = json.loads(payload['Attestation'])

            if len(attestation):
                # actualfax cosign payload
                try:
                    if attestation.decode("utf-8").startswith("# cosign\n\n"):
                        link = {'predicateType': "cosign-readme :)"}

                except:
                    link = attestation
                    if type(link) == list:
                        link = link[0]
            else:
                link = {'predicateType': "opaque"}
            # self._type = "in-toto {}".format(link['predicateType'])
            self._type = "in-toto" #classify all as intoto
            if 'subject' in link and link['subject']:
                if type(link['subject']) == list:
                    try:
                        self.artifact_id = link['subject'][0]['name'] 
                    except:
                        self.artifact_id = 'unknown'
                else:
                    self.artifact_id = link['subject']['name']
            else:
                self.artifact_id = payload['Body']['IntotoObj']['content']['hash']['value']
            # self.author = payload['Body']['IntotoObj']['content']['envelope']['publicKey']
            try:
                self.author = payload['Body']['IntotoObj']['publicKey']
            except:
                self.author = payload['Body']['IntotoObj']['content']['envelope']['signatures'][0]['publicKey']

        elif is_base64(payload['Attestation']):
            attestation = b64d(payload['Attestation'])
            if len(attestation):
                # actualfax cosign payload
                if attestation.decode("utf-8").startswith("# cosign\n\n"):
                    link = {'predicateType': "cosign-readme :)"}

                else:
                    link = json.loads(attestation)
                    if type(link) == list:
                        link = link[0]
            else:
                link = {'predicateType': "opaque"}
            # self._type = "in-toto {}".format(link['predicateType'])
            self._type = "in-toto" #classify all as intoto
            if 'subject' in link and link['subject']:
                if type(link['subject']) == list:
                    self.artifact_id = link['subject'][0]['name'] 
                else:
                    self.artifact_id = link['subject']['name']
            else:
                self.artifact_id = payload['Body']['IntotoObj']['content']['hash']['value']
            self.author = payload['Body']['IntotoObj']['publicKey']

        elif payload['Attestation'] == 'hello world':
            link = payload
            self._type = "in-toto" 
            if 'subject' in link and link['subject']:
                if type(link['subject']) == list:
                    self.artifact_id = link['subject'][0]['name'] 
                else:
                    self.artifact_id = link['subject']['name']
            else:
                self.artifact_id = payload['Body']['IntotoObj']['content']['hash']['value']
            self.author = payload['Body']['IntotoObj']['content']['envelope']['signatures'][0]['publicKey']
            

        else:
            self.author = "invalid_type_in-toto"
            # import pdb; pdb.set_trace()

        extract_cert_info(self, payload)

    except Exception as e:
        signature_without_cert += 1
        if "string argument should contain only ASCII characters" in str(e):
            write_to_file(payload['LogIndex'], wrong_ascii_filepath)
        if "'utf-8' codec can't decode" in str(e):
            log(f"weird_intoto_format: index is {payload['LogIndex']}, type is {type(payload)}")
            write_to_file(payload['LogIndex'], 'issues_folder/weird_intoto_format_filepath')
        else:
            log(f"other exception: index is {payload['LogIndex']}, type is {type(payload)}")
            log(e)
            # import pdb; pdb.set_trace()

def parse_hashed_rekord(self, payload): 
    try:
        self._type = payload['Body']['HashedRekordObj']['signature']['format']
    except:
        self._type = "hashed_rekord"

    self.provider = None
    try:
        self.author = payload['Body']['HashedRekordObj']['signature']['publicKey']['content']
        extract_cert_info(self, payload)
    except Exception as e:
        log(e)
        # import pdb; pdb.set_trace()


    self.artifact_id = payload['Body']['HashedRekordObj']['data']['hash']['value']


def parse_dsse(self, payload): 
    # payload = payload['Body']["DSSEObj"]
    self._type = "DSSE"
    self.provider = None

    try:
        self.artifact_id = payload['Body']["DSSEObj"]['payloadHash']['value']
        try:
            self.author = payload['Body']["DSSEObj"]['signatures']['verifier']
        except Exception as e:
            self.author = payload['Body']["DSSEObj"]['signatures'][0]['verifier']
        extract_cert_info(self, payload)
    except Exception as e:
        log(e)
        # import pdb; pdb.set_trace()


def parse_rpm(self, payload): 
    payload = payload['Body']["RPMModel"]
    self._type = "rpm"
    self.artifact_id = "{Name}-{Epoch}:{Version}-{Release}-{Architecture}".format(**payload['package']['headers'])
    # FIXME: this should decode the b64 *and* then parse the gpg payload to fetch a uid
    self.author = payload['publicKey']['content']
    extract_cert_info(self, payload)


def parse_rfc3161(self, payload): 
    payload = payload['Body']["Rfc3161Obj"]
    self._type = "RFC3161"
    self.artifact_id = payload['tsr']['content']
    # FIXME: this should decode the b64 *and* then parse the cms payload to fetch a uid
    # self.author = payload['publicKey']['content']


def parse_helm(self, payload): 
    payload = payload['Body']["HelmObj"]
    self._type = "Helm"
    self.artifact_id = payload['chart']['hash']['value']
    self.author = payload['publicKey']['content']
    extract_cert_info(self,payload)


def parse_tuf(self, payload): 
    global signature_without_cert
    payload = payload['Body']["TufObj"]
    self._type = "Tuf"
    self.artifact_id = "TUF Trust root"
    self.author = "Sigstore authors"
    self.identity = 'not_keyless'
    self.oidc_issuer = 'not_keyless'
    self.not_before = 'not_keyless'
    self.not_after = 'not_keyless'
    self.signature_validity = 'not_keyless'
    signature_without_cert += 1



def parse_jar(self, payload_): 
    payload = payload_['Body']["JARModel"]
    self._type = "JAR"
    self.artifact_id = payload['archive']['hash']['value']
    # FIXME: this should decode the b64 *and* then parse the cms payload to fetch a uid
    self.author = payload['signature']['publicKey']['content']
    # self.author = payload['signature']['content']
    extract_cert_info(self,payload_)


def parse_alpine(self, payload_): 
    payload = payload_['Body']["AlpineModel"]
    self._type = "Alpine"
    try:
        self.artifact_id = payload['package']['pkginfo']['datahash']
    except Exception as e:
        log(e)
        # import pdb; pdb.set_trace()
    # FIXME: this should decode the b64 *and* then parse the cms payload to fetch a uid
    self.author = payload['publicKey']['content']
    extract_cert_info(self,payload_)



type_parser_dispatch = {
    "RekordObj": parse_rekord,
    "IntotoObj": parse_in_toto,
    "HashedRekordObj": parse_hashed_rekord,
    "Rfc3161Obj": parse_rfc3161,
    "HelmObj": parse_helm,
    "RPMModel": parse_rpm,
    "JARModel": parse_jar,
    "TufObj": parse_tuf,
    "AlpineModel": parse_alpine,
    "DSSEObj": parse_dsse,
}

def write_to_file(content, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'a') as file:
        file.write(f"{content}\n")

Debug = False
def log(s):
    if Debug:
        print(s)

class RekorEntry:

    _type = None
    artifact_id = None
    timestamp = None
    author = None

    identity = None
    oidc_issuer = None
    public_key = None
    not_before = None
    not_after = None
    signature_validity = None
    log_index = None
    signature_validity = None

    def __init__(self, payload):

        keys = [x for x in payload['Body'].keys()]
        assert (len(keys)) == 1
        if keys[0] in type_parser_dispatch:
            type_parser_dispatch[keys[0]](self, payload)
            self.timestamp = payload['IntegratedTime']
            self.log_index = payload['LogIndex']
            # if self._type is None:
            #     import pdb; pdb.set_trace()
                
        else:
            # TODO: define unknown obj types parsing
            if keys[0] not in unknown_Obj_type:
                content = f"{keys[0]}:{payload['LogIndex']}"
                write_to_file(content, unknown_Obj_path)
                unknown_Obj_type.add(keys[0])
            # import pdb; pdb.set_trace()
            # if self._type is None:
            #     import pdb; pdb.set_trace()

class MinimalRekorEntry:

    _type = None
    artifact_id = None
    timestamp = None
    author = None

    def __init__(self, payload):

        keys = [x for x in payload['Body'].keys()]
        assert (len(keys)) == 1
        if keys[0] in type_parser_dispatch:
            self.timestamp = payload['IntegratedTime']
            self.log_index = payload['LogIndex']
                
        else:
            # TODO: define unknown obj types parsing
            if keys[0] not in unknown_Obj_type:
                content = f"{keys[0]}:{payload['LogIndex']}"
                write_to_file(content, unknown_Obj_path)
                unknown_Obj_type.add(keys[0])


def get_entry(filename):
    with open(filename) as fp:
        data = fp.read()
    try:
        result = json.loads(data)
    except Exception as e:
        import pdb; pdb.set_trace()
        raise
    return result


if __name__ == "__main__":
    classes = Counter()
    i = 0
    limit = int(float(config['DEFAULT']['limit']))
    # for entry in os.listdir(dataset_path)[:limit]:
    total_entries = len(os.listdir(dataset_path))
    widgets = [
        'Processed: ', progressbar.Percentage(), 
        ' (', progressbar.FormatLabel('%(value)d / {} lines'.format(total_entries)), 
        ' in: ', progressbar.ETA(), ')'
    ]
    pbar = progressbar.ProgressBar(widgets=widgets, maxval=len(os.listdir(dataset_path)))
    for entry in pbar(os.listdir(dataset_path)):
        res = get_entry(os.path.join(dataset_path, entry))
        r = RekorEntry(res)
        classes[r._type] += 1
        

    with open("type_breakdown.json", 'w') as fp:
        json.dump(classes, fp)
    log(classes)
    log(f"Total counts in classes: {classes.total()}")
    log(f"Count of signature_without_cert: {signature_without_cert}")
