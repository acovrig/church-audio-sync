import os
from dotenv import load_dotenv
from datetime import timedelta, datetime
import mysql.connector

class BulletinDB:
  def __init__(self):
    print('Init DB')
    load_dotenv()
    self.db = mysql.connector.connect(
      host=os.getenv('MYSQL_HOST'),
      user=os.getenv('MYSQL_USER'),
      password=os.getenv('MYSQL_PASS'),
      database=os.getenv('MYSQL_DB')
    )
    self.cursor = self.db.cursor(dictionary=True)
  
  def get_date(self, date=None):
    if date is None:
      date = 7 - (5 - datetime.now().weekday()) # TODO: test this, it feels wrong
      date = 0 if date == 7 else date
      date = (datetime.now() - timedelta(date)).date()
    self.cursor.execute('SELECT name,who,info,start FROM bulletin WHERE date=%s ORDER BY start;', (date,))
    res = self.cursor.fetchall()
    ss = res[0]['start']
    del res[0]
    for x in res:
      d = str(x['start'] - ss)
      x['ss'] = d
    
    return res

if __name__ == '__main__':
  from dotenv import load_dotenv
  load_dotenv()

  bulletin = BulletinDB()
  bulletin = bulletin.get_date()
  for e in bulletin:
    print(f"{e['ss']} - {e['name']} - {e['who']} ({e['info']})")