import argparse

from .infrai_client import InfraiClient


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--webhook-id", required=True)
    args = parser.parse_args()

    infrai = InfraiClient()
    deliveries = infrai.account.webhooks.deliveries(args.webhook_id)
    print(deliveries)


if __name__ == "__main__":
    main()
