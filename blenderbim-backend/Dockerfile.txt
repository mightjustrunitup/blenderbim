# -----------------------------
# Stage 1: Builder — build Blender, addons, MCP server
# -----------------------------
FROM ubuntu:22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /build

# System dependencies
RUN apt-get update && apt-get install -y \
    wget unzip bzip2 git libfreetype6 libgl1-mesa-glx libglu1-mesa \
    libxi6 libxrender1 libgomp1 libgeos-dev xvfb libxkbcommon0 \
    python3.11 python3.11-venv python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Blender 4.4
RUN wget -q https://download.blender.org/release/Blender4.4/blender-4.4.0-linux-x64.tar.xz \
    && tar -xf blender-4.4.0-linux-x64.tar.xz \
    && mv blender-4.4.0-linux-x64 /opt/blender \
    && ln -s /opt/blender/blender /usr/local/bin/blender

# Install BlenderBIM / Bonsai add-on
RUN wget -q https://github.com/IfcOpenShell/IfcOpenShell/releases/download/blenderbim-240602/blenderbim-240602-py311-linux.zip \
    -O /root/blenderbim.zip \
    && mkdir -p /root/.config/blender/4.4/scripts/addons \
    && unzip -q /root/blenderbim.zip -d /root/.config/blender/4.4/scripts/addons/ \
    && rm /root/blenderbim.zip

# Fix shapely & lxml inside Blender's Python
RUN /opt/blender/4.4/python/bin/python3.11 -m ensurepip \
    && /opt/blender/4.4/python/bin/python3.11 -m pip install --upgrade pip \
    && /opt/blender/4.4/python/bin/python3.11 -m pip install shapely==2.0.2 lxml==5.1.0

# Clone and install MCP server (ifc-bonsai-mcp)
RUN git clone https://github.com/Show2Instruct/ifc-bonsai-mcp.git /opt/ifc-bonsai-mcp
WORKDIR /opt/ifc-bonsai-mcp
# Normal install (not editable)
RUN pip3 install .  

# Install libraries needed by MCP + Blender scripts
RUN /opt/blender/4.4/python/bin/python3.11 -m pip install websockets trimesh numpy

# Prepare runtime folder for final image
RUN mkdir -p /opt/app_runtime
RUN cp -r /opt/blender /opt/app_runtime/blender
RUN cp -r /opt/ifc-bonsai-mcp /opt/app_runtime/mcp4ifc

# -----------------------------
# Stage 2: Runtime — minimal / final image
# -----------------------------
FROM ubuntu:22.04 AS runtime

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    libfreetype6 libgl1-mesa-glx libglu1-mesa libxi6 libxrender1 \
    libgomp1 libgeos-dev xvfb libxkbcommon0 python3.11 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Copy built Blender + MCP + addons from builder
COPY --from=builder /opt/app_runtime /opt/app_runtime

# Add Blender to PATH (or call via full path /opt/app_runtime/blender/blender)
ENV PATH="/opt/app_runtime/blender/blender:${PATH}"

# Copy and install your application
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY main.py blender_generator.py mcp_client.py start.sh ./
RUN chmod +x start.sh

EXPOSE ${PORT}
CMD ["./start.sh"]
