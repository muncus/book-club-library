import datetime
from google.appengine.ext import ndb

class Person(ndb.Model):
  displayname = ndb.StringProperty()
  email = ndb.StringProperty()

class Book(ndb.Model):
  owner = ndb.StringProperty()
  title = ndb.StringProperty()
  isbn = ndb.StringProperty()
  author = ndb.StringProperty(repeated=True)
  description = ndb.StringProperty()

  def is_available(self):
    """A book is available if it is not currently loaned out."""
    lq = Loan.query(
        Loan.book == self.key,
        Loan.is_returned == False)
    if lq.count(limit=1) > 0:
      return False
    return True

class Loan(ndb.Model):
  book = ndb.KeyProperty()
  # may be a user, or just a name.
  loaned_to = ndb.StringProperty()
  loaned_from = ndb.StringProperty()
  note = ndb.TextProperty(default='')
  start_date = ndb.DateProperty(auto_now_add=True)
  end_date = ndb.DateProperty()
  is_returned = ndb.BooleanProperty(default=False)

  @classmethod
  def to_user(cls, email):
    """query to return books loaned to the email provided."""
    query = Loan.query(
        Loan.loaned_to == email,
        Loan.is_returned == False)
    return query

  @classmethod
  def from_user(cls, email):
    """query to return books loaned by the email provided."""
    query = Loan.query(
        Loan.loaned_from == email,
        Loan.is_returned == False)
    return query

  @classmethod
  def from_book(cls, book_obj):
    new_loan = Loan(
        loaned_from=book_obj.owner,
        book=book_obj.key,
    )
    return new_loan
  
  def complete(self):
    """Return a loaned item."""
    self.is_returned = True
    self.end_time = datetime.date.today()
    self.put()
