# -*- coding: utf-8 -*-
import datetime
import logging
from google.appengine.ext import ndb
from google.appengine.api import users

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
  owner = ndb.KeyProperty(kind=Person)
  title = ndb.StringProperty(default="")
  isbn = ndb.StringProperty(default="")
  author = ndb.StringProperty(repeated=True)
  artist = ndb.StringProperty(repeated=True)
  description = ndb.TextProperty(default="")
  # The count of interest entities below this one.
  interest = ndb.IntegerProperty(default=0, required=True)
  publisher = ndb.StringProperty()

  def is_available(self):
    """A book is available if it is not currently loaned out."""
    lq = Loan.query(
        Loan.book == self.key,
        Loan.is_returned == False)
    if lq.count(limit=1) > 0:
      return False
    return True

  def is_mine(self):
    return self.owner.get().email == users.get_current_user().email()

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

  def get_interest(self):
    """Is current user interested in this book?"""
    thing = Interest.get_by_id(users.get_current_user().email(), parent=self.key)
    if thing != None:
      return True
    return False

  def set_interest(self, user, value):
    """Set whether the user is interested in this book."""
    if value == True:
      existing = Interest.get_by_id(user.email, parent=self.key)
      if existing:
        return
      new = Interest(id=user.email, parent=self.key).put()
      self.interest +=1
      self.put()
    if value == False:
      try:
        # ignore failures when no such interest object exists.
        ndb.Key('Interest', user.email, parent=self.key).delete()
        self.interest -=1
        self.put()
      except Exception as e:
        logging.warning(e)
        pass
    return

class Loan(ndb.Model):
  book = ndb.KeyProperty(kind=Book)
  # may be a user, or just a name.
  loaned_to = ndb.KeyProperty(kind=Person)
  loaned_from = ndb.KeyProperty(kind=Person)
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

class Interest(ndb.Model):
  """Captures interest in a book. No real content, just presence/absence."""
  pass
