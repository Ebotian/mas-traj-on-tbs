import argparse
import json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fidelity", type=int, required=True)
    parser.add_argument("--fraction", type=float, required=True)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()

    manifest = {
        "fidelity": args.fidelity,
        "fraction": args.fraction,
        "seed": args.seed,
        "score": 0.42,
    }
    print("KAPSO_EVAL_MANIFEST " + json.dumps(manifest))


if __name__ == "__main__":
    main()
