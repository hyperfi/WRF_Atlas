"""Run indexer and frontend tests with one cross-platform npm command."""

import subprocess
import sys


def main() -> None:
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], check=True)
    subprocess.run(["node", "--experimental-strip-types", "--test", "tests/namelist.test.ts", "tests/presentation.test.ts"], check=True)


if __name__ == "__main__":
    main()
