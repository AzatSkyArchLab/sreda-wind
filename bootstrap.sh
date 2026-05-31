#!/bin/bash
# Provisions the environment on a clean Ubuntu 22.04/24.04.
# Identical on a Multipass VM and on a VPS.
set -euo pipefail

OPENFOAM_VERSION=13   # pin: change here and only here

if [ ! -d "/opt/openfoam${OPENFOAM_VERSION}" ]; then
    sudo sh -c "wget -O - https://dl.openfoam.org/gpg.key > /etc/apt/trusted.gpg.d/openfoam.asc"
    sudo add-apt-repository -y http://dl.openfoam.org/ubuntu
    sudo apt-get update
    sudo apt-get install -y "openfoam${OPENFOAM_VERSION}"
fi
grep -q "openfoam${OPENFOAM_VERSION}/etc/bashrc" ~/.bashrc || \
    echo "source /opt/openfoam${OPENFOAM_VERSION}/etc/bashrc" >> ~/.bashrc

sudo apt-get install -y python3-venv python3-pip git
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"

. "/opt/openfoam${OPENFOAM_VERSION}/etc/bashrc"
python -m pytest tests/ -q
echo "OK - environment ready, OpenFOAM ${OPENFOAM_VERSION}"
