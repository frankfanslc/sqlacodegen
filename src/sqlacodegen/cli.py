from __future__ import annotations

import argparse
import sys
from contextlib import ExitStack

from sqlalchemy.engine import create_engine
from sqlalchemy.schema import MetaData

if sys.version_info < (3, 8):
    from importlib_metadata import entry_points, version
else:
    from importlib.metadata import entry_points, version


def main() -> None:
    generators = {ep.name: ep for ep in entry_points()['sqlacodegen.generators']}
    parser = argparse.ArgumentParser(
        description='Generates SQLAlchemy model code from an existing database.')
    parser.add_argument('url', nargs='?', help='SQLAlchemy url to the database')
    parser.add_argument('--option', nargs='*', help="options passed to the generator class")
    parser.add_argument('--version', action='store_true', help="print the version number and exit")
    parser.add_argument('--schemas', help='load tables from the given schemas (comma separated)')
    parser.add_argument('--generator', choices=generators, default='declarative',
                        help="generator class to use")
    parser.add_argument('--tables', help='tables to process (comma-separated, default: all)')
    parser.add_argument('--noviews', action='store_true', help="ignore views")
    parser.add_argument('--outfile', help='file to write output to (default: stdout)')
    args = parser.parse_args()

    if args.version:
        print(version('sqlacodegen'))
        return
    if not args.url:
        print('You must supply a url\n', file=sys.stderr)
        parser.print_help()
        return

    # Use reflection to fill in the metadata
    engine = create_engine(args.url)
    metadata = MetaData()
    tables = args.tables.split(',') if args.tables else None
    schemas = args.schemas.split(',') if args.schemas else [None]
    for schema in schemas:
        metadata.reflect(engine, schema, not args.noviews, tables)

    # Instantiate the generator
    generator_class = generators[args.generator].load()
    generator = generator_class(metadata, engine, set(args.option or ()))

    # Open the target file (if given)
    with ExitStack() as stack:
        if args.outfile:
            outfile = open(args.outfile, 'w', encoding='utf-8')
            stack.enter_context(outfile)
        else:
            outfile = sys.stdout

        # Write the generated model code to the specified file or standard output
        outfile.write(generator.generate())
