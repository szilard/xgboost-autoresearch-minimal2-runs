# syntax=docker/dockerfile:1
# ============================================================================
# Ubuntu 26.04 + AI coding agents
#
#   as user `ubuntu` :  claude, codex, openclaw, pi, opencode, hermes
#   as user `root`   :  claude  (separate install, under /root)
#   plus             :  clone of szilard/xgboost-autoresearch-minimal
#
# Build:  docker build -t agents:26.04 .
# Run:    docker run -it --rm agents:26.04
# ============================================================================
FROM ubuntu:26.04

# ---------------------------------------------------------------------------
# 1. System packages
# ---------------------------------------------------------------------------
# git      - cloning the repo, and hermes clones its own source tree
# ripgrep  - used by most of these agents for search
# python3  - hermes is a Python app (its installer adds uv on top)
# xz-utils - to unpack the Node tarball
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        wget \
        git \
        jq \
        unzip \
        xz-utils \
        ripgrep \
        build-essential \
        python3 \
        python3-venv \
        python3-pip \
        less \
        vim \
        procps \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# 2. Node.js
# ---------------------------------------------------------------------------
# NOT from NodeSource: it publishes no 'resolute' (26.04) suite as of 2026-09.
# NOT from apt: Ubuntu 26.04 ships Node 22.22, but openclaw wants >= 22.16 with
# 24 recommended, and several of these CLIs assume a modern Node.
# So: official nodejs.org binary tarball, pinned.
ARG NODE_VERSION=24.21.0
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
        amd64) node_arch='x64' ;; \
        arm64) node_arch='arm64' ;; \
        *) echo "unsupported arch: $arch" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${node_arch}.tar.xz" -o /tmp/node.tar.xz; \
    curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/SHASUMS256.txt" -o /tmp/SHASUMS256.txt; \
    (cd /tmp && grep " node-v${NODE_VERSION}-linux-${node_arch}.tar.xz\$" SHASUMS256.txt \
        | awk '{print $1"  node.tar.xz"}' | sha256sum -c -); \
    tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 \
        --exclude CHANGELOG.md --exclude LICENSE --exclude README.md; \
    rm -f /tmp/node.tar.xz /tmp/SHASUMS256.txt; \
    node --version; npm --version

# ---------------------------------------------------------------------------
# 3. claude for ROOT  --  separate install, lives under /root
# ---------------------------------------------------------------------------
# Uses the native installer (not npm), which installs per-user into $HOME.
# Running as plain root is explicitly supported by the installer; it only
# refuses to run under `sudo` from a regular user's shell.
# Result: /root/.local/bin/claude  -- entirely independent of ubuntu's copy.
# PATH is image-global in Docker (there is no per-user ENV), so it is declared
# once, here, and ordered deliberately:
#   /root/.local/bin           -> root's own claude, first
#   /home/ubuntu/.npm-global   -> ubuntu's agents
# /root is mode 0700, so user `ubuntu` cannot traverse it and simply falls
# through to its own copies; root, which can, gets its own claude. Each user's
# ~/.profile and ~/.bashrc additionally pin their own dir first (section 7),
# so shell sessions never depend on that behaviour alone.
ENV PATH=/root/.local/bin:/home/ubuntu/.npm-global/bin:/home/ubuntu/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

USER root
RUN set -eux; \
    curl -fsSL https://claude.ai/install.sh | bash; \
    /root/.local/bin/claude --version

# ---------------------------------------------------------------------------
# 4. The `ubuntu` user
# ---------------------------------------------------------------------------
# The ubuntu:26.04 image already ships a uid-1000 `ubuntu` user; create it only
# if that ever stops being true, so this Dockerfile works either way.
#
# `ubuntu` is deliberately UNPRIVILEGED: the sudo package is not installed at
# all (see section 1), no sudoers entry is granted, and the account is left out
# of every admin group. Anything needing root must be done with
# `docker run --user root`, from outside the container.
RUN set -eux; \
    if ! id -u ubuntu >/dev/null 2>&1; then \
        useradd -m -s /bin/bash -u 1000 ubuntu; \
    fi; \
    install -d -o ubuntu -g ubuntu /home/ubuntu; \
    rm -f /etc/sudoers.d/ubuntu; \
    for g in sudo admin adm wheel staff; do \
        gpasswd -d ubuntu "$g" 2>/dev/null || true; \
    done; \
    echo "ubuntu groups: $(id -nG ubuntu)"

