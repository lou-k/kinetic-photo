ARG PYTHON_VERSION="3.7.4"
FROM python:${PYTHON_VERSION}-slim-buster

# Install the build requirements
RUN apt-get update && \
    apt-get install -y build-essential wget libgl1-mesa-dev git && \
    rm -rf /var/cache/apt /var/lib/apt/lists

# Download the models
WORKDIR /opt/BoostingMonocularDepth
RUN mkdir -p midas && wget -nv https://github.com/intel-isl/MiDaS/releases/download/v2/model-f46da743.pt -O midas/model.pt
RUN mkdir -p ./pix2pix/checkpoints/mergemodel && wget  -nv https://filebox.ece.vt.edu/~jbhuang/project/3DPhoto/model/latest_net_G.pth -O ./pix2pix/checkpoints/mergemodel/latest_net_G.pth 
RUN mkdir -p /root/.cache/torch/hub && wget -nv https://github.com/facebookresearch/WSL-Images/archive/main.zip -O /root/.cache/torch/hub/main.zip
RUN mkdir -p /root/.cache/torch/checkpoints && wget -nv https://download.pytorch.org/models/ig_resnext101_32x8-c38310e5.pth -O /root/.cache/torch/checkpoints/ig_resnext101_32x8-c38310e5.pth

# Install the build requirements
RUN apt-get update && \
    apt-get install -y libglib2.0-0 rsync && \
    rm -rf /var/cache/apt /var/lib/apt/lists

# Install python requirements
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Clode the repository
RUN cd /tmp && \
    git clone --depth 1 https://github.com/lou-k/BoostingMonocularDepth.git && \
    rsync -rav BoostingMonocularDepth /opt/ && \
    rm -rf BoostingMonocularDepth && \
    cd /opt/BoostingMonocularDepth/ && \
    git checkout 223fd2c113400e9981e5b993a27d9ffa75bb7bb7
WORKDIR /opt/BoostingMonocularDepth

ENTRYPOINT ["python", "run.py", "--data_dir", "/data/inputs", "--output_dir", "/data/outputs", "--Final", "--depthNet", "0"]
CMD []