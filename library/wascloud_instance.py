from ansible.module_utils.basic import *
import time

"""
Example usage:
  wasbm_instance:
    state: present
    name: temp_dev_env
    instance_type: WASBase (valid options ['LibertyCollective', 'LibertyCore', 'LibertyNDServer', 'WASBase', 'WASCell', 'WASNDServer']
    size: M
    region: <bluemix_region>
    org: <bluemix_org>
    space: <bluemix_space>
    apikey: <bluemix api key>
    wait: True
  register: wasbm_instace

"""

def main():
  module = AnsibleModule(
      
      argument_spec     = dict(
          state         = dict(default='present', choices=['present', 'absent', 'latest', 'reloaded']),
          name          = dict(required=True),
          wait          = dict(required=False, default=False, type='bool'),
          instance_type = dict(required=False),
          size          = dict(required=False),
          app_vms       = dict(required=False, type='int'),
          controller_size= dict(required=False),
          software_level= dict(required=False),
          region        = dict(required=True),
          org           = dict(required=True),
          space         = dict(required=True),
          apikey        = dict(required=True)
      ),

      required_if       = [
                            ['instance_type', 'WASBase',           ['size']],
                            ['instance_type', 'WASCell',           ['controller_size', 'app_vms', 'size']],
                            ['instance_type', 'LibertyCollective', ['controller_size', 'app_vms', 'size']]
                          ]
  )

  regionKey     = module.params['region']
  organisation  = module.params['org']
  space         = module.params['space']
  instance_name = module.params['name']
  state         = module.params['state']
  apiKey        = module.params['apikey']
  instance_type = module.params['instance_type']
  size          = module.params['size']
  software_level= module.params['software_level']
  wait          = module.params['wait']
  
  # Get authorizatin token from Bluemix
  bx = BluemixAPI(region_key = regionKey, apiKey = apiKey)
  authorization = 'Bearer ' + bx.get_token()
  
  # Create a connection object for WebSphere in Bluemix broker
  was = WASaaSAPI(region_key = regionKey, org = organisation, space = space, si_name = instance_name, token = authorization)

  status = {}
  status['instance_deleted'] = False
  status['changed'] = False
  
  # basic validation that org/space is valid
  success, message = was.valid_connection()
  
  if not success:
    module.fail_json(msg=message, **status)
 
  # If the task includes delete, just delete right away
  if state in ['absent', 'reloaded', 'latest']:
    if was.instance_exists():
      # Attempt to delete the instance
      success, message = was.delete_instance()
      
      if success:
        status['instance_deleted'] = True
        status['changed'] = True
      else:
        module.fail_json(msg=message, **status)
      
      if state == 'absent':
        module.exit_json(msg=message, **status)

    else:
      if state == 'absent':
        module.exit_json(msg='Instance name not found', **status)


  # The instance creation part of the task  
  if state in ['present', 'latest', 'reloaded']:

    if was.instance_exists():
      
      if status['instance_deleted']:
        # We only get here with latest and reloaded when an instance already exists. 
        # Wait for it to be properly deleted.
        while was.instance_exists():
          time.sleep(10)
      else:
        # In state present we just return the resources list
        resources = was.get_resources_list()
        module.exit_json(msg='Instance by that name already exists', resources=resources, **status)

    # Basic configuration for creating service instances
    instance_config = {
        "Type": instance_type,
        "Name": instance_name,
        "ApplicationServerVMSize": size.upper()
    }
    
    if instance_type in ['WASCell', 'LibertyCollective']:
      instance_config['ControlServerVMSize'] = module.params['controller_size'].upper()
      instance_config['NumberOfApplicationVMs'] = module.params['app_vms']

    if instance_type in ['WASBase', 'WASNDServer', 'WASCell']:
      if module.params.get('software_level'):
        instance_config['software_level'] = module.params.get('software_level')

    resources = []
    success, message = was.create_instance(instance_config, wait_until_ready=wait)
    if not success:
      module.fail_json(msg=message, **status)
    else:
      resources = was.get_resources_list()
      module.exit_json(msg=message, resources=resources, **status)


'''
  if state == 'present':
    # Check if exists
    if was.instance_exists():
      resources = was.get_resources_list()
      module.exit_json(msg='Instance by that name already exists', changed=False, resources=resources)

    success, message = was.create_instance(instance_config, wait_until_ready=wait)
    resources = was.get_resources_list()
    # Create a new instance, and grab the virtuser ssh certificate
    module.exit_json(msg=message, changed=success, resources=resources)
    
  if state == 'latest' or state == 'reloaded':
    if was.instance_exists():
      was.delete_instance()
      was.sid = ''
    
    success, message = was.create_instance(instance_config, wait_until_ready=wait)
    if not success:
      module.fail_json(msg=message)
    else:
      resources = was.get_resources_list()
      module.exit_json(msg=message, changed=success, resources=resources)
'''

