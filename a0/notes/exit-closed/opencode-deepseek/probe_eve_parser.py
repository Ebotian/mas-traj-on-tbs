"""Feed a real opencode v2.0.11 `--format json` stream through EvE's parser.

EvE's OpenCodeSessionDriver parses the CLI stdout itself.  This script imports
that exact parser (read-only: no EvE file is modified) and runs it against a
captured stream, so the schema question is answered by execution, not by reading.

Usage: PYTHONPATH=/tmp/eve/src <venv>/python probe_eve_parser.py <stream.jsonl>
"""

import json
import sys
import traceback

from scaling_evolve.providers.agent.drivers.opencode import OpenCodeSessionDriver


def main(path: str) -> int:
    stdout = open(path, encoding="utf-8").read()
    print(f"stream={path} lines={len(stdout.splitlines())}")
    try:
        summary = OpenCodeSessionDriver._parse_stdout_jsonl(stdout)
    except Exception as error:  # noqa: BLE001 - we want the real failure text
        print(f"PARSER_RESULT=FAIL {type(error).__name__}: {error}")
        traceback.print_exc()
        return 1
    print("PARSER_RESULT=OK")
    print(json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
