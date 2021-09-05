#!/usr/bin/env python3

from argparse import ArgumentParser
from datetime import datetime
from logging import getLogger
import lxml.html
from pathlib import Path
import pytz
import re
from requests_cache import CachedSession # https://requests-cache.readthedocs.io/en/stable/user_guide.html
from textwrap import dedent
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

    source_file.write_text(
        yaml.safe_dump(
            source,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
            width=250))


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
    cal = parse_ical(r.text)
    event['meetupcom']['ical'] = {
        'summary': cal['VEVENT']['SUMMARY'],
        'description': cal['VEVENT']['DESCRIPTION'],
        'location': cal['VEVENT']['LOCATION'],
        'geo': parse_ical_geo(cal['VEVENT']['GEO']),
        'status': cal['VEVENT']['STATUS'],
        'uid': cal['VEVENT']['UID'],
        'url': cal['VEVENT']['URL'],
        'dtstart': parse_ical_datetime(cal['VEVENT'], 'DTSTART'),
        'dtend': parse_ical_datetime(cal['VEVENT'], 'DTEND'),
    }


def parse_ical_geo(s):
    lat, lon = s.split(';')
    return {
        'lat': float(lat),
        'lon': float(lon),
    }


def parse_ical_datetime(event, key):
    for k, v in event.items():
        if k.startswith(key):
            m = re.match(r'^;TZID=([^;=]+)$', k[len(key):])
            tzname, = m.groups()
            dt = datetime.strptime(v, '%Y%m%dT%H%M%S')
            dt = pytz.timezone(tzname).localize(dt)
            dt_utc = pytz.utc.normalize(dt)
            return {
                'timezone': tzname,
                'datetime': v,
                'datetime_utc': dt_utc.strftime('%Y%m%dT%H%M%SZ'),
            }
    raise Exception(f'Could not find {key}')



def preprocess_raw_ical(raw):
    lines = raw.splitlines()
    lines = [line for line in lines if not line.startswith('DTSTAMP:')]
    return lines


def parse_ical(data):
    lines = data.splitlines()
    pos = 0

    def unescape(s):
        return s.replace(r'\,', ',').replace(r'\n', '\n')

    def parse_block():
        nonlocal pos
        assert lines[pos].startswith('BEGIN:')
        block_name = lines[pos][6:]
        pos += 1
        block_data = {}
        while True:
            if lines[pos].startswith('END:'):
                assert lines[pos] == f'END:{block_name}'
                pos += 1
                break
            if lines[pos].startswith('BEGIN:'):
                subblock_name, subblock_data = parse_block()
                assert subblock_name not in block_data
                block_data[subblock_name] = subblock_data
                continue
            if lines[pos].startswith(' '):
                block_data[key] += unescape(lines[pos][1:])
            else:
                key, value = lines[pos].split(':', 1)
                assert key not in block_data
                block_data[key] = unescape(value)
            pos += 1
        return block_name, block_data

    root_name, root_data = parse_block()
    assert root_name == 'VCALENDAR'
    return root_data