def validate_input(module):
  
  if module.params.get('state') == 'absent':
    # No validation required to delete service instance
    return True
    
  if module.params.get('instance_type') == 'WASBase':
    incompatibles = ['ControlServerVMSize', 'NumberOfApplicationVMs']
    required = ['size']
    
  if module.params.get('instance_type') == 'WASCell':
    required = ['ControlServerVMSize', 'size', 'NumberOfApplicationVMs']
    
  
  if module.params.get('instance_type') == 'LibertyCollective':
    required = ['ControlServerVMSize', 'size', 'NumberOfApplicationVMs']
    
  return True

        
import requests
import base64
class BluemixAPI:

  def __init__(self, region_key, apiKey):
   
    self.access_token = ''
    self.refresh_token = ''
    self.region_keys = ['ng', 'eu-gb']
    self.region_key = ''
    self.apiKey = ''

    self.region_key = region_key
    self.apiKey = apiKey
    self.fetch_token()

  def fetch_token(self):
    headers = {
      'Content-Type': 'application/x-www-form-urlencoded', 
      'Accept': 'application/json',
      'Authorization': 'Basic ' + base64.b64encode('bx:bx')}

    data='apikey=%s&grant_type=urn:ibm:params:oauth:grant-type:apikey&response_type=cloud_iam,uaa&uaa_client_id=cf&uaa_client_secret=' % self.apiKey
    
    url = 'https://iam.%s.bluemix.net/oidc/token' % self.region_key
    
    r = requests.post(url, data=data, headers=headers)
    
    if r.status_code == 200:
      self.access_token = r.json()['uaa_token']
      self.refresh_token = r.json()['uaa_refresh_token']
    else:
      print r.text
  
  def get_token(self):
    if self.access_token == '':
      self.fetch_token()
      
    return self.access_token

import requests

