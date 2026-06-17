import subprocess

result = subprocess.run(
    ["findmnt", "/data/slideshow"],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    print("Mount vorhanden")
    print(result.stdout)
else:
    print("Kein Mount vorhanden")
