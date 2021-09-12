//const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const days = ['Ne', 'Po', 'Út', 'St', 'Čt', 'Pá', 'So']

const now = new Date()

function DateCard({ date }) {
  if (typeof date === 'string') {
    date = new Date(date)
  }
  return (
    <div className='DateCard'>
      <div className='inner'>
        <div className='dayOfMonth'>{date.getDate()}</div>
        <div className='dayOfWeek'>{days[date.getDay()]}</div>
      </div>
      <style jsx>{`
        .DateCard {
          display: inline-block;
          font-size: 11px;
          font-weight: bold;
          color: #666;
          margin-bottom: 10px;
          min-width: 30px;
        }
        .DateCard > .inner {
          display: inline-block;
          text-align: center;
        }
        .DateCard .dayOfWeek {
          font-weight: 400;
          text-transform: uppercase;
          font-size: 11px;
        }
        .DateCard .dayOfMonth {
          color: #c00;
          font-size: 15px;
        }
      `}</style>
    </div>
  )
}

export default DateCard
