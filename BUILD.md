# Build and Deployment Guide

This document explains how to build and deploy the apikey-usage-inspector Docker image.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) package manager
- Docker
- DockerHub account and access token (for pushing images)

### Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Setup

### 1. Install dependencies

```bash
uv sync
```

### 2. Configure credentials (optional, for pushing)

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and set your DockerHub credentials:

```bash
DOCKERHUB_USERNAME=your_dockerhub_username
DOCKERHUB_TOKEN=your_dockerhub_access_token
```

**Note:** Use DockerHub [Access Tokens](https://docs.docker.com/docker-hub/access-tokens/) instead of passwords for better security.

## Building the Docker Image

```bash
# Build and push (requires .env file)
uv run build-and-push --push
```

## Build Script Options

The build script supports the following options:

- `--dockerhub-username` (optional): Your DockerHub username (can use DOCKERHUB_USERNAME env var)
- `--dockerhub-token` (optional): DockerHub access token (can use DOCKERHUB_TOKEN env var)
- `--image-name` (optional): Custom image name (default: username/apikey-usage-inspector)
- `--tag` (optional): Custom tag (default: version from pyproject.toml)
- `--platform` (optional): Target platform(s) for multi-arch builds
- `--push`: Push image to DockerHub after building
- `--tag-latest`: Also tag as 'latest' and push
- `--no-cache`: Build without using Docker cache

## Environment Variables

You can set these in your `.env` file or as environment variables:

- `DOCKERHUB_USERNAME`: Your DockerHub username
- `DOCKERHUB_TOKEN`: Your DockerHub access token (**recommended over password**)
- `IMAGE_NAME`: Custom image name (optional)
- `TAG`: Custom tag (optional)

## Examples

### Build image and push to dockerhub

```bash
uv run build-and-push --push
```

## GitHub Actions

This repository includes a GitHub Actions workflow that automatically builds and pushes Docker images to DockerHub when new tags are created.

### Automated Builds on Tag Creation

The workflow (`.github/workflows/docker-build-push.yml`) triggers when you create a new tag:

1. **Tag Creation**: Push a new version tag (e.g., `v1.0.0`, `v2.1.3`)
2. **Automatic Build**: GitHub Actions builds the Docker image
3. **Multi-arch Support**: Builds for both `linux/amd64` and `linux/arm64`
4. **DockerHub Push**: Pushes with the version tag and also tags as `latest`

### Required GitHub Secrets

To use the GitHub Actions workflow, add these secrets to your repository:

- `DOCKERHUB_USERNAME`: Your DockerHub username
- `DOCKERHUB_TOKEN`: Your DockerHub access token

### Creating a New Release

```bash
# Create and push a new tag
git tag v1.0.0
git push origin v1.0.0

# The GitHub Actions workflow will automatically:
# 1. Build the Docker image
# 2. Tag it with the version (1.0.0) and 'latest'
# 3. Push both tags to DockerHub
```

## Local Development

```bash
# Install dependencies
uv sync

# Run locally (without Docker)
uv run python main.py
```
