import datetime
from google.appengine.ext import ndb

class Person(ndb.Model):
  displayname = ndb.StringProperty()
  email = ndb.StringProperty()

  @classmethod
  def by_email(self, email):
    q = Person.query(
      Person.email == email)
    if q.count(1):
      return q.fetch(1)[0]
    else:
      return None

  @classmethod
  def by_name(self, name):
    q = Person.query(
      Person.displayname == name)
    if q.count(1):
      return q.fetch(1)[0]
    else:
      return None

  @classmethod
  def find_or_create_by_name(self, name):
    p = Person.by_name(name)
    if p:
      return p
    else:
      p = Person(displayname=name)
      p.put()
      return p

  def find_or_create(self, name):
    """Find, or create, a Person entity given a displayname."""
    q = Person.query(
      Person.displayname == name,
      Person.email == name)
    if q.count(1):
      return q.fetch(1)[0]
    else:
      new_p = Person(name=name)
      new_p.put()
      return new_p

class Book(ndb.Model):
  owner = ndb.KeyProperty()
  title = ndb.StringProperty(default="")
  isbn = ndb.StringProperty(default="")
  author = ndb.StringProperty(repeated=True)
  description = ndb.StringProperty(default="")

  def is_available(self):
    """A book is available if it is not currently loaned out."""
    lq = Loan.query(
        Loan.book == self.key,
        Loan.is_returned == False)
    if lq.count(limit=1) > 0:
      return False
    return True
  
  def history(self):
    """Returns a cursor containing previous trades for this book."""
    lq = Loan.query(
      Loan.book == self.key).order(-Loan.start_date)
    return lq

  def owner_displayname(self):
    if self.owner:
      return self.owner.get().displayname
    else:
      return ''

class Loan(ndb.Model):
  book = ndb.KeyProperty()
  # may be a user, or just a name.
  loaned_to = ndb.KeyProperty()
  loaned_from = ndb.KeyProperty()
  note = ndb.TextProperty(default='')
  start_date = ndb.DateProperty(auto_now_add=True)
  end_date = ndb.DateProperty()
  is_returned = ndb.BooleanProperty(default=False)

  @classmethod
  def to_user(cls, email):
    """query to return books loaned to the email provided."""
    query = Loan.query(
        Loan.loaned_to == Person.by_email(email).key,
        Loan.is_returned == False)
    return query

  @classmethod
  def from_user(cls, email):
    """query to return books loaned by the email provided."""
    query = Loan.query(
        Loan.loaned_from == Person.by_email(email).key,
        Loan.is_returned == False)
    return query

  @classmethod
  def from_book(cls, book_obj):
    new_loan = Loan(
        loaned_from=book_obj.owner,
        book=book_obj.key,
        parent=book_obj.key,
    )
    return new_loan
  
  def complete(self):
    """Return a loaned item."""
    self.is_returned = True
    self.end_date = datetime.date.today()
    self.put()

  def duration(self):
    """Time for which the loan has been outstanding, in days."""
    end = self.end_date or datetime.date.today()
    duration = end - self.start_date
    return duration.days
