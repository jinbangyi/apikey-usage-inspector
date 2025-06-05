#!/usr/bin/env python3
"""
Build script for apikey-usage-inspector Docker image
Builds the Docker image and optionally pushes to DockerHub
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

try:
    from dotenv import load_dotenv

    load_dotenv()  # Load .env file if python-dotenv is available
except ImportError:
    pass  # python-dotenv not installed, continue without it


def run_command(
    cmd: list[str], check: bool = True, cwd: Optional[Path] = None
) -> subprocess.CompletedProcess:
    """Run a command and handle errors"""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd, check=check, cwd=cwd, capture_output=True, text=True
        )
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        sys.exit(1)


def get_version_and_name() -> Tuple[str, str]:
    """Get version from pyproject.toml"""
    import tomllib

    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)

    return data["project"]["version"], data["project"]["name"]


def docker_login(username: str, token: str) -> None:
    """Login to DockerHub using access token"""
    print("Logging into DockerHub...")
    cmd = ["docker", "login", "-u", username, "--password-stdin"]
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = process.communicate(input=token)

    if process.returncode != 0:
        print(f"Docker login failed: {stderr}")
        sys.exit(1)
    print("Docker login successful")


def build_image(image_name: str, tag: str, platform: Optional[str] = None) -> None:
    """Build Docker image"""
    print(f"Building Docker image: {image_name}:{tag}")

    cmd = ["docker", "build", "-t", f"{image_name}:{tag}"]

    if platform:
        cmd.extend(["--platform", platform])

    cmd.append(".")

    run_command(cmd)
    print(f"Successfully built {image_name}:{tag}")


def push_image(image_name: str, tag: str) -> None:
    """Push Docker image to DockerHub"""
    print(f"Pushing Docker image: {image_name}:{tag}")
    run_command(["docker", "push", f"{image_name}:{tag}"])
    print(f"Successfully pushed {image_name}:{tag}")


def tag_image(source_image: str, target_image: str) -> None:
    """Tag Docker image"""
    print(f"Tagging image: {source_image} -> {target_image}")
    run_command(["docker", "tag", source_image, target_image])


def main():
    """Main build function"""
    parser = argparse.ArgumentParser(description="Build and push Docker image")
    parser.add_argument(
        "--dockerhub-username",
        help="DockerHub username (can also be set via DOCKERHUB_USERNAME env var)",
    )
    parser.add_argument(
        "--dockerhub-token",
        help="DockerHub access token (can also be set via DOCKERHUB_TOKEN env var)",
    )
    parser.add_argument(
        "--image-name",
        help="Docker image name (default: dockerhub-username/apikey-usage-inspector)",
    )
    parser.add_argument(
        "--tag", help="Docker image tag (default: version from pyproject.toml)"
    )
    parser.add_argument(
        "--platform", help="Target platform (e.g., linux/amd64,linux/arm64)"
    )
    parser.add_argument(
        "--push", action="store_true", help="Push image to DockerHub after building"
    )
    parser.add_argument(
        "--tag-latest", action="store_true", help="Also tag as 'latest' and push"
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Build without using cache"
    )

    args = parser.parse_args()

    # Get DockerHub credentials from args or environment
    username = args.dockerhub_username or os.getenv("DOCKERHUB_USERNAME")
    token = args.dockerhub_token or os.getenv("DOCKERHUB_TOKEN")

    if not username:
        print(
            "Error: DockerHub username required. Use --dockerhub-username or set DOCKERHUB_USERNAME env var"
        )
        sys.exit(1)

    if not token and args.push:
        print(
            "Error: DockerHub access token required for pushing. Use --dockerhub-token or set DOCKERHUB_TOKEN env var"
        )
        sys.exit(1)

    # Set defaults
    version, name = get_version_and_name()
    image_name = args.image_name or f"{username}/{name}"
    tag = args.tag or version

    print(f"Building image: {image_name}:{tag}")
    print(f"Project version: {version}")
    print(f"DockerHub username: {username}")

    # Build image
    build_cmd = ["docker", "build", "-t", f"{image_name}:{tag}"]

    if args.platform:
        build_cmd.extend(["--platform", args.platform])

    if args.no_cache:
        build_cmd.append("--no-cache")

    build_cmd.append(".")

    run_command(build_cmd)

    if args.push:
        # Ensure token is available
        if not token:
            print("Error: DockerHub access token required for pushing")
            sys.exit(1)

        # Login to DockerHub
        docker_login(username, token)

        # Push the versioned image
        push_image(image_name, tag)

        # Optionally tag and push as latest
        if args.tag_latest:
            latest_image = f"{image_name}:latest"
            tag_image(f"{image_name}:{tag}", latest_image)
            push_image(image_name, "latest")

    print("Build process completed successfully!")


if __name__ == "__main__":
    main()
