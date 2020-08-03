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

## Another definition

CLI for Python + Flask projects
- Auto detect Flask
- Generate Dockerfile if not exists
- Create Deployment YAML
- Create autoscaler YAML
- Create service (type optional, clusterip default)
- Create ingress definition (optional)
- Deploy to K8s (optional)
- Test with port-forward
- Generate Terraform file for K8s integration + GKE/AWS/Azure/...
- Ask secret usage, getting names from K8s (optional)
- Ask disk type, size, mountpoint (optional)
- Create local cluster with kind/minikube/k3d and deploy the app onto it
- Use skaffold/telepresence to provide a complete dev environment
- Get status, logs, metrics
- Ask metric exports

Re-running should be possible, and it should check the YAMLs and other files to be idempotent
