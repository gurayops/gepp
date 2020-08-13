FROM guray/tfcdkc:0.0.14 AS cdkbuild


#RUN cdktf init --project-name iac-gcp \
#    --template python --local --disable-logging \
#    --project-description 'Deploy a basic infrastructure to GCP and run K8s, generated by GEPP'
COPY templates/cdktf-files/cdktf.json /code/
RUN cdktf get -l python


FROM python:3-alpine

ARG K3D_VERSION=v3.0.0
WORKDIR /code

# Install k3d
RUN wget https://github.com/rancher/k3d/releases/download/${K3D_VERSION}/k3d-linux-amd64 && \
    mv k3d-linux-amd64 /usr/local/bin/k3d && \
    chmod +x /usr/local/bin/k3d

# Install deps: git for GitPython / 
RUN apk add git nodejs

COPY requirements.txt /code
RUN pip install -r requirements.txt

COPY . /code

COPY --from=cdkbuild /code/imports /code/imports
COPY --from=cdkbuild /code/cdktf.json /code/cdktf.json

# Mount user's project to this location
WORKDIR /project

CMD /code/main.py