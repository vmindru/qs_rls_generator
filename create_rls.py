import boto3
import csv
from os import environ as os_environ
from os.path import basename as file_basename
from botocore.exceptions import NoCredentialsError
from sys import exit

OWNER_TAG = os_environ['CUDOS_OWNER_TAG'] if 'CUDOS_OWNER_TAG' in os_environ else 'cudos_users'
BUCKET_NAME = os_environ['BUCKET_NAME'] if 'BUCKET_NAME' in os_environ else 'BUCKET_NOT_DEFINED'
TMP_RLS_FILE = os_environ['TMP_RLS_FILE'] if 'TMP_RLS_FILE' in os_environ else '/tmp/cudos_rls.csv'
RLS_HEADER = ['UserName', 'account_id']
CUDOS_FULL_ACESS_USERS = os_environ['CUDOS_FULL_ACCESS'].split(",") if 'CUDOS_FULL_ACCESS' in os_environ else ['a']
ROOT_OU = os_environ['ROOT_OU'] if 'ROOT_OU' in os_environ else exit("Missing ROOT_OU env var, please define ROOT_OU in ENV vars")
org_client = boto3.client('organizations')
s3_client = boto3.client('s3')

#def remove_inactive_accoutns(account_list):
#    for account in account_list:
#        if account['Status'] != 'ACTIVE':
#            print("Removing inactive account: {}".format(acc['Id']))
#            account_list[account]
#        return account_list


def get_tags(account_list):
    for index, account  in enumerate(account_list):
        account_tags = org_client.list_tags_for_resource(ResourceId=account["Id"])['Tags']
        account_tags = {'AccountTags': account_tags}
        account.update(account_tags)
        account_list[index] = account
    return account_list


def  print_account_list():
    account_list = remove_inactive_accoutns(org_client.list_accounts()['Accounts'])
    account_list = get_tags(account_list)
    print(account_list)


def add_full_access_users(full_acess_user, cudos_users):
    full_acess_user = full_acess_user.strip()
    if full_acess_user in cudos_users:
        cudos_users[full_acess_user] = ' '
    else:
        cudos_users.update({full_acess_user: ' '})


def add_cudos_user_to_qs_rls(account, users, qs_rls,separator=":"):
    """ Default separator """
    users = users.split(separator)
    for user in users:
        user = user.strip()
        if user in qs_rls.keys():
           if account not in qs_rls[user]:
               qs_rls[user].append(account)
        else:
           qs_rls.update({user: []})
           add_cudos_user_to_qs_rls(account,user, qs_rls)

    return qs_rls

def get_ou_children(ou):
    NextToken = True
    ous_list = []
    while NextToken:
        if NextToken is str:
            list_ous_result = org_client.list_organizational_units_for_parent(ParentId=ou, MaxResults=20, NextToken=NextToken)
        else:
            list_ous_result = org_client.list_organizational_units_for_parent(ParentId=ou, MaxResults=20)
        if 'NextToken' in list_ous_result:
            NextToken = list_ous_result['NextToken']
        else:
            NextToken = False
            ous = list_ous_result['OrganizationalUnits']
            for ou in ous:
                ous_list.append(ou['Id'])
    return ous_list


def get_ou_accounts(ou, accounts_list=None):
    NextToken = True
    if accounts_list is None:
        accounts_list = []
    while NextToken:
        if NextToken is str:
            list_accounts_result = org_client.list_accounts_for_parent(ParentId=ou, MaxResults=20, NextToken=NextToken)
        else:
            list_accounts_result = org_client.list_accounts_for_parent(ParentId=ou, MaxResults=20)
        if 'NextToken' in list_accounts_result:
            NextToken = list_accounts_result['NextToken']
        else:
            NextToken = False
        accounts = list_accounts_result['Accounts']
        for account in accounts:
            if  account['Status'] == 'ACTIVE':
                accounts_list.append(account)
    for ou in get_ou_children(ou):
        get_ou_accounts(ou, accounts_list)
    return accounts_list


def get_cudos_users(account_list):
    cudos_users = []
    for account in account_list:
        for index, key in enumerate(account['AccountTags']):
            if key['Key'] == 'cudos_users':
                cudos_users.append((account['Id'], account['AccountTags'][index]['Value']))
    return cudos_users


def dict_list_to_csv(dict):
    for key in dict:
        dict[key]=','.join(dict[key])
    return dict


def upload_to_s3(file, s3_file):
    s3 = boto3.client('s3')

    try:
        s3.upload_file(file, BUCKET_NAME, file_basename(s3_file))
    except FileNotFoundError:
        print("The file was not found")
        return None
    except NoCredentialsError:
        print("Credentials not available")
        return None

