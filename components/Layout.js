import Head from 'next/head'
import styles from './Layout.module.css'

function Layout({ children }) {
  return <div className={styles.container}>
    <Head>
      <title>ITsrazy.cz</title>
    </Head>
    {children}
  </div>
}

export default Layout
