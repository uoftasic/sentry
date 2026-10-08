ARG VARIANT=ubuntu-24.04
FROM mcr.microsoft.com/vscode/devcontainers/base:${VARIANT}

ENV DEBIAN_FRONTEND=noninteractive
ENV PDK_ROOT=/home/vscode/ttsetup/pdk
ENV PDK=sky130A

RUN apt update
RUN apt install -y iverilog gtkwave python3 python3-pip python3-venv python3-tk python-is-python3 libcairo2 verilator libpng-dev libqhull-dev

# Clone tt-support-tools
RUN mkdir -p /ttsetup
RUN git clone https://github.com/TinyTapeout/tt-support-tools /ttsetup/tt-support-tools

COPY test/requirements.txt /ttsetup/test_requirements.txt
COPY .devcontainer/copy_tt_support_tools.sh /ttsetup

RUN python -m venv /ttsetup/venv
RUN /ttsetup/venv/bin/pip install -r /ttsetup/test_requirements.txt -r /ttsetup/tt-support-tools/requirements.txt

# Install verible (for formatting)
RUN umask 022 && \
    curl -L https://github.com/chipsalliance/verible/releases/download/v0.0-4023-gc1271a00/verible-v0.0-4023-gc1271a00-linux-static-x86_64.tar.gz | \
    tar zxf - -C /usr/local --strip-components=1 && \
    chmod 755 /usr/local/bin

# Install LibreLane
RUN /ttsetup/venv/bin/pip install librelane==3.0.14

# Install svlint
RUN apt-get update && apt-get install -y unzip && \
    curl -fsSL https://github.com/dalance/svlint/releases/download/v0.9.3/svlint-v0.9.3-x86_64-lnx.zip \
    -o /tmp/svlint.zip && \
    unzip -q /tmp/svlint.zip -d /tmp/svlint && \
    install -m 755 /tmp/svlint/bin/svlint /usr/local/bin/svlint && \
    rm -rf /tmp/svlint /tmp/svlint.zip
