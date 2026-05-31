#!/bin/bash
# Provisions the environment on a clean Ubuntu 22.04/24.04.
# Identical on a Multipass VM and on a VPS.
set -euo pipefail

OPENFOAM_VERSION=13                     # pin: change here and only here
VENV_DIR="${HOME}/.venvs/sreda-wind"    # outside the project dir: Multipass mounts break venv symlinks

if [ ! -d "/opt/openfoam${OPENFOAM_VERSION}" ]; then
    sudo sh -c "wget -O - https://dl.openfoam.org/gpg.key > /etc/apt/trusted.gpg.d/openfoam.asc"
    sudo add-apt-repository -y http://dl.openfoam.org/ubuntu
    sudo apt-get update
    sudo apt-get install -y "openfoam${OPENFOAM_VERSION}"
fi
# OpenFOAM is sourced from ~/.bashrc for interactive shells, NOT here:
# sourcing it under `set -euo pipefail` corrupts the bash shell context.
grep -q "openfoam${OPENFOAM_VERSION}/etc/bashrc" ~/.bashrc || \
    echo "source /opt/openfoam${OPENFOAM_VERSION}/etc/bashrc" >> ~/.bashrc

sudo apt-get install -y python3-venv python3-pip git

if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv "${VENV_DIR}"
fi
. "${VENV_DIR}/bin/activate"
pip install --upgrade pip
pip install -e ".[dev]"

python -m pytest tests/ -q
echo "OK - environment ready, OpenFOAM ${OPENFOAM_VERSION}"
echo "venv: ${VENV_DIR}  (activate: . ${VENV_DIR}/bin/activate)"
