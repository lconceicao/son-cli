

class Access(object):

    def __init__(self, platform_url):
        self._platform_url = platform_url       # Service Platform URL
        self.errmsg = ''                        # keep last error message

    @property
    def platform_url(self):
        return self.platform_url

    @property
    def error_message(self):
        return self.errmsg


def main():

    import argparse
    parser = argparse.ArgumentParser(
        description="Access to components in SONATA Service "
                    "Platform (SP)"
    )

    subparsers = parser.add_subparsers(
        title='subcommands',
        help='additional help')

    # push command arguments
    parser_push = subparsers.add_parser('push')
    parser_push.add_argument(
        '-d', '--descriptor',
        help="Publish descriptor to Catalogue",
        required=False
    )
    parser_push.add_argument(
        '-p', '--package',
        help="Publish service package to Catalogue",
        required=False
    )

    # pull command arguments
    parser_pull = subparsers.add_parser('pull')
    parser_pull.add_argument(
        '-d', '--descriptor',
        help="Retrieve descriptor from Catalogue",
        required=False
    )

    args = parser.parse_args()

    if not parser_push:
        print("no push for you")

