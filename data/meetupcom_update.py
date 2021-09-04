#!/usr/bin/env python3

from argparse import ArgumentParser
from logging import getLogger
import lxml.html
from pathlib import Path
import requests
import yaml


logger = getLogger(Path(__file__).with_suffix('').name)

rs = requests.Session()


def main():
    p = ArgumentParser()
    p.add_argument('source_file', nargs='+', help='YAML file')
    args = p.parse_args()
    setup_logging()
    for source_file in args.source_file:
        source_file = Path(source_file)
        try:
            process_source_file(source_file)
        except Exception as e:
            logger.exception('Failed to process source file %s: %r', source_file, e)


def setup_logging():
    from logging import basicConfig, DEBUG
    basicConfig(level=DEBUG, format='%(asctime)s %(name)-25s %(levelname)5s: %(message)s')


def process_source_file(source_file):
    assert isinstance(source_file, Path)
    logger.info('Processing source file %s', source_file)
    try:
        source = yaml.safe_load(source_file.read_text())
    except Exception as e:
        logger.warning('Failed to load source file %s as YAML: %r', source_file, e)
        return
    if not source['series'].get('meetupcom'):
        logger.debug('No meetupcom field')
        return
    source['series'].setdefault('events', [])

    r = rs.get(source['series']['meetupcom']['url'])
    r.raise_for_status()
    root = lxml.html.fromstring(r.content)
    # process <meta> elements
    for meta in root.xpath('/html/head/meta'):
        if meta.attrib.get('property') == 'og:title':
            source['series']['meetupcom']['title'] = meta.attrib['content']
        elif meta.attrib.get('name') == 'description':
            source['series']['meetupcom']['description'] = meta.attrib['content']
    # process <link> elements
    for link in root.xpath('/html/head/link'):
        if link.attrib.get('rel') == 'canonical':
            source['series']['meetupcom']['url'] = link.attrib['href']
        elif link.attrib.get('rel') == 'image_src':
            source['series']['meetupcom']['image'] = link.attrib['href']

    source_file.write_text(yaml.safe_dump(source, sort_keys=False, allow_unicode=True, default_flow_style=False))


if __name__ == '__main__':
    main()
