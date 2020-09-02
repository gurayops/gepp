#!/usr/bin/env python3

import os
import subprocess
import tarfile
import io
import jinja2
import git
import docker

# For generating names from directory names and user input
from slugify import slugify

# bullet, prompt_toolkit, cmd, cmd2, click
from prompt_toolkit.completion import WordCompleter

# Print flush default
import functools
print = functools.partial(print, flush=True)

# Flow Definitions
YAMLParts = {
    "deployment": [
        {
            "name": "metadata",
            "template": "...",
            "rendered": ""
        },
        {
            "name": "spec",
            "template": "...",
            "rendered": ""
        }
    ]
}

serviceTypes = {
    "ClusterIP: Load balance internal requests. No external access.": "ClusterIP",
    "NodePort: All from ClusterIP + external by opening a port from all Kubernetes nodes.": "NodePort",
    "LoadBalancer: All from NodePort + try to get a loadbalancer IP from provider. Mostly useful for managed K8s": "LoadBalancer",
    "Headless: Don't create load balancer, only return IPs of all backends": "Headless"
}

portTypes = {
    "TCP (Default)": "TCP",
    "UDP": "UDP",
    "SCTP": "SCTP"
}

resourceConstraints = {
    "requests": {"cpu": "10m", "memory": "50Mi"},
    "limits": {"cpu": "100m", "memory": "500Mi"}
}

environmentDefinitions = {"PYTHON_DEBUG": "0"}

secretDefinitions = [
    {
        "name": "prod-jwt-token",
        "key": "secret",
        "path": "/secrets/jwt"
    }
]


def get_stack(instance_type="Standard_D2_v2",
              cluster_name="gepp-kube-cluster",
              cluster_dns_prefix="gepp",
              cluster_location='East US',
              resource_group_name='gepp'):
    # Terraform CDK imports
    from imports.azurerm import \
        AzurermProvider, \
        ResourceGroup, \
        KubernetesCluster, \
        KubernetesClusterDefaultNodePool, \
        KubernetesClusterIdentity, ResourceGroupConfig, AzurermProviderConfig, AzurermProviderFeatures
    from cdktf import App, TerraformStack, TerraformOutput
    from constructs import Construct

    class TFStack(TerraformStack):
        def __init__(self, scope: Construct, ns: str):
            super().__init__(scope, ns)

            # define resources here
            features = AzurermProviderFeatures()
            provider = AzurermProvider(self, 'azure', features=[features])

            node_pool = KubernetesClusterDefaultNodePool(
                name='default', node_count=1, vm_size='${var.instance_type}')

            # resource_group = ResourceGroup(
            #    self, name='gepp', location='East US', id='')
            resource_group = ResourceGroupConfig(
                name='${var.resource_group}', location='${var.cluster_location}')

            identity = KubernetesClusterIdentity(type='SystemAssigned')

            cluster = KubernetesCluster(
                self, cluster_name,
                name=cluster_name,
                default_node_pool=[node_pool],
                dns_prefix=cluster_dns_prefix,
                location=resource_group.location,
                resource_group_name=resource_group.name,
                identity=[identity],
                tags={"genarated": "gepp"}
            )

            kubeconfig = TerraformOutput(
                self, 'kubeconfig',
                value=cluster.kube_config_raw,
                sensitive=True
            )

            self.add_override(path='variable', value={
                "cluster_size": {
                    "description": "Number of nodes that will be in default pool",
                    "type": "number",
                    "default": 3
                },
                "instance_type": {
                    "description": "Instance type",
                    "type": "string",
                    "default": instance_type
                },
                "cluster_location": {
                    "description": "Location of the cluster",
                    "type": "string",
                    "default": cluster_location
                },
                "resource_group": {
                    "description": "Azure resource group name for cluster to be created in",
                    "type": "string",
                    "default": resource_group_name
                }
            })

    return TFStack


def generate_default_config():
    """Generates default config and return it"""
    pass


def get_interactive_config():
    """Asks questions to the user and gets config values"""
    pass


def doesFileExist(fileName):
    return os.path.exists(os.path.join(os.getcwd(), fileName))


def create_k8s_dir(dirname='kubernetes'):
    if not doesFileExist(dirname):
        os.mkdir(os.path.join(os.getcwd(), dirname))


def check_and_create(fileName, templates, templateName, emoji='', vars={}):
    print(f'{emoji} Checking for {fileName}... ', end='')
    if not doesFileExist(fileName):
        print('Not found. ❌')

        print(f'   - Creating {fileName}... ', end='')
        content = templates.get_template(
            f'{templateName}').render(**vars) + '\n'

        print('Writing...', end='')
        path = os.path.join(os.getcwd(), f'{fileName}')
        with open(path, 'w') as df:
            df.write(content)
        print('Done! ✅')
    else:
        print('Found. ✅')


def get_main():
    if not doesFileExist('main.py'):
        print('Not found  ❌')
        # TODO: get main file's name
        raise NameError('Couldnt found main')
    else:
        print('Present. ✅')
        return 'main.py'


def build_image(org='', repo='gepp', tag='latest'):
    client = docker.from_env()
    tag = f'{repo}:{tag}' if not org else f'{org}/{repo}:{tag}'
    try:
        serverVersion = client.version()['Components'][0]['Version']
        print(f'Connected Docker version {serverVersion} ✅')
    except:
        print('Couldnt connect to Docker daemon. Passing image build phase')
        return
    try:
        print('   - Starting build... ', end='')
        client.images.build(path=os.getcwd(), tag=tag)
        print('Done! ✅')
        print(f'   - Tagget with \033[1m{tag}\033[0m ✅')
    except Exception as e:
        print(
            'Image could not be built. ❌ The error -for information- is below.')
        print(str(e), end='...')
        print(' Continuing...')
    return tag


def create_k3d_cluster(name, images=[]):
    print(
        f'   - Checking existing ones "k3d cluster list {name}" ', end='')
    result = subprocess.run(['k3d', 'cluster', 'list', name],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    clusterExists = False
    # Already exists
    if result.stderr:
        print('Not found, creating a new one.')
    else:
        print('Found. Continuing... ✅')
        clusterExists = True

    if not clusterExists:
        print(f'   - Running "k3d cluster create {name}"... ', end='')
        result = subprocess.run(
            [
                'k3d', 'cluster', 'create', '-p', '80@loadbalancer', '-p', '443@loadbalancer', name
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if result.stderr:
            print('Got error. ❌ Details:')
            print(result.stderr.decode(), '\n', '-' * 20)
            return False
        print('Done! ✅')

    print('   - Creating/Merging ./kubeconfig file... ', end='')
    result = subprocess.run(['k3d', 'kubeconfig', 'merge', name, '-o', './kubeconfig'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.stderr:
        print(f'Could not write Kubeconfig. Error details:', result.stderr)
        print(result.stderr.decode(), '\n', '-' * 20)
        return False
    print('Saved. ✅')

    for imageTag in images:
        print(f'   - Importing image {imageTag} to the cluster... ', end='')
        result = subprocess.run(['k3d', 'image', 'import', imageTag, '-c', name],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.stderr:
            print('Got error. ❌ Details:')
            print(result.stderr.decode(), '\n', '-' * 20)
            return False
        print('Done. ✅')

    return True


def get_k3d_info(cluster_name: str):
    """
    Returns exposed port list from k3d Docker LB container.
    """
    containerName = f'k3d-{cluster_name}-serverlb'
    containerPorts = (80, 443, 6443)
    exposedPorts = {}

    # TODO: make this part a function or method
    client = docker.from_env()
    try:
        serverVersion = client.version()['Components'][0]['Version']
    except:
        print('Couldnt connect to Docker daemon. Passing image build phase')
        return

    loadbalancer = client.containers.get(containerName)
    for pair in loadbalancer.ports.items():
        exposedPorts[pair[0].split('/')[0]] = pair[1][0]['HostPort']

    return exposedPorts


def deploy_to_k8s(appName):
    print('   - Creating a temp container with kubectl... ', end='')

    client = docker.from_env()
    
    try:
        deployContainer = client.containers.run(
            image='guray/gepp-kubectl:v1.18.6',
            environment=['KUBECONFIG=/kubeconfig'],
            network=f'k3d-{appName}',
            remove=True,
            detach=True
        )

        print(f'Named: {deployContainer.name}. Done!')
    
    except Exception as err:
        print(err)


    print('   - Copying K8s object YAMLs and kubeconfig to temp container... ', end='')
    # Send YAMLs and kubeconfig
    tempFile = io.BytesIO()
    tarFile = tarfile.open(fileobj=tempFile, mode='w')
    tarFile.add('kubernetes')
    tarFile.add('kubeconfig')
    tarFile.close()
    tempFile.seek(0)
    deployContainer.put_archive('/', tempFile)

    # Switch DNS and port to match with internal network
    try:
        deployContainer.exec_run(cmd=f"sed -i -E 's/0.0.0.0\:\d+/k3d-{appName}-serverlb:6443/' /kubeconfig")
        print('Done!')
    except Exception as err:
        print(err)
    # Deploy K8s objects

    try:
        print('   - Deploying YAMLs... ', end='')
        deployContainer.exec_run(cmd="kubectl apply -f /kubernetes")
        print('Done!')
    except Exception as err:
        print(err)

    try:
        print('   - Removing temp container... ', end='')
        deployContainer.remove(force=True)
        print('Done!')
    
    except Exception as err:
        print(err)
    
    return True


def generate_terraform(appName):
    from cdktf import App
    app = App(stack_traces=False)
    stack = get_stack()
    stack(app, appName)
    """
    TODO: add input variables
    stack.add_override(path='variable', value={
        "tags": {
            "description": "Tags for the instance",
            "type": "map(string)"
        },
        "instance_type": {
            "description": "Instance type",
            "type": "string"
        }
    })
    """
    # stack.add_override()
    print(
        f'   - Starting synth...', end='')
    app.synth()
    print('Done \033[1mAvailable in cdktf.out directory\033[0m ✅')
    print('   - Deleting .terraform symlink... ', end='')
    os.remove(os.path.join(os.getcwd(), 'cdktf.out', '.terraform'))
    print('Done ✅')
    print(
        f'   - You may edit \033[1mcdk.tf.json\033[0m and run \033[1mterraform init, \
terraform plan, and terraform apply\033[0m in cdktf.out directory according to your needs.')


def main():

    ##### Defaults #####
    interactive = False
    # Get current commit:
    try:
        currentCommit = git.Repo(os.getcwd()).head.commit.hexsha
    except:
        currentCommit = None

    tempVars = {
        'appObject': 'app',
        'appName': 'app',
        'mainFile': 'main.py',
        'appPort': 80,
        'codeDir': '.',
        'dependencyFile': 'requirements.txt',
        'baseImage': 'python:3-alpine3.12',
        'currentCommit': currentCommit[:8] if currentCommit else 'latest',
        'baseDir': os.path.basename(os.getcwd()),
        'imageWorkDir': '/code',
        'userID': 0,
        'ports': [],
        'dnsName': 'localhost'
    }
    tempVars['appName'] = slugify(os.getenv('PROJECT_NAME', 'project'))

    ##### Main session #####
    print('🙌 GEPP Starting!')

    if interactive:
        config = get_interactive_config()
    else:
        config = generate_default_config()

    templates = jinja2.Environment(
        loader=jinja2.PackageLoader(package_name='main'), autoescape=True)
    '''
    TODO: fix here to include prompt toolkit and get a list of ports

    listening = prompt(
        "Is the app listening additional ports (for exposing metrics, healthchecks etc.)?")

    if listening:
        print("it is listening!")
    '''

    print('📍 Locating main.py file... ', end='')
    try:
        mainFile = get_main()
    except:
        print('Could not get main.py, exiting.')
        import sys
        sys.exit(1)
    tempVars['mainFile'] = mainFile

    tempVars['ports'].append(
        {'name': 'http', 'protocol': 'TCP', 'port': tempVars['appPort']})
    # TODO: remove after testing
    tempVars['ports'].append({'name': 'api', 'protocol': 'TCP', 'port': 8080})

    # Check for Dockerfile and create if not exists
    check_and_create('Dockerfile', templates,
                     'Dockerfile.j2', '🐳', vars=tempVars)

    # Check for .dockerignore file and create if not exists
    check_and_create('.dockerignore', templates, 'dockerignore.j2', '🐳')

    # Build Docker image
    print('🏗  Trying Docker image build... ', end='', flush=True)
    # TODO: check whether main.py, requirements.txt exists or manually supplied
    tempVars['imageName'] = build_image(
        repo=tempVars['appName'], tag=tempVars['currentCommit'])

    print('☸️  Generating YAMLs for Kubernetes:')
    create_k8s_dir()
    check_and_create(f'kubernetes/deployment-{tempVars["appName"]}.yaml',
                     templates, 'deployment.yaml.j2', '   -', vars=tempVars)
    check_and_create(f'kubernetes/service-{tempVars["appName"]}.yaml',
                     templates, 'service.yaml.j2', '   -', vars=tempVars)
    check_and_create(f'kubernetes/ingress-{tempVars["appName"]}.yaml',
                     templates, 'ingress.yaml.j2', '   -', vars=tempVars)
    check_and_create(f'kubernetes/hp-autoscaler-{tempVars["appName"]}.yaml',
                     templates, 'hp-autoscaler.yaml.j2', '   -', vars=tempVars)

    # k3d cluster create $NAME + k3d kubeconfig get $NAME
    print('⚓ Creating a test cluster with k3d')
    create_k3d_cluster(tempVars['appName'], images=[tempVars['imageName']])

    # Get exposed port list and print
    exposedPorts = get_k3d_info(tempVars['appName'])
    print(
        f'   - Connect to Kubernetes Ingress via HTTP using \033[1mhttp://localhost:{exposedPorts["80"]}\033[0m')
    print(
        f'   - Connect to Kubernetes Ingress via HTTPS using \033[1mhttps://localhost:{exposedPorts["443"]}\033[0m')

    print('🚀 Deploying apps to Kubernetes')
    deploy_to_k8s(tempVars['appName'])

    print('📦 Generating Terraform file for Azure Kubernetes Service')

    generate_terraform(tempVars['appName'])

    print('Done! ✅')


if __name__ == '__main__':
    main()
