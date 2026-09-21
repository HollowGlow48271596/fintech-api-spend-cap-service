import argparse

from .infrai_client import InfraiClient


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hard-cap-usd", type=float, required=True)
    parser.add_argument("--alert-threshold-usd", type=float, required=False)
    parser.add_argument("--period", type=str, default="monthly")
    args = parser.parse_args()

    infrai = InfraiClient()
    result = infrai.account.budget.set(
        hard_cap_usd=args.hard_cap_usd,
        period=args.period,
        alert_threshold_usd=args.alert_threshold_usd,
    )
    print(result)


if __name__ == "__main__":
    main()