def test_parse_ical():
    sample_ical = dedent(r'''
        BEGIN:VCALENDAR
        VERSION:2.0
        PRODID:-//Meetup//RemoteApi//EN
        CALSCALE:GREGORIAN
        METHOD:PUBLISH
        X-ORIGINAL-URL:https://www.meetup.com/asociace-ux/events/280440185/ical/x
         .ics
        X-WR-CALNAME:Events - x.ics
        X-MS-OLK-FORCEINSPECTOROPEN:TRUE
        BEGIN:VTIMEZONE
        TZID:Europe/Prague
        TZURL:http://tzurl.org/zoneinfo-outlook/Europe/Prague
        X-LIC-LOCATION:Europe/Prague
        BEGIN:DAYLIGHT
        TZOFFSETFROM:+0100
        TZOFFSETTO:+0200
        TZNAME:CEST
        DTSTART:19700329T020000
        RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
        END:DAYLIGHT
        BEGIN:STANDARD
        TZOFFSETFROM:+0200
        TZOFFSETTO:+0100
        TZNAME:CET
        DTSTART:19701025T030000
        RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
        END:STANDARD
        END:VTIMEZONE
        BEGIN:VEVENT
        DTSTAMP:20210904T225439Z
        DTSTART;TZID=Europe/Prague:20210906T183000
        DTEND;TZID=Europe/Prague:20210906T203000
        STATUS:CONFIRMED
        SUMMARY:UX Monday: Podpora začínajících designérů v týmu
        DESCRIPTION:Asociace UX\nMonday\, September 6 at 6:30 PM\n\nZáří znamená 
         návrat školních lavic a nejinak tomu bude i v případě UX Monday. Opět se
          totiž vedle online streamu potkáme také v offline režimu (detail...\n\n
         https://www.meetup.com/asociace-ux/events/280440185/
        CLASS:PUBLIC
        CREATED:20210830T121007Z
        GEO:50.08;14.43
        LOCATION:Svornosti 3321/2 (Svornosti 3321/2\, Smíchov\, Praha-Praha 5\, C
         zech Republic 150 00)
        URL:https://www.meetup.com/asociace-ux/events/280440185/
        LAST-MODIFIED:20210830T145130Z
        UID:event_280440185@meetup.com
        END:VEVENT
        END:VCALENDAR
    ''').lstrip()
    parsed = parse_ical(sample_ical)
    assert parsed == {
        'CALSCALE': 'GREGORIAN',
        'METHOD': 'PUBLISH',
        'PRODID': '-//Meetup//RemoteApi//EN',
        'VERSION': '2.0',
        'VEVENT': {
            'CLASS': 'PUBLIC',
            'CREATED': '20210830T121007Z',
            'DESCRIPTION': 'Asociace UX\n'
                           'Monday, September 6 at 6:30 PM\n'
                           '\n'
                           'Září znamená návrat školních lavic a nejinak tomu '
                           'bude i v případě UX Monday. Opět se totiž vedle '
                           'online streamu potkáme také v offline režimu '
                           '(detail...\n'
                           '\n'
                           'https://www.meetup.com/asociace-ux/events/280440185/',
            'DTEND;TZID=Europe/Prague': '20210906T203000',
            'DTSTAMP': '20210904T225439Z',
            'DTSTART;TZID=Europe/Prague': '20210906T183000',
            'GEO': '50.08;14.43',
            'LAST-MODIFIED': '20210830T145130Z',
            'LOCATION': 'Svornosti 3321/2 (Svornosti 3321/2, Smíchov, '
                        'Praha-Praha 5, Czech Republic 150 00)',
            'STATUS': 'CONFIRMED',
            'SUMMARY': 'UX Monday: Podpora začínajících designérů v týmu',
            'UID': 'event_280440185@meetup.com',
            'URL': 'https://www.meetup.com/asociace-ux/events/280440185/'
        },
        'VTIMEZONE': {
            'DAYLIGHT': {
                'DTSTART': '19700329T020000',
                'RRULE': 'FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU',
                'TZNAME': 'CEST',
                'TZOFFSETFROM': '+0100',
                'TZOFFSETTO': '+0200'
            },
            'STANDARD': {
                'DTSTART': '19701025T030000',
                'RRULE': 'FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU',
                'TZNAME': 'CET',
                'TZOFFSETFROM': '+0200',
                'TZOFFSETTO': '+0100'
            },
            'TZID': 'Europe/Prague',
            'TZURL': 'http://tzurl.org/zoneinfo-outlook/Europe/Prague',
            'X-LIC-LOCATION': 'Europe/Prague'
        },
        'X-MS-OLK-FORCEINSPECTOROPEN': 'TRUE',
        'X-ORIGINAL-URL': 'https://www.meetup.com/asociace-ux/events/280440185/ical/x.ics',
        'X-WR-CALNAME': 'Events - x.ics'
    }


test_parse_ical()


if __name__ == '__main__':
    main()
