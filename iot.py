import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

import click
import paramiko
import requests

from scp import SCPClient

BUTTON_WIFI_URI = 'http://192.168.4.1/config/wifi'
BUTTON_HUB_URI = 'http://192.168.4.1/config/iothub'
BUTTON_CONFIG_URI = 'http://192.168.4.1/config/opsmode'
BUTTON_HEADERS = {'Content-type':'application/json', 'Accept':'application/json'}
BUTTON_WIFI_PAYLOAD = '{"ssid":"%s","password":"%s"}'
BUTTON_HUB_PAYLOAD = '{"iothub":"%s","iotdevicename":"%s","iotdevicesecret":"%s"}'
BUTTON_CONFIG_PAYLOAD = "{'opsmode':'client'}"

FUNCTION_APP_INDEX_JS_FILE = """module.exports = function (context, IoTHubMessages) {
    context.log(`JavaScript eventhub trigger function called for message array ${IoTHubMessages}`);

    IoTHubMessages.forEach(message => {
    context.log(`Processed message ${message}`);
    });

    context.done();
    }"""
FUNCTION_APP_JSON_FILE = """{
    "disabled": false,
    "bindings": [
        {
        "authLevel": "anonymous",
        "type": "eventHubTrigger",
        "direction": "in",
        "name": "IoTHubMessages",
        "path": "%s",
        "connection": "AzureIoTHubEventHubConnectionString",
        "cardinality": "many",
        "consumerGroup": "$Default"
        }
    ]
    }"""

SCRIPTS_ZIP_URI = 'http://iotcompanionapp.blob.core.windows.net/scripts/scripts.zip'
LOCATION_OPTIONS = [
    'eastus', 'eastus2', 'centralus', 'southcentralus', 'westcentralus', 'westus',
    'westus2', 'canadaeast', 'canadacentral', 'brazilsouth', 'northeurope',
    'westeurope', 'ukwest', 'uksouth', 'germanycentral', 'germanynortheast',
    'southeastasia', 'eastasia', 'australiaeast', 'australiasoutheast', 'centralindia',
    'southindia', 'japaneast', 'japanwest', 'koreacentral', 'koreasouth'
]

CONTAINER_REGISTRY_SKUS = ['Basic', 'Standard', 'Premium', 'Classic']

DEVICE_TAGS_JSON = """{'id': '%s','description': 'Raspberry Pi 3','credentials': {'user': '%s','password': '%s'}}"""

class Iot(object):
    """Context for IoT settings."""

    def __init__(self):
        self.config = {}

    def set_config(self, key, value):
        self.config[key] = value

    def __repr__(self):
        return '<IoT %r>' % self.config

pass_iot = click.make_pass_decorator(Iot)

def run_command_with_stderr(command):
    """Runs a command in a shell using subprocess.Popen.
    Returns stdout and stderr as outputs."""
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (stdout, stderr) = p.communicate()
    return stdout, stderr

def run_command_with_stderr_json_out(command):
    """Runs a command in a shell using subprocess.Popen.
    Loads stdout (JSON) into a python dict, and decodes stderr to a UTF-8 string"""
    out, err = run_command_with_stderr(command)
    if out == b'' or out == '' or out is None:
        return None, err.decode("utf-8")
    return json.loads(out), err.decode("utf-8")

def set_missing_parameters(iot):
    """Queries Azure for mising parameters like iothub hostname, keys,
    and connection_string"""
    if 'hostname' not in iot.config:
        hub_info, err = run_command_with_stderr_json_out(
            "az iot hub show --resource-group %s --name %s" %
            (iot.config['rgroup'], iot.config['iothub']))
        if err:
            click.secho(err)
            sys.exit(1)
        iot.set_config("hostname", hub_info["properties"]["hostName"])

    if 'key' not in iot.config:
        existingDevice, err = run_command_with_stderr_json_out(
            "az iot hub device-identity show --resource-group %s --hub-name %s --device-id %s " %
            (iot.config['rgroup'], iot.config['iothub'], iot.config['device']))
        if err:
            click.secho(err)
            sys.exit(1)
        iot.set_config("key", existingDevice["authentication"]["symmetricKey"]["primaryKey"])

    device_info, err = run_command_with_stderr_json_out(
        'az iot hub device-identity show-connection-string --resource-group %s --hub-name %s '
        '--device-id %s' % (iot.config['rgroup'], iot.config['iothub'],
                            iot.config['device']))
    if err:
        click.secho(err)
        sys.exit(1)

    iot.set_config("cs", device_info["cs"])

    hub_info, err = run_command_with_stderr_json_out(
        'az iot hub show-connection-string --resource-group %s --hub-name %s' %
        (iot.config['rgroup'], iot.config['iothub']))

    # stderr actually contains something here on success so check in opposite order
    if hub_info and "cs" in hub_info:
        iot.set_config("hub_cs", hub_info["cs"])
    else:
        click.secho(err)
        sys.exit(1)

def prompt_for_resource_group(iot):
    """Prompts the user for a Resource Group if one isn't passed in"""
    name = click.prompt("Enter a Resource Group name")
    # check for existence of group
    exists = os.popen('az group exists -n '+ name).read().rstrip()

    if exists == 'false':
        click.secho("Resource Group with name '%s' does not exist. Creating a new Resource Group..." % name)
        location = click.prompt(
            "Specify the location (e.g. 'westus') where the Resource Group should be created",
            type=click.Choice(LOCATION_OPTIONS))
        _, err = run_command_with_stderr('az group create -n %s -l %s' % (name, location))
        if err:
            click.secho(err)
            sys.exit(1)
        else:
            iot.set_config("location", location)
            click.secho("Created a new Resource Group '%s'" % name)

    elif exists == 'true':
        click.secho("Using existing Resource Group with name '%s'." % name)

    else:
        click.secho("Error checking for resource group existence")
        sys.exit(1)

    iot.set_config("rgroup", name)
    click.secho("")

def prompt_for_iothub(iot):
    """Prompts the user for an IoT Hub if one isn't passed in"""
    #TODO: deal with clashes both in terms of globally unique names, sku clashes etc
    # right now any error will result in retries
    while True:
        name = click.prompt("Enter an IoT Hub name")
        exists, err = run_command_with_stderr_json_out(
            "az iot hub show --resource-group %s --name %s" %
            (iot.config['rgroup'], name))
        if not exists:
            click.secho("IoTHub with name '%s' does not exist. Creating a new IoTHub..." % name)
            output, err = run_command_with_stderr_json_out(
                "az iot hub create --resource-group %s --name %s --sku %s" %
                (iot.config['rgroup'], name, iot.config['iothub_sku']))
            if output and "properties" in output and "hostName" in output["properties"]:
                click.secho("Created a new IoTHub '%s'" % name)
                hostName = output["properties"]["hostName"]
                break
            elif 'Bad Request' in err and '400 Client Error' in err and iot.config['iothub_sku'] == 'F1':
                sku = click.prompt('Unable to use the Free Tier (F1) IoT Hub SKU. '
                                   'Please choose a different SKU', type=click.Choice(['S1', 'S2', 'S3']))
                iot.set_config("iothub_sku", sku)
            else:
                click.secho(err)
        elif "properties" in exists and "hostName" in exists["properties"]:
            click.secho("Using existing IoTHub with name '%s'" % name)
            hostName = exists["properties"]["hostName"]
            break

    iot.set_config("hostname", hostName)
    iot.set_config("iothub", name)
    click.secho("")

def prompt_for_device(iot, subcommand):
    """Prompts the user for an IoT Hub Device if one isn't passed in"""
    #TODO: deal with specific errors right now any error will result in retries
    existingDevice = None
    while existingDevice is None:
        name = click.prompt("Enter an IoT Hub Device name")
        existingDevices, err = run_command_with_stderr_json_out("az iot hub device-identity list -g %s --hub-name %s" % (iot.config['rgroup'], iot.config['iothub']))

        for d in existingDevices:
            if d["deviceId"] == name:
                existingDevice = d
                click.secho("Using existing IoTHub Device with name '%s'" % name)

        if existingDevice is None:
            click.secho("IoTHub Device with name '%s' does not exist. Creating a new IoTHub Device..." % name)
            edgeArg = "--edge-enabled" if subcommand == "configure_device" else ""
            existingDevice, err = run_command_with_stderr_json_out(
                "az iot hub device-identity create %s --resource-group %s "
                "--hub-name %s --device-id %s" %
                (edgeArg, iot.config['rgroup'], iot.config['iothub'], name))
            if err:
                click.secho(err)
            else:
                iot.set_config("key", existingDevice["authentication"]["symmetricKey"]["primaryKey"])

    iot.set_config("device", name)
    click.secho("")

