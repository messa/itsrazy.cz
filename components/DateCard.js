const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const months0 = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

const now = new Date()

function DateCard({ date }) {
  if (typeof date === 'string') {
    date = new Date(date)
  }
  return (
    <div className='DateCard'>
      <div className='dayOfWeek'>{days[date.getDay()]}</div>
      <div className='dayOfMonth'>{date.getDate()}</div>
      {months0[date.getMonth()]}
      {now.getFullYear() != date.getFullYear() && <div className='year'>{date.getFullYear()}</div>}
      <style jsx>{`
        .DateCard {
          text-align: center;
          display: inline-block;
          min-width: 50px;
          font-size: 11px;
          font-weight: bold;
          color: #666;
          margin-bottom: 10px;
        }
        .DateCard .dayOfWeek {
          font-weight: 500;
          text-transform: uppercase;
        }
        .DateCard .dayOfMonth {
          color: #c00;
          font-size: 15px;
        }
        .DateCard .year {
          color: #000;
        }
      `}</style>
    </div>
  )
}

export default DateCard
