# GEPP - Developer's Helper to K8s

GEPP provides developers to easily run their apps as containerized apps in Kubernetes. Here is what it is aiming:

- You run the tool in a directory with Python/Go/NodeJS code
- It will generate a Dockerfile depending on the framework your code uses
- It will generate YAMLs for Kubernetes deployment, pod autoscaling, service definitions (it will ask some questions like service type)
- (optional) It can generate a plan for Terraform for your cloud provider for a K8s cluster and deploying your app (in JSON, using tfcdk)
- (optional) It will insert environment variable, secretmap, configmaps to the generated YAML (interactively asks)
- (optional) It can get storageclasses from your cluster and define some storage and insert it to your YAML
- (optional) It can generate servicemonitor and podmonitor YAML files for Prometheus operator
- (optional) It can generate network policies for some of the network providers