class WASaaSAPI:

  def __init__(self, region_key, org, space, si_name = '', token = '', refresh_token = ''):    
    self.token = token
    self.si_name = si_name
    self.sid = ''
    self.resources_raw = []
    self.adminip = ''
    self.wsadmin_user = ''
    self.wsadmin_pass = ''
    self.vpnConfig_link = ''
    self.space = space
    self.org = org
    self.regionKey = region_key
    self.appserver_size = ''
    self.instance_type = ''
    self.software_level = ''
    # Available Environments:
    # Dallas - https://wasaas-broker.ng.bluemix.net/wasaas-broker/api/v1
    # London - https://wasaas-broker.eu-gb.bluemix.net/wasaas-broker/api/v1
    # Sydney - https://wasaas-broker.au-syd.bluemix.net/wasaas-broker/api/v1
    # Frankfurt - https://wasaas-broker.eu-de.bluemix.net/wasaas-broker/api/v1
    regions = {
      'ng': 'https://wasaas-broker.ng.bluemix.net/wasaas-broker/api/v1',
      'eu-gb': 'https://wasaas-broker.eu-gb.bluemix.net/wasaas-broker/api/v1',
      'eu-de': 'https://wasaas-broker.eu-de.bluemix.net/wasaas-broker/api/v1',
      'au-syd': 'https://wasaas-broker.au-syd.bluemix.net/wasaas-broker/api/v1'
    }
    self.baseUrl = regions[self.regionKey]
    self._headers={
      'authorization': self.token,
      'Accept': 'application/json'
    }

  def create_instance(self, config, wait_until_ready = False):

    url = self.baseUrl + '/organizations/{0}/spaces/{1}/serviceinstances'.format(self.org, self.space)
    r = requests.post(url, json=config, headers=self._headers)
    if r.status_code != 200:
      return False, r.text
    else:
      self.sid = r.json()['ServiceInstance']['ServiceInstanceID']
      if not wait_until_ready:
        return True, 'Instance requested'
      else:
        while not self.instance_ready():
          time.sleep(10)
        return True, 'Instance ready'
      
  def instance_ready(self):
    url = self.baseUrl + '/organizations/%s/spaces/%s/serviceinstances/%s/resources' % (self.org, self.space, self.sid)
    r = requests.get(url, headers=self._headers)
    if r.status_code != 200:
      print 'Error retrieving service instances. '
      print 'Server returned status code: %s' % r.status_code
      print r.text
      return False   
    
    if len(r.json()) >= 1:
      return True
    else:
      return False
    
  def delete_instance(self):
    if self.sid == '':
      self.fetch_resource_details()
    
    url = self.baseUrl + '/organizations/%s/spaces/%s/serviceinstances/%s' % (self.org, self.space, self.sid)
    r = requests.delete(url, headers=self._headers)
    if r.status_code == 204:
      self.sid = ''
      return True, 'Instance deleted'
    else:
      return False, r.text
  
  #### Not used yet. Method for downloading zip with openvpn certificates and config for the region  
  def get_vpnConfig_zip(self):
    if self.sid == '':
      self.fetch_resource_details()
    
    url = self.baseUrl + '/organizations/%s/spaces/%s/serviceinstances/%s/vpnconfig' % (self.org, self.space, self.sid)
    r = requests.get(url, headers=self._headers)
    if r.status_code != 200:
      print 'Error retrieving service instance vpn configuration. '
      print 'Server returned status code: %s' % r.status_code
      print r.text
      return False   
    
    return r.json()['VpnConfig']

  # basic validation that org/space is valid
  def valid_connection(self):
    success, message = self.get_serviceinstances(self.org, self.space)
    if success:
      return True, ''
    else:
      return False, message


  def instance_exists(self):
    success, sis = self.get_serviceinstances(self.org, self.space)
    for s in sis:
      if not 'Name' in s['ServiceInstance']:
        # Some instance deployment types do not seem to have these
        continue
      if s['ServiceInstance']['Name'] == self.si_name:
        # Populate sid if does not already exist
        if self.sid == '':
          self.sid = s['ServiceInstance']['ServiceInstanceID']
        return True
      
    return False

  def fetch_resource_details(self):

    if self.sid == '':
      success, sis = self.get_serviceinstances(self.org, self.space)
      si = False
      for s in sis:
        if s['ServiceInstance']['Name'] == self.si_name:
          si = s
          break
      
      if not si:
        print "Could not find service instance with name %s " % self.si_name
        return False

      # Ensure this is basic WAS as we don't support ND cluster yet
      if si['ServiceInstance']['ServiceType'] != 'WASBase':
        print "Don't support the service instance type %s " % si['ServiceInstance']['ServiceType']
        return False
      
      self.sid = si['ServiceInstance']['ServiceInstanceID']
    
    r = self.get_resources_list()
    
    self.resources_raw  = r
    self.adminip        = r[0]['osHostname']
    self.rootpassword   = r[0]['osAdminPassword']
    self.wsadmin_user   = r[0]['wasAdminUser']
    self.wsadmin_pass   = r[0]['wasAdminPass']
    self.vpnConfig_link = r[0]['vpnConfigLink']

    return True

  def get_resources_list(self):
    if len(self.resources_raw) > 0:
      return self.resources_raw
    else:
      url = self.baseUrl + '/organizations/%s/spaces/%s/serviceinstances/%s/resources' % (self.org, self.space, self.sid)
      r = requests.get(url, headers=self._headers)
      if r.status_code == 404:
        # This generally means that we're in the middle of a create or delete. For now return false
        return False
      if r.status_code != 200:
        # Catch everything else
        print 'Error retrieving service instances. '
        print 'Server returned status code: %s' % r.status_code
        print r.text
        return False
      return r.json()
    
    

  def get_resource_details(self, resourceid):

      url = baseUrl + '/organizations/%s/spaces/%s/serviceinstances/%s/resources/%s' % (self.org, self.space, self.sid, resourceid)
      r = requests.get(url, headers=self._headers)
      return r.json()
    
    

  def get_serviceinstances(self, organisation, space):

    url = self.baseUrl + '/organizations/%s/spaces/%s/serviceinstances' % (organisation, space)
    r = requests.get(url, headers=self._headers)
    if r.status_code == 200:
      return True, r.json()
    else:
      return False, r.text
      
  def get_spaces(self, organisation):

    url = baseUrl + '/organizations/%s/spaces' % (organisation)
    r = requests.get(url, headers=self._headers)
    return r.json()
      
  def get_serviceinstance_id(self, organisation, space, serviceinstance_name):
    success, serviceinstances = self.get_serviceinstances(organisation, space)    
    for si in serviceinstances:
      if si['ServiceInstance']['Name'] == serviceinstance_name:
        return si['ServiceInstance']['ServiceInstanceID']
      
    print "Could not find service instance " + serviceinstance_name
    return False
      
  def get__resource_from_id(self,organisation, space, sid):
    url = baseUrl + '/organizations/%s/spaces/%s/serviceinstances/%s/resources' % (organisation, space, sid)

  def get_serviceinstance_details(self, organisation, space, serviceinstance_name):

    success, sis = self.get_serviceinstances(organisation, space)
    for s in sis:
      if s['ServiceInstance']['Name'] == serviceinstance_name:
        si = s
        break
              
    if not serviceinstance:
      print "Could not find service instance with name %s " % serviceinstance_name
      return False
          
    # Ensure this is basic WAS as we don't support ND cluster yet
    if si['ServiceInstance']['ServiceType'] != 'WASBase':
      print "Don't support the service instance type %s " % si['ServiceInstance']['ServiceType']
      return False



if __name__ == '__main__':
    main()
