"""Export/check the explicitly limited M1 runtime contract, never a running database."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/api"))
from nex_api.config import Settings  # noqa: E402
from nex_api.main import create_app  # noqa: E402

TARGET = Path("lib/api-spec/openapi.yaml")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    contract = create_app(Settings(_env_file=None)).openapi()
    if args.check:
        if json.loads(TARGET.read_text()) != contract:
            raise SystemExit("M1 runtime/static contract drift")
        print("M1 runtime/static contract identical")
    else:
        # JSON is valid YAML; preserves exact runtime 3.1 schemas for Orval.
        TARGET.write_text(json.dumps(contract, indent=2) + "\n")


if __name__ == "__main__":
    main()