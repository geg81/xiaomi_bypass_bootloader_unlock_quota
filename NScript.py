"""Run the preflight checks. Application submissions are not supported."""
from preflight import main

if __name__ == "__main__":
    raise SystemExit(main())
