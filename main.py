#!/usr/bin/env python3
import jinja2
import os

# bullet, prompt_toolkit, cmd, cmd2, click
from prompt_toolkit.completion import WordCompleter

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


def check_and_create(fileName, templates, templateName, emoji='', vars={}):
    print(f'{emoji} Checking for {fileName}... ', end='')
    exists = os.path.exists(os.path.join(os.getcwd(), fileName))
    if not exists:
        print('Not found. ❌')

        print(f'⛵ Creating {fileName}... ', end='')
        content = templates.get_template(f'{templateName}').render() + '\n'

        print('Writing...', end='')
        path = os.path.join(os.getcwd(), f'{fileName}')
        with open(path, 'w') as df:
            df.write(content)
        print('Done! ✅')
    else:
        print('Found. ✅')
    pass


def main():
    print('🙌 GEPP Starting!')
    templates = jinja2.Environment(
        loader=jinja2.PackageLoader(package_name='main'), autoescape=True)
    '''
    listening = prompt(
        "Is the app listening additional ports (for exposing metrics, healthchecks etc.)?")

    if listening:
        print("it is listening!")
    '''

    # Check for Dockerfile and create if not exists
    check_and_create('Dockerfile', templates, 'Dockerfile.j2', '🐳')

    # Check for .dockerignore file and create if not exists
    check_and_create('.dockerignore', templates, 'dockerignore.j2', '🐳')

    print('Done! ✅')

    # print(Dockerfile)
    # print(DockerIgnore)


if __name__ == '__main__':
    main()
