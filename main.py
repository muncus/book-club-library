import logging
import model

from google.appengine.api import users
from google.appengine.ext import ndb

import requests
import requests_toolbelt.adapters.appengine

# Use the App Engine Requests adapter. This makes sure that Requests uses
# URLFetch.
requests_toolbelt.adapters.appengine.monkeypatch()

from urllib import quote, urlencode, urlopen

from flask import Flask, render_template, request, redirect

BASEURL='http://library.muncustest.appspot.com'

app = Flask(__name__)

@app.route('/')
def home():
  return render_template('home.html',
      add_url=quote(BASEURL + '/add/{CODE}'),
      loan_url=quote(BASEURL + '/loan/{CODE}'))

@app.route('/add/<isbn>')
def add_to_library(isbn):
  owner = users.get_current_user()
  logging.warn(owner)
  if owner == None:
    return redirect(users.create_login_url('/add/%s' % isbn))
  # NB: i use email below. i know its not best practice. i'll fix it later.

  r = fetch_details_from_isbn(isbn)
  if r.ok:
    book = r.json()['items'][0]['volumeInfo']
    logging.warn(book)
    new_book = model.Book(
        title=book['title'],
        author=book['authors'],
        description=book['description'],
        isbn=isbn,
        owner=owner.email(),
        )
    new_book.put()
    return new_book.title
  else:
    return r.content

@app.route('/borrow/<key>', methods=['GET'])
def loan_out(key):
  if request.values.has_key('id'):
    return loan_submit(key)
  book = ndb.Key(urlsafe=key)
  loan = model.Loan.from_book(book.get())
  logging.warn(loan)
  loan.put()
  return render_template(
      'loan_edit.html',
      loan=loan)

@app.route('/borrow/<key>', methods=['POST'])
def loan_submit(key):
  if request.values.has_key('id'):
    #editing existing loan.
    loan = ndb.Key(urlsafe=request.values['id']).get()
  else:
    loan = model.Loan()
  loan.loaned_to = request.values['loan_to']
  loan.note = request.values['note']
  loan.put()
  return render_template(
      'loan_edit.html',
      loan=loan)

@app.route('/books')
def show_books():
  my_books = model.Book.query(
      model.Book.owner == users.get_current_user().email(),
  )
  books = model.Book.query()
  return render_template(
      'list_books.html',
      my_books=my_books,
      books=books,
  )

def fetch_details_from_isbn(isbn):
  """Call the google books api with an isbn, to return a dict of metadata."""
  books_api_base_url = 'https://www.googleapis.com/books/v1/volumes'
  query_params = {
    'q': 'isbn:' + isbn,
    'country': 'US',
  }
  response = requests.request('GET', books_api_base_url, params=query_params)
  return response

#@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred.', 500
