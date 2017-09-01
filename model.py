from google.appengine.ext import ndb

class Person(ndb.Model):
    username = ndb.StringProperty()
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
    note = ndb.TextProperty()
