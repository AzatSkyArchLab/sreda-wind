# sreda-wind

Urban pedestrian wind comfort engine.
Roadmap: AIJ validation (OpenFOAM 13, classical RANS) -> port the core -> GPU / ML surrogate.

Part of the Sreda project. Sibling engines (insolation, microclimate) live in separate repositories.

## Setup
On a clean Ubuntu 22.04/24.04 (Multipass VM or VPS):

    git clone git@github.com:AzatSkyArchLab/sreda-wind.git
    cd sreda-wind && bash bootstrap.sh