def prompt_for_container_registry(iot):
    """Prompts the user for an Azure Container Registry if one isn't passed in"""
    existingRegistry = None
    while existingRegistry is None:
        name = click.prompt("Enter a Container Registry name")

        existingRegistries, err = run_command_with_stderr_json_out("az acr list -g %s" % iot.config['rgroup'])
        for r in existingRegistries:
            if r["name"] == name:
                existingRegistry = r
                click.secho("Using existing Container Registry with name '%s'" % name)

        if existingRegistry is None:
            click.secho("Container Registry with name '%s' does not exist. Creating a new Container Registry..." % name)
            # we need to create it, prompt for sku if not specified
            if not iot.config['container_registry_sku']:
                sku = click.prompt("Specify the sku of the container registry (e.g. Basic)", type=click.Choice(CONTAINER_REGISTRY_SKUS))
                iot.set_config("container_registry_sku", sku)
            existingRegistry, err = run_command_with_stderr_json_out(
                "az acr create --name %s --resource-group %s --sku %s --admin-enabled true" %
                (name, iot.config['rgroup'], iot.config['container_registry_sku']))
            if err:
                click.secho(err)

    creds, err = run_command_with_stderr_json_out("az acr credential show --name %s --resource-group %s" % (name, iot.config['rgroup']))
    if not err:
        iot.set_config("container_registry", name)
        iot.set_config("cr_user", creds["username"])
        iot.set_config("cr_pwd", creds["passwords"][0]['value'])
        click.secho("")
    else:
        click.secho(err)
        sys.exit(1)

def createSSHClient(server, port, user, password):
    """Helper function to wrap paramiko's SSHClient"""
    try:
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(server, port, user, password)
    except paramiko.AuthenticationException:
        return None
    return client

def runSSHCommand(client, command):
    """Run a command over SSH using a paramiko SSHClient"""
    _, stdout, _ = client.exec_command(command)
    while not stdout.channel.exit_status_ready():
        if stdout.channel.recv_ready():
            data = stdout.channel.recv(1024)
            while stdout.channel.recv_ready():
                data += stdout.channel.recv(1024)
            return data
    return None


@click.group()
@click.option('--wifi-ssid', help='SSID of the WiFi Network that the device will connect to.',
              prompt="""Please enter the SSID of a WiFi Network with internet access.
Your device will be configured to connect to this WiFi network """)
@click.option('--wifi-password', hide_input=True, confirmation_prompt=True, default="",
              help='Password for the WiFi Network that the device will connect to.',
              prompt='Please enter the password for the WiFi Network with internet access')
@click.option('--resource-group', help='Resource Group Name for the device in Azure.')
@click.option('--iothub', help='IoTHub Name for the device in Azure.')
@click.option('--iothub-sku', default="F1", type=click.Choice(['F1', 'S1', 'S2', 'S3']), help='Sku for the Iot hub.')
@click.option('--device', help='Device Name for the device in Azure.')
@click.option('--container-registry', help='Container registry name for device module containers.')
@click.option('--container-registry-sku', default="Basic", type=click.Choice(CONTAINER_REGISTRY_SKUS), help='The sku of the container registry (if creating a new one).')
@click.option('--device-ip', help='IP Address of the IoT device.', default='192.168.4.1')
@click.option('--device-user', help='Username to use to connect to the device.', default='pi')
@click.option('--device-password', help='Password to use to connect to the device.', default='raspberry')
@click.option('--fn-name', help='Name for the Azure IoT Sample Function', default='sampleiotfunction')
@click.version_option('1.0')
@click.pass_context
def cli(ctx, wifi_ssid, wifi_password, resource_group, iothub, iothub_sku, device, container_registry, container_registry_sku,
        device_ip, device_user, device_password, fn_name):
    """Iot is a command line tool that showcases how to configure the Azure
    teXXmo IoT button and the Grove Starter Kit for Azure IoT Edge.
    """
    click.secho("")
    click.secho("Please ensure you are connected to a network with internet access now.")
    click.pause("Press any key to continue...")
    click.secho("")

    # Create an Iot object and remember it as as the context object.  From
    # this point onwards other commands can refer to it by using the
    # @pass_iot decorator.
    ctx.obj = Iot()
    ctx.obj.set_config('wifi_ssid', wifi_ssid)
    ctx.obj.set_config('wifi_password', wifi_password)
    ctx.obj.set_config('rgroup', resource_group)
    ctx.obj.set_config('iothub', iothub)
    ctx.obj.set_config('iothub_sku', iothub_sku)
    ctx.obj.set_config('device', device)
    ctx.obj.set_config('container_registry', container_registry)
    ctx.obj.set_config('container_registry_sku', container_registry_sku)
    ctx.obj.set_config('ip', device_ip)
    ctx.obj.set_config('username', device_user)
    ctx.obj.set_config('password', device_password)
    ctx.obj.set_config('fn_name', fn_name)

    if not ctx.obj.config['rgroup']:
        prompt_for_resource_group(ctx.obj)

    if not ctx.obj.config['iothub']:
        prompt_for_iothub(ctx.obj)

    if not ctx.obj.config['device']:
        prompt_for_device(ctx.obj, ctx.invoked_subcommand)

    set_missing_parameters(ctx.obj)


