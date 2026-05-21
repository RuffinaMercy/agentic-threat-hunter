import docker
import sys
import tempfile
import os
from pathlib import Path

client = docker.from_env()

def run_code_in_sandbox(code: str, timeout: int = 10) -> str:
    # Create a temporary Python file on the host
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(code)
        host_script = Path(f.name).absolute()
    
    try:
        # Convert Windows path to Linux-style for mounting (Docker expects forward slashes)
        mount_path = str(host_script).replace('\\', '/')
        
        # Run container with script mounted, override entrypoint to run python script
        container = client.containers.run(
            "skill-sandbox",
            command=f"python /tmp/script.py",
            entrypoint="",   # override the default entrypoint
            detach=True,
            remove=False,
            mem_limit="128m",
            nano_cpus=int(0.5 * 1e9),
            network_mode="none",
            read_only=True,
            security_opt=["no-new-privileges"],
            user="sandbox",
            working_dir="/tmp",
            environment={},
            volumes={mount_path: {"bind": "/tmp/script.py", "mode": "ro"}}
        )
        result = container.wait(timeout=timeout)
        logs = container.logs(stdout=True, stderr=True).decode('utf-8')
        container.remove()
        if result['StatusCode'] != 0:
            return f"ERROR (exit {result['StatusCode']}):\n{logs}"
        return logs
    except Exception as e:
        return f"Execution error: {e}"
    finally:
        host_script.unlink()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python sandbox_docker.py '<code>'")
        sys.exit(1)
    output = run_code_in_sandbox(sys.argv[1])
    print(output)