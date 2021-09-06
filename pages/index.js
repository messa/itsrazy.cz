import fs from 'fs'
import { resolve } from 'path'
import yaml from 'js-yaml'
import Layout from '../components/Layout'
import DateCard from '../components/DateCard'
import EventPreview from '../components/EventPreview'

function IndexPage({ currentEvents }) {
  return (
    <Layout>
      <h1>ITsrazy.cz</h1>
      {currentEvents.map((event, index) => (
        <div key={index} style={{ display: 'flex' }}>
          <DateCard date={event.startDate} />
          <EventPreview event={event} />
        </div>
      ))}
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
  const currentEvents = []
  allSeries.forEach(series => {
    series.events.forEach(event => {
      const dt = new Date(event.startDate);
      if (dt >= new Date()) {
        currentEvents.push(event)
      }
    })
  })
  currentEvents.sort((a, b) => {
    if (a.startDate < b.startDate) return -1;
    if (a.startDate > b.startDate) return 1;
    return 0;
  })
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
    title: data.title || data.meetupcom.og_title || null,
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
