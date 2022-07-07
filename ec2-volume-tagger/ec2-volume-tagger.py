#!/usr/bin/env python
from argparse import ArgumentParser
import boto3


DEFAULT_TAGS_TO_COPY = [
    "CreatedBy",
    "Env",
    "Proj",
]

# Tags keys are unique, but tags are returned as [{Key: key, Value: value}, ...]
def tags_to_dict(tags):
    if tags:
        return dict((t["Key"], t["Value"]) for t in tags)
    return {}


def dict_to_tags(d):
    tags = [{"Key": k, "Value": v} for (k, v) in d.items()]
    return tags


def update_tags(tags_to_copy, dryrun):
    ec2 = boto3.resource("ec2")
    for instance in ec2.instances.all():
        i_tags = tags_to_dict(instance.tags)
        print(f"\n{instance.id}: {i_tags}")

        for volume in instance.volumes.all():
            v_tags = tags_to_dict(volume.tags)
            print(f"{volume.id}: {v_tags}")

            update = False
            for k, v in i_tags.items():
                if k in tags_to_copy and v_tags.get(k) != v:
                    update = True
                    v_tags[k] = v
            if update:
                print(f"*** Updating volume tags {instance.id} {volume.id}: {v_tags}")
                ec2_v_tags = dict_to_tags(v_tags)
                if not dryrun:
                    volume.create_tags(Tags=ec2_v_tags)


def main():
    parser = ArgumentParser()
    parser.add_argument("--dryrun", action="store_true", help="Don't apply changes")
    parser.add_argument(
        "--tags",
        nargs="+",
        default=DEFAULT_TAGS_TO_COPY,
        help="Tag(s) to copy from instance to volume",
    )
    args = parser.parse_args()
    update_tags(set(args.tags), args.dryrun)


if __name__ == "__main__":
    main()