USER ubuntu
WORKDIR /home/ubuntu

# User-level npm prefix so global installs need no root and stay in $HOME.
# Deliberately NOT via `ENV NPM_CONFIG_PREFIX` (image-global: root's `npm -g`
# would write into ubuntu's home) and NOT via `npm config set` / ~/.npmrc
# (WORKDIR is /home/ubuntu, so npm reads that file as the *project* config for
# whoever runs there, root included). Instead: an explicit --prefix on each
# build-time install, plus NPM_CONFIG_PREFIX exported in ubuntu's shell rc only.
ENV UBUNTU_NPM_PREFIX=/home/ubuntu/.npm-global
RUN mkdir -p /home/ubuntu/.npm-global

# ---------------------------------------------------------------------------
# 5. Agents installed as `ubuntu`
# ---------------------------------------------------------------------------
# Separate RUN layers on purpose: if one upstream breaks, the others still
# build and the failure is obvious from the layer that stopped.

# claude  -> @anthropic-ai/claude-code   (bin: claude)
RUN npm install -g --prefix "$UBUNTU_NPM_PREFIX" @anthropic-ai/claude-code && claude --version

# codex   -> @openai/codex               (bin: codex)
RUN npm install -g --prefix "$UBUNTU_NPM_PREFIX" @openai/codex && codex --version

# opencode -> opencode-ai                (bin: opencode)
RUN npm install -g --prefix "$UBUNTU_NPM_PREFIX" opencode-ai && opencode --version

# openclaw -> openclaw                   (bin: openclaw)
# Installed via npm rather than openclaw.ai/install.sh: the script also runs an
# onboarding wizard and installs a background daemon, neither of which belongs
# in an image build.
RUN npm install -g --prefix "$UBUNTU_NPM_PREFIX" openclaw@latest && openclaw --version

# pi      -> @earendil-works/pi-coding-agent  (bin: pi)
# --ignore-scripts is what upstream documents for this package.
# (@mariozechner/pi-coding-agent is the older scope, last published 2026-05.)
RUN npm install -g --prefix "$UBUNTU_NPM_PREFIX" --ignore-scripts @earendil-works/pi-coding-agent && pi --version

# hermes  -> NousResearch/hermes-agent   (bin: hermes)
# Python app; its installer pulls uv + a pinned Python and clones the repo into
# ~/.hermes.  Flags keep the build non-interactive and skip the heavy optional
# extras (Playwright/Chromium is ~1GB; the Computer-Use driver is also large).
# Drop --skip-browser / --skip-computer-use if you need those tools.
RUN curl -fsSL https://hermes-agent.nousresearch.com/install.sh \
      | bash -s -- --non-interactive --skip-setup --skip-browser --skip-computer-use

# ---------------------------------------------------------------------------
# 6. Clone the project repo as `ubuntu`
# ---------------------------------------------------------------------------
RUN git clone https://github.com/szilard/xgboost-autoresearch-minimal.git \
        /home/ubuntu/xgboost-autoresearch-minimal

# ---------------------------------------------------------------------------
# 7. Shell environment
# ---------------------------------------------------------------------------
# ENV above covers non-login shells; add PATH to .bashrc so `docker exec bash`
# and interactive login shells pick it up too.
# ~/.profile covers non-interactive login shells (`bash -lc`); ~/.bashrc covers
# interactive ones (`docker exec -it ... bash`). Ubuntu's stock .bashrc returns
# early when non-interactive, which is why .profile is written too.
USER ubuntu
RUN for f in /home/ubuntu/.profile /home/ubuntu/.bashrc; do \
      printf '%s\n' \
        'export NPM_CONFIG_PREFIX="$HOME/.npm-global"' \
        'export PATH="$HOME/.npm-global/bin:$HOME/.local/bin:$PATH"' >> "$f"; \
    done

USER root
RUN for f in /root/.profile /root/.bashrc; do \
      printf '%s\n' 'export PATH="$HOME/.local/bin:$PATH"' >> "$f"; \
    done

USER ubuntu
WORKDIR /home/ubuntu
CMD ["/bin/bash"]
