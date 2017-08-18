# Ansible WASCloud Module


## Synopsis

* This module allows Ansible to interface with the [IBM WebSphere Application Server in Bluemix](https://console.bluemix.net/docs/services/ApplicationServeronCloud/index.html) service broker
* The module can be used to create, delete and get information about existing WAS Instances in available Bluemix regions.


## Requirements (on the host that executes the module)
* python >= 2.7
* requests
* To work on the websphere instance you will need an OpenVPN connection to WebSphere region. Information on setting up the OpenVPN connection [here](https://console.bluemix.net/docs/services/ApplicationServeronCloud/systemAccess.html#setup_openvpn)
  - This is *not* required to work with the service broker, i.e. create / delete / get information about WAS Service instances


## Options

parameter   | required | default | choices | comments
------------|-------|-----------|-----------|----------
region      | yes  |         | <ul><li>ng</li><li>eu-gb</li><li>au-syd</li><li>eu-de</li></ul> | Bluemix region to stand up WAS Instance
org         | yes  |         |              | Bluemix organisation
space       | yes  |         |              | Bluemix space
apikey      | yes  |         |              | Bluemix API key. Instructions to obtain [here](https://console.bluemix.net/docs/iam/apikeys.html#manapikey)
name        | yes  |         |              | Name of the WAS Service Instance to create, delete or get information about
state       | no   | present | <ul><li>present</li><li>absent</li><li>latest</li><li>reloaded</li></ul> | Target state of the WAS instance. Present will return a resource object if the resources are ready, either by selecting _wait_ or if the resource already exists. _latest_ (and reloaded alias) will delete existing instance before creating new one. absent deletes instance if it exists
type        | no   |         |              | Type of WAS Instance as supported by the WAS Broker. Currently supported: LibertyCollective, LibertyCore, LibertyNDServer, WASBase, WASCell or WASNDServer<br>Required with state = present or latest/reloaded
size        | no   |         | <ul><li>S</li><li>M</li><li>L</li><li>XL</li><li>XXL</li></ul> | Size of application server VM(s)<br>Required with state = present or latest/reloaded
controller_size | no |       | <ul><li>S</li><li>M</li><li>L</li><li>XL</li><li>XXL</li></ul> | Size of controller VM. Required when type = WASCell or LibertyCollective. 
app_vms     | no  |         |               | Number of Application VMs to provision. Required when type = WASCell or LibertyCollective.
software_level | no | 9.0.0 | <ul><li>8.5.5</li><li>9.0.0</li></ul> | Software Level of WAS. Only valid for type =  WASBase, WASCell and WASNDServer
wait        | no  | false   | <ul><li>true</li><li>false</li></ul> | Wait for newly created instance resources to be available. Valid for state = present and latest/reloaded. 
public_ip   | no  | false   | <ul><li>true</li><li>false</li></ul> | Request and open public IP address for the instance. Will force wait for provisioning to complete.

## Examples
```
  - hosts: localhost
    connection: local
    gather_facts: False
    vars_files: 
    - bluemix-vars.yaml

    tasks:

    - name: create instance
      wascloud_instance:
        state: latest
        name: "{{ was_instance_name }}"
        instance_type: WASBase
        size: s
        region: "{{ region }}"
        org: "{{ org }}"
        space: "{{ space }}"
        apikey: "{{ apikey }}"
        wait: True
      register: was_instance
    
    - name: Add new instance to host group
      add_host:
        hostname: "{{ item.osHostname }}"
        groupname: launched
        ansible_user: "{{ item.osAdminUser }}"
        ansible_ssh_pass: "{{ item.osAdminPassword }}"
        ansible_ssh_common_args: "-o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no"
        wasadmin: "{{ item.wasAdminUser }}"
        wasadminpass: "{{ item.wasAdminPass }}"
      with_items: "{{ was_instance.resources }}"
    - name: Wait for ssh to become available
      wait_for:
        host: "{{ item.osHostname }}"
        port: 22
        sleep: 2
        timeout: 300
        state: started
      with_items: "{{ was_instance.resources }}"

      
  - hosts: launched
    gather_facts: True
    vars_files: 
    - db-vars.yaml

    roles:
    - my_important_role
    - my_important_tests
```

### How to use the examples in the git repository

1. ```git clone <repository link>```
2. ```cd <repository directory>```
3. Edit bluemix-vars.yaml with your own credential information
4. ```ansible-playbook -i localhost examples/simple_smallwasbase_create_only.yaml```
5. ```ansible-playbook -i localhost examples/simple_refresh_smallwasbase.yaml```
6. ```ansible-playbook -i localhost examples/simple_delete_only.yaml```
7. ```ansible-playbook -i localhost examples/advanced_create_and_configure.yaml```

## Return values

name | description      | returned  | type  | sample
-----|------------------|-----------|-------|-------
instance_deleted | Whether an instance was deleted during the task run | always | boolen | 
resources | information about the VM(s) of the WAS Service instance. If the service instance is not ready an empty list is returned. | always | list of dicts |  [<br />{<br />"WASaaSResourceID": "33a7f6d1-f33e-439b-98d9-ce4412e48591", <br />"creationTime": "08-10-2017 22:33:18", <br />"disk": 12.0, <br />"expireTime": null, <br />"ifixinfo": [], <br />"keyStorePassword": "p9N2ZmXf", <br />"machinename": "tWAS Base (RHEL 6.8, WebSphere 9004 and JDK 8) 17.13", <br />"machinestatus": "RUNNING", <br />"memory": 2048, <br />"osAdminPassword": "aa58786a", <br />"osAdminUser": "root", <br />"osHostname": "169.44.39.132",  <br />"osType": "RHEL 6.8 X64", <br />"vcpu": 1, <br />"virtuserPrivateSshKey": "-----BEGIN RSA PRIVATE KEY-----privatekeystring==\n-----END RSA PRIVATE KEY-----\n", <br />"vpnConfigLink": "https://wasaas-broker.ng.bluemix.net:443/wasaas-broker/consumerPortal/openvpn/openvpnConfig.zip", <br />"wasAdminPass": "ed85b817", <br />"wasAdminUser": "wsadmin", <br />"waslink": "http://169.44.39.132:9060/ibm/console"<br />}<br />]<br />