def crawl_org(org_client):
#    for root in org_client.list_roots():
#        for ou in
#
    pass

def craw_ou(ou):
#    org_client.list_children(ou, 'ORGANIZATIONAL_UNIT')
    pass




def main():
    cudos_users = {}
    cudos_users_list = []
    account_list = get_tags(remove_inactive_accoutns(org_client.list_accounts()['Accounts']))
    cudos_users_list.extend(get_cudos_users(account_list))
    for entry in cudos_users_list:
        account = entry[0]
        users  = entry[1]
        add_cudos_user(account, users, cudos_users)
    for full_access_user in CUDOS_FULL_ACESS_USERS:
        add_full_access_users(full_access_user, cudos_users)
    cudos_users = dict_list_to_csv(cudos_users)
    with open(TMP_RLS_FILE,'w',newline='') as cudos_rls_csv:
        wrt = csv.DictWriter(cudos_rls_csv,fieldnames=RLS_HEADER)
        wrt.writeheader()
        for k,v in cudos_users.items():
            wrt.writerow({RLS_HEADER[0]: k, RLS_HEADER[1]: v})
    upload_to_s3(TMP_RLS_FILE, TMP_RLS_FILE)

def test(separator=":"):
    qs_rls = {}
    #mou =  'ou-hg33-utwcpxrb'
    root_ou = ROOT_OU
    qs_rls = process_ou(root_ou, qs_rls, root_ou)
    qs_rls = process_root_ou(root_ou,qs_rls)
    print(f"Final result of qs_rls: {qs_rls}")
    write_csv(qs_rls)



def process_account(account_id, qs_rls, ou):
    #account_id = account['Id']
    print(f"DEBUG: proessing account level tags, processing account_id: {account_id}")
    tags = org_client.list_tags_for_resource(ResourceId=account_id)['Tags']
    for tag in tags:
        if tag['Key'] == 'cudos_users':
            cudos_users_tag_value = tag['Value']
            for account in get_ou_accounts(ou):
                account_id = account['Id']
                print(f"DEBUG: processing child account: {account_id} for ou: {ou}")
                add_cudos_user_to_qs_rls(account_id, cudos_users_tag_value, qs_rls)
    return qs_rls

def process_root_ou(root_ou, qs_rls):
    tags = org_client.list_tags_for_resource(ResourceId=root_ou)['Tags']
    for tag in tags:
        if tag['Key'] == 'cudos_users':
            cudos_users_tag_value = tag['Value']
            for user in cudos_users_tag_value.split(':'):
                if user in qs_rls.keys():
                    qs_rls[user] = [' ']
                else:
                    qs_rls.update({user: ' '})
    return qs_rls


def process_ou(ou, qs_rls, root_ou):
    print("DEBUG: processing ou {}".format(ou))
    tags = org_client.list_tags_for_resource(ResourceId=ou)['Tags']
    for tag in tags:
        if tag['Key'] == 'cudos_users':
            cudos_users_tag_value = tag['Value']
            if ou != root_ou:
                for account in get_ou_accounts(ou):
                   account_id = account['Id']
                   print(f"DEBUG: processing inherit tag: {cudos_users_tag_value} for ou: {ou} account_id: {account_id}")
                   add_cudos_user_to_qs_rls(account_id, cudos_users_tag_value, qs_rls)
            else:
                pass

    children_ou = get_ou_children(ou)
    if len(children_ou) > 0:
        for ou in children_ou:
            print(f"DEBUG: processing child ou: {ou}")
            process_ou(ou, qs_rls,root_ou)

    ou_accoutns = get_ou_accounts(ou)
    print(f"DEBUG: Preparing process for noniherit accounts of ou: {ou}, accounts: {ou_accoutns}")
    for account in get_ou_accounts(ou):
        account_id = account['Id']
        process_account(account_id, qs_rls, ou)
    return qs_rls

def write_csv(qs_rls):
    print(qs_rls)
    qs_rls_dict_list = dict_list_to_csv(qs_rls)
    with open(TMP_RLS_FILE,'w',newline='') as cudos_rls_csv_file:
        wrt = csv.DictWriter(cudos_rls_csv_file,fieldnames=RLS_HEADER)
        wrt.writeheader()
        for k,v in qs_rls_dict_list.items():
            wrt.writerow({RLS_HEADER[0]: k, RLS_HEADER[1]: v})
    upload_to_s3(TMP_RLS_FILE, TMP_RLS_FILE)


    #for acc in get_ou_accounts(mou):
    #    print(acc['Id'])


def lambda_handler(event, context):
    main()

if __name__ == '__main__':
#    main()
    test()