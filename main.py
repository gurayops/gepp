#!/usr/bin/env python3
import os
import jinja2
import git
import docker
import subprocess

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


def generate_default_config():
    """Generates default config and return it"""
    pass


def get_interactive_config():
    """Asks questions to the user and gets config values"""
    pass


def doesFileExist(fileName):
    return os.path.exists(os.path.join(os.getcwd(), fileName))


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
        result = subprocess.run(['k3d', 'cluster', 'create', name],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.stderr:
            print('Got error. ❌ Details:')
            print(result.stderr.decode(), '\n', '-' * 20)
            return False
        print('Done! ✅')

    print('   - Creating/Merging ./kubeconfig file with the new config... ', end='')
    result = subprocess.run(['k3d', 'kubeconfig', 'merge', name, '-o', './kubeconfig'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.stderr:
        print(f'Could not write Kubeconfig. Error details:', result.stderr)
        print(result.stderr.decode(), '\n', '-' * 20)
        return False
    print('Saved. ✅')

    for imageTag in images:
        print(f'   - Importing image {imageTag} to the cluster... ', end='')
        result = subprocess.run(['k3d', 'image', 'import', imageTag, '-c', 'rastgelesayi'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.stderr:
            print('Got error. ❌ Details:')
            print(result.stderr.decode(), '\n', '-' * 20)
            return False
        print('Done. ✅')

    return True


def main():

    ##### Defaults #####
    interactive = False
    # Get current commit:
    try:
        currentCommit = git.Repo(os.getcwd()).head.commit.hexsha
    except:
        currentCommit = None

    tempVars = {
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
    tempVars['appName'] = slugify(tempVars['baseDir'])

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
    check_and_create(f'kubernetes/deployment-{tempVars["appName"]}.yaml',
                     templates, 'deployment.yaml.j2', '   -', vars=tempVars)
    check_and_create(f'kubernetes/service-{tempVars["appName"]}.yaml',
                     templates, 'service.yaml.j2', '   -', vars=tempVars)
    check_and_create(f'kubernetes/ingress-{tempVars["appName"]}.yaml',
                     templates, 'ingress.yaml.j2', '   -', vars=tempVars)
    check_and_create(f'kubernetes/hp-autoscaler-{tempVars["appName"]}.yaml',
                     templates, 'hp-autoscaler.yaml.j2', '   -', vars=tempVars)
    # ⚓ 🚀📦☸️

    # k3d cluster create $NAME + k3d kubeconfig get $NAME
    print('⚓ Creating a test cluster with k3d')
    create_k3d_cluster(tempVars['appName'], images=[tempVars['imageName']])

    print('Done! ✅')


if __name__ == '__main__':
    main()
