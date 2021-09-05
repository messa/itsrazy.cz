function EventPreview({ event }) {
  return (
    <div className='EventPreview'>
      <h3 className='title'>
        <ALink href={event.url}>{event.title}</ALink>
      </h3>
      {event.location && <div className='location'>{event.location}</div>}
      {/*<pre>{JSON.stringify(event)}</pre>*/}
      <style jsx>{`
        .EventPreview {
          margin-bottom: 1em;
        }
        .EventPreview .title {
          margin: 0 0 3px 0;
          font-size: 14px;
        }
        .EventPreview .title :global(a) {
          color: #000;
        }
        .EventPreview .location {
          margin: 3px 0;
          font-size: 12px;
          color: #404040;
        }
      `}</style>
    </div>
  )
}

function ALink({ children, href }) {
  if (href) return <a href={href}>{children}</a>
  return {children}
}

export default EventPreview
