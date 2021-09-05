import fs from 'fs'
import { resolve } from 'path'
import yaml from 'js-yaml'
import Layout from '../components/Layout'

function IndexPage({ foo }) {
  return (
    <Layout>
      <h1>ITsrazy.cz</h1>
      <pre>{JSON.stringify(foo, null, 2)}</pre>
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
  return {
    props: { // will be passed to the page component as props
      foo: allSeries,
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
    id: data.id || data.meetupcom.ical?.uid || null,
    title: data.title || data.meetupcom.og_title || null,
    url: data.url || data.meetupcom.url || null,
    venue: data.venue || null,
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
