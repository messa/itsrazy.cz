import fs from 'fs'
import { resolve } from 'path'
import yaml from 'js-yaml'
import Layout from '../components/Layout'
import DateCard from '../components/DateCard'
import EventPreview from '../components/EventPreview'

function aggregateItems(items, getKey) {
  const chunks = []
  let currentChunk = null
  let currentKey = null
  for (const item of items) {
    const itemKey = getKey(item)
    if (currentChunk && itemKey === currentKey) {
      currentChunk.push(item)
    } else {
      currentChunk = [item]
      currentKey = itemKey
      chunks.push(currentChunk)
    }
  }
  return chunks
}

const aggregateEventsByMonth = events => aggregateItems(events, event => {
  const dt = new Date(event.startDate)
  return `${dt.getFullYear()}-${dt.getMonth()}`
})

const aggregateEventsByDay = events => aggregateItems(events, event => {
  const dt = new Date(event.startDate)
  return `${dt.getFullYear()}-${dt.getMonth()}-${dt.getDate()}`
})

function deduplicateEvents(events) {
  let lastEvent = null
  return events.filter(event => {
    try {
      return event.startDate !== lastEvent?.startDate || event.title !== lastEvent?.title
    } finally {
      lastEvent = event
    }
  })
}

const monthNames = ['leden', 'únor', 'březen', 'duben', 'květen', 'červen', 'červenec', 'srpen', 'září', 'říjen', 'listopad', 'prosinec']

const firstUpperCase = s => s[0].toUpperCase() + s.substr(1)

function IndexPage({ currentEvents }) {
  return (
    <Layout>
      <h1>IT<span>srazy.cz</span></h1>
      {aggregateEventsByMonth(currentEvents).map(monthEvents => {
        const monthDate = new Date(monthEvents[0].startDate)
        return (
          <div key={monthDate.toISOString()}>
            <h3>{firstUpperCase(monthNames[monthDate.getMonth()])} {monthDate.getFullYear()}</h3>
            {aggregateEventsByDay(monthEvents).map(dayEvents => (
              <div key={dayEvents[0].startDate} style={{ display: 'flex', marginBottom: '0.75rem' }}>
                <DateCard date={dayEvents[0].startDate} />
                <div>
                  {dayEvents.map(event => (
                    <div key={event.startDate}>
                      <EventPreview event={event} />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )
      })}
      {false && <pre>{JSON.stringify({ currentEvents }, null, 2)}</pre>}
    </Layout>
  )
}

export async function getStaticProps(context) {
  const sourcesDir = findDataDir(__dirname) + '/sources'
  const allSeries = new Array()
  fs.readdirSync(sourcesDir).forEach(file => {
    if (file.endsWith('.yaml')) {
      const filePath = sourcesDir + '/' + file
      const fileContents = fs.readFileSync(filePath, 'utf8')
      const fileData = yaml.load(fileContents)
      if (fileData.series) {
        const series = loadSeries(fileData.series)
        series.id = series.id || file
        allSeries.push(series)
      }
    }
  })
  let currentEvents = []
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  allSeries.forEach(series => {
    series.events.forEach(event => {
      const eventDate = new Date(event.startDate);
      if (eventDate >= today) {
        currentEvents.push(event)
      }
    })
  })
  currentEvents.sort((a, b) => {
    if (a.startDate < b.startDate) return -1;
    if (a.startDate > b.startDate) return 1;
    return 0;
  })
  currentEvents = deduplicateEvents(currentEvents)
  return {
    props: { // will be passed to the page component as props
      currentEvents,
    },
  }
}

function loadSeries(data) {
  return {
    id: data.id || null,
    events: (data.events || []).map(ev => loadEvent(ev)),
  }
}

function loadEvent(data) {
  return {
    id: data.id || data.meetupcom?.ical?.uid || data.url,
    title: data.title || data.meetupcom?.ical?.summary || data.meetupcom?.og_title || data.id || data.url || null,
    url: data.url || data.meetupcom.url || null,
    location: data.venue?.name || data.meetupcom?.ical?.location || null,
    startDate: data.date?.toISOString() || data.meetupcom?.ical?.dtstart.toISOString() || null,
  }
}

function findDataDir(path) {
  const dataDir = resolve(path + '/data')
  if (fs.existsSync(dataDir) && fs.lstatSync(dataDir).isDirectory()) {
    return dataDir
  }
  return findDataDir(path + '/..')
}

export default IndexPage