@cli.command()
@pass_iot
def configure_device(iot):
    """Configures the Grove Starter Kit for Azure IoT Edge.
    This will connect to the device, discover information about it, and
    then use that information to create and configure an IoT Edge device
    in Azure IoT Hub.
    """

    # Select or create container registry for pushing private modules, otherwise get creds for selected CR
    # This is only required in the "configure device" scenario (not "configure button")
    if not iot.config['container_registry']:
        prompt_for_container_registry(iot)
    else:
        creds, err = run_command_with_stderr_json_out("az acr credential show --name %s --resource-group %s" %
                                                      (iot.config['container_registry'], iot.config['rgroup']))
        if not err:
            iot.set_config("container_registry", iot.config['container_registry'])
            iot.set_config("cr_user", creds["username"])
            iot.set_config("cr_pwd", creds["passwords"][0]['value'])
        else:
            click.secho(err)
            sys.exit(1)

    # Update the device twin
    device_tags = DEVICE_TAGS_JSON % (iot.config['device'], iot.config['username'], iot.config['password'])
    _, err = run_command_with_stderr_json_out('az iot hub device-twin update --resource-group %s --hub-name %s --device-id %s --set tags="%s"' %
                                              (iot.config['rgroup'], iot.config['iothub'], iot.config['device'], device_tags))
    if err:
        click.secho(err)

    # Download scripts to be run on device
    # TODO: Scripts need to be updated to detect hostmanager vs hostapd on target device (and update workflow accordingly)
    try:
        urllib.request.urlretrieve(SCRIPTS_ZIP_URI, "scripts.zip")
    except BaseException as e:
        click.secho("Error in downloading scripts. Error message: " + str(e))
        return

    get_curl = 'sudo apt update && sudo apt install -y curl software-properties-common'
    unzip_scripts = 'unzip -o scripts.zip -d scripts && rm scripts.zip && chmod +x ./scripts/*.sh'
    run_script = (
        "sudo nohup ./scripts/runner.sh '%s' '%s' '%s' '%s' '%s' '%s' '%s' '%s' </dev/null >/home/pi/connect.log 2>&1 &" %
        (iot.config['wifi_ssid'], iot.config['wifi_password'], iot.config['hub_cs'], iot.config['device'],
         iot.config['cs'], iot.config['container_registry'], iot.config['cr_user'], iot.config['cr_pwd']))

    # We need to be able to connect to the device now.
    click.secho("Please connect to the SSID of your Raspberry Pi 3 now.")
    click.pause("Press any key to continue...")
    click.secho("")
    time.sleep(5) # Make sure the connection is established.

    # Copy scripts to device
    try:
        ssh = createSSHClient(iot.config['ip'], 22, iot.config['username'], iot.config['password'])
        if not ssh:
            click.secho("Failed to SSH to the Device. Please check the device-user and device-password and try again")
            return

        scp_client = SCPClient(ssh.get_transport())
        scp_client.put("scripts.zip", "scripts.zip")
        os.remove("scripts.zip")
    except BaseException as e:
        click.secho("Error in copying scripts to device. Error message: " + str(e))
        return
    try:
        click.secho("Connecting to your device and installing pre-requisites (Step 1 of 2).")
        runSSHCommand(ssh, get_curl)
        runSSHCommand(ssh, unzip_scripts)
        click.secho("Installing the required software now (Step 2 of 2). This script will exit shortly, but setup on your ")
        click.secho("device will take several minutes. Execute 'tail -f ~/connect.log' on the device to view setup progress.")
        runSSHCommand(ssh, run_script)
    except BaseException as e:
        click.secho("Failed to SSH to the Device. Please check the device-user and device-password and try again. "
                    "Error message: " + str(e))
        return


