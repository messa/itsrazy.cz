#!/usr/bin/env python3

from argparse import ArgumentParser
from logging import getLogger
import lxml.html
from pathlib import Path
import re
from requests_cache import CachedSession # https://requests-cache.readthedocs.io/en/stable/user_guide.html
from urllib.parse import urljoin
import yaml


logger = getLogger(Path(__file__).with_suffix('').name)

rs = CachedSession()


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
    if not source['series']['meetupcom'].get('url'):
        logger.debug('No meetupcom.url field')
        return

    m = re.match(r'^https://www\.meetup\.com/([^/?]+)/?', source['series']['meetupcom']['url'])
    urlname, = m.groups()

    r = rs.get(source['series']['meetupcom']['url'])
    r.raise_for_status()
    root = lxml.html.fromstring(r.content)
    # process <meta> elements
    for meta in root.xpath('/html/head/meta'):
        if meta.attrib.get('property') == 'og:title':
            source['series']['meetupcom']['og_title'] = meta.attrib['content']
        elif meta.attrib.get('name') == 'description':
            source['series']['meetupcom']['meta_description'] = meta.attrib['content']
    # process <link> elements
    for link in root.xpath('/html/head/link'):
        if link.attrib.get('rel') == 'canonical':
            source['series']['meetupcom']['url'] = link.attrib['href']
        elif link.attrib.get('rel') == 'image_src':
            source['series']['meetupcom']['image'] = link.attrib['href']


    event_urls = []
    for a in root.xpath('//a'):
        try:
            a_href = urljoin(r.url, a.attrib['href'])
        except KeyError:
            continue
        if f'/{urlname}/events/' in a_href and re.match(r'^https://www.meetup.com/[^/]+/events/(mbj[a-z]+|[0-9]+)/$', a_href):
            if a_href not in event_urls:
                event_urls.append(a_href)

    source['series'].setdefault('events', [])
    for event_url in event_urls:
        process_event(event_url, source['series']['events'])

    source_file.write_text(yaml.safe_dump(source, sort_keys=False, allow_unicode=True, default_flow_style=False, width=250))


def process_event(event_url, events):
    for event in events:
        if event['meetupcom']['url'] == event_url:
            break
    else:
        event = {'meetupcom': {}}
        events.append(event)

    r = rs.get(event_url)
    r.raise_for_status()
    root = lxml.html.fromstring(r.content)
    # process <meta> elements
    for meta in root.xpath('/html/head/meta'):
        if meta.attrib.get('property') == 'og:title':
            event['meetupcom']['og_title'] = meta.attrib['content']
        elif meta.attrib.get('name') == 'description':
            event['meetupcom']['meta_description'] = meta.attrib['content']
    # process <link> elements
    for link in root.xpath('/html/head/link'):
        if link.attrib.get('rel') == 'canonical':
            event['meetupcom']['url'] = link.attrib['href']
        elif link.attrib.get('rel') == 'image_src':
            event['meetupcom']['image'] = link.attrib['href']

    assert event_url.endswith('/')
    r = rs.get(event_url + 'ical/x.ics')
    r.raise_for_status()
    event['meetupcom']['ical_raw'] = preprocess_raw_ical(r.text)


def preprocess_raw_ical(raw):
    lines = raw.splitlines()
    lines = [line for line in lines if not line.startswith('DTSTAMP:')]
    return lines


if __name__ == '__main__':
    main()
