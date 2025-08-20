import os
import sys
from alembic.config import main

if __name__ == "__main__":
    # This ensures that alembic's command-line interface is run
    # with the correct Python environment and working directory.
    # We are programmatically doing what 'alembic upgrade head' does.

    # Read the password from the secret file
    try:
        with open("/run/secrets/POSTGRES_PASSWORD", "r") as f:
            os.environ["POSTGRES_PASSWORD"] = f.read().strip()
    except FileNotFoundError:
        print("POSTGRES_PASSWORD secret not found. Please ensure it is mounted correctly.")
        sys.exit(1)

    sys.argv = [
        "alembic",
        "upgrade",
        "head",
    ]
    main()