def createSampleFunctionApp(iot):
    """Helper function to create an Azure Sample Function Application once
    the button is configured"""
    existingAccount = None
    while existingAccount is None:
        name = click.prompt("Enter a Storage Account for the Sample Function")
        existingAccounts, err = run_command_with_stderr_json_out(
            "az storage account list -g %s" % iot.config['rgroup'])

        for a in existingAccounts:
            if a["name"] == name:
                existingAccount = a
                click.secho("Using existing Storage Account with name '%s'" % name)

        if existingAccount is None:
            click.secho("Storage Account with name '%s' does not exist. Creating a new Storage Account..." % name)
            existingAccount, err = run_command_with_stderr_json_out(
                "az storage account create --name %s --resource-group %s --sku Standard_LRS" %
                (name, iot.config['rgroup']))
            if err:
                click.secho(err)

    click.secho("")
    click.secho("Creating a new Sample Azure Function Application...")
    fnName = iot.config['fn_name']
    _, err = run_command_with_stderr_json_out(
        "az functionapp create -g %s -n %s -s %s -c %s" %
        (iot.config['rgroup'], fnName, name, iot.config['location'] if 'location' in iot.config else 'westus'))

    iothub, err = run_command_with_stderr_json_out("az iot hub show -n %s" % iot.config['iothub'])
    eventHubEndpoint = iothub['properties']['eventHubEndpoints']['events']['endpoint']
    eventHubPath = iothub['properties']['eventHubEndpoints']['events']['path']
    hubSubstring = iot.config['hub_cs'].split(";", 1)[1]
    settings = ("AzureIoTHubConnectionString='%s' AzureIoTHubEventHubConnectionString='Endpoint=%s;%s'" %
                (iot.config['hub_cs'], eventHubEndpoint, hubSubstring))

    cmd = ("az functionapp config appsettings set --name %s --resource-group %s --settings %s" %
           (fnName, iot.config['rgroup'], settings))
    _ = os.popen(cmd).read()

    tmpFile = os.path.join(tempfile.mkdtemp(), 'iotbuttonmyfunction.zip')
    with zipfile.ZipFile(tmpFile, 'w') as myzip:
        myzip.writestr('iotbuttonmyfunction/index.js', FUNCTION_APP_INDEX_JS_FILE)
        myzip.writestr('iotbuttonmyfunction/function.json', FUNCTION_APP_JSON_FILE % eventHubPath)

    cmd = ("az functionapp deployment source config-zip -g %s --name %s --src %s" %
           (iot.config['rgroup'], fnName, tmpFile))
    _ = os.popen(cmd).read()

    click.secho("Deployed a Sample Azure Function Application: '%s' in Resource Group: '%s'" %
                (fnName, iot.config['rgroup']))


@cli.command()
@pass_iot
def configure_button(iot):
    """Configures the Azure teXXmo IoT button.
    This will connect to the Button, and set it up so that it can be used with
    Microsoft Azure. It can also optionally deploy an Azure Function to run when
    the Button is pressed.
    """

    click.secho("Please connect to the SSID of your IoT Button now.")
    click.pause("Press any key to continue...")
    click.secho("")

    # First POST call sets the Wi-fi parameters
    data = BUTTON_WIFI_PAYLOAD % (iot.config['wifi_ssid'], iot.config['wifi_password'])
    requests.post(BUTTON_WIFI_URI, headers=BUTTON_HEADERS, data=data)

    # Second POST call sets up the button as an IoT Device
    data = BUTTON_HUB_PAYLOAD % (iot.config['hostname'], iot.config['device'], iot.config['key'])
    requests.post(BUTTON_HUB_URI, headers=BUTTON_HEADERS, data=data)

    # Third POST call puts the button into client mode
    data = BUTTON_CONFIG_PAYLOAD
    try:
        # Note: On this POST call, the button does not send any response. It just turns off AP mode.
        # This will result in an exception, but it should be safe to ignore. Learned this the hard way.
        requests.post(BUTTON_CONFIG_URI, headers=BUTTON_HEADERS, data=data)
    except BaseException as e:
        pass

    click.secho("Your Button is now connected to Azure!")
    if click.confirm('Would you like to set up a Sample Azure Function Application for the Button? (This may result in charges)'):
        click.secho("")
        createSampleFunctionApp(iot)
