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

class Loan(ndb.Model):
  book = ndb.KeyProperty()
  # may be a user, or just a name.
  loaned_to = ndb.StringProperty()
  loaned_from = ndb.StringProperty()
  note = ndb.TextProperty()
  start_date = ndb.DateProperty(auto_now_add=True)
  end_date = ndb.DateProperty()

  @classmethod
  def from_book(cls, book_obj):
    new_loan = Loan(
        loaned_from=book_obj.owner,
        book=book_obj.key,
    )
    return new_loan
