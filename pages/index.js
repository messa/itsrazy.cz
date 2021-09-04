import fs from 'fs'
import { resolve } from 'path'
import yaml from 'js-yaml'

function IndexPage({ foo }) {
  return (
    <div>
      <h1>itsrazy.cz</h1>
      <pre>{JSON.stringify(foo, null, 2)}</pre>
    </div>
  )
}

export async function getStaticProps(context) {
  const dataDir = findDataDir(__dirname)
  const allData = []
  fs.readdirSync(dataDir).forEach(file => {
    if (file.endsWith('.yaml')) {
      const filePath = dataDir + '/' + file
      const fileContents = fs.readFileSync(filePath, 'utf8')
      const fileData = yaml.load(fileContents)
      allData.push({ filePath, fileData })
    }
  })
  return {
    props: { // will be passed to the page component as props
      foo: allData,
    },
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
