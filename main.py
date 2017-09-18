import datetime
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

from flask import Flask, flash, render_template, request, redirect, url_for

BASEURL='http://library.muncustest.appspot.com'
ADD_SCAN_REDIR = quote(BASEURL + '/add/{CODE}')
BORROW_SCAN_REDIR = quote(BASEURL + '/borrow/{CODE}')

RESULTS_PER_PAGE=40
BOOK_DATA_FAILURE_MSG = ("Failed to fetch book data.\n" +
                         "Please fill in manually.")

app = Flask(__name__)
app.secret_key = "Some_Secret_Key"

@app.route('/register')
def register_current_user():
  me = model.Person()
  me.email = users.get_current_user().email()
  me.displayname = users.get_current_user().nickname()
  me.put()
  return redirect('/')

@app.route('/')
def home():
  return render_template('home.html',
      add_url=ADD_SCAN_REDIR,
      loan_url=BORROW_SCAN_REDIR,)

@app.route('/add/<isbn>', methods=['POST'])
def add_from_form(isbn):
  if request.values.get('id', None):
    book = ndb.Key(urlsafe=request.values['id']).get()
    book.populate(
      title = request.values.get('title', book.title),
      author = request.values.get('author', ','.join(book.author)).split(','),
      description=request.values.get('description', book.description),
      isbn = request.values.get('isbn', book.isbn),
      owner = request.values.get('owner', book.owner),
    )
    book.put()
    flash("Changes Saved!")
    return render_template(
        'book_edit.html',
        book=book,
        add_url=ADD_SCAN_REDIR,
        loan_url=BORROW_SCAN_REDIR,
    )
  else:
    new_book = model.Book()
    new_book.populate(
        title=request.values.get('title',''),
        author=request.values.get('author', '').split(','),
        description=request.values.get('description', ''),
        isbn=request.values.get('isbn', isbn),
        owner=request.values.get('owner', users.get_current_user().email()),
    )
    new_book.put()
    flash("Book Created!")
    return render_template(
        'book_edit.html',
        book=new_book,
        add_url=ADD_SCAN_REDIR,
        loan_url=BORROW_SCAN_REDIR,
    )

@app.route('/book/<key>/delete', methods=['POST'])
def delete_book(key):
  book = ndb.Key(urlsafe=key)
  book.delete_async()
  flash("Book Deleted.")
  return render_template(
      'book_edit.html',
      book=model.Book(),
      add_url=ADD_SCAN_REDIR,
      loan_url=BORROW_SCAN_REDIR,
  )

@app.route('/book/<key>', methods=['GET', 'POST'])
def show_book(key):
  if request.method == 'POST':
    return add_from_form('unused')
  return render_template(
      'book_edit.html',
      book=ndb.Key(urlsafe=key).get(),
      add_url=ADD_SCAN_REDIR,
      loan_url=BORROW_SCAN_REDIR,
  )

@app.route('/add/<isbn>')
def add_from_isbn(isbn):
  # NB: i use email below. i know its not best practice. i'll fix it later.

  new_book = get_populated_book(isbn)

  #First, check if this title is already present.
  q = model.Book.query(
      model.Book.isbn == isbn)
  if (q.count(limit=1) > 0 or
      new_book.description == BOOK_DATA_FAILURE_MSG):
    # This book already exists, or we failed to fetch book data.
    # Show the form, but don't write to datastore yet.
    return render_template(
        'book_edit.html',
        book=new_book,
        messages=['Book exists, or failed to fetch data. Press submit to save.'],
        add_url=ADD_SCAN_REDIR,
        loan_url=BORROW_SCAN_REDIR,
    )
  else:
    new_book.put()
    return render_template(
        'book_edit.html',
        book=new_book,
        messages=["Book Added!"],
        add_url=ADD_SCAN_REDIR,
        loan_url=BORROW_SCAN_REDIR,
    )

@app.route('/borrow/<isbn_or_key>', methods=['GET'])
def borrow_dispatch(isbn_or_key):
  #TODO: improve isbn matching.
  if len(isbn_or_key) > 13:
    #not an isbn.
    return borrow_by_key(isbn_or_key)
  else:
    return borrow_by_isbn(isbn_or_key)

def borrow_by_key(key):
  book_key = ndb.Key(urlsafe=key)
  loan = model.Loan.from_book(book_key.get())
  loan.loaned_to = users.get_current_user().email()
  loan.put()
  logging.warn(loan.key.urlsafe())
  flash("Book Borrowed.")
  return redirect("/loan/%s" % loan.key.urlsafe())

def borrow_by_isbn(isbn):
  # Borrow may be called with an isbn, or a book key.
  q = model.Book.query(
    model.Book.isbn == isbn)
  results = q.fetch(2)
  logging.warn(results)
  if len(results) == 0:
    #book not found. add it.
    flash("Could not find book. Adding it intead.")
    return add_from_isbn(isbn)
  if len(results) == 1:
    # only one copy. redirect to borrow it by key.
    book_key = results[0].key.urlsafe()
    redirect('/borrow/%s' % book_key)
  else:
    return "support for multiple copies not yet implemented."
    # multiple copies known, pick one.

@app.route('/return/<key>')
def return_by_loan_key(key):
  loan = ndb.Key(urlsafe=key).get()
  loan.complete()
  flash("Returned!")
  return redirect("/loan/%s" % loan.key.urlsafe())

@app.route('/loan/<key>')
def edit_loan(key):
  if request.values.has_key('id'):
    return loan_submit(key)
  loan = ndb.Key(urlsafe=key).get()
  return render_template(
      'loan_edit.html',
      add_url=ADD_SCAN_REDIR,
      loan_url=BORROW_SCAN_REDIR,
      loan=loan)

@app.route('/loan/<key>', methods=['POST'])
def loan_submit(key):
  loan = model.Loan()
  if request.values.has_key('id'):
    #editing existing loan.
    loan = ndb.Key(urlsafe=request.values['id']).get()
  loan.loaned_to = request.values['loan_to']
  loan.note = request.values['note']
  loan.put()
  flash("Loan Saved.")
  return redirect("/loan/%s" % loan.key.urlsafe())

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
      add_url=ADD_SCAN_REDIR,
      loan_url=BORROW_SCAN_REDIR,
  )

@app.route('/loans')
def show_loans():
  user_email = users.get_current_user().email()
  to_me = model.Loan.to_user(user_email)
  from_me = model.Loan.from_user(user_email)
  logging.debug(to_me.fetch(1))
  logging.debug(from_me.fetch(1))
  return render_template(
      'loans_list.html',
      add_url=ADD_SCAN_REDIR,
      loan_url=BORROW_SCAN_REDIR,
      loans_to=to_me,
      loans_from=from_me)

def fetch_details_from_isbn(isbn):
  """Call the google books api with an isbn, to return a dict of metadata."""
  books_api_base_url = 'https://www.googleapis.com/books/v1/volumes'
  query_params = {
    'q': 'isbn:' + isbn,
    'country': 'US',
  }
  response = requests.request('GET', books_api_base_url, params=query_params)
  return response

def get_populated_book(isbn):
  new_book = model.Book()
  new_book.owner=users.get_current_user().email()
  new_book.isbn = isbn

  r = fetch_details_from_isbn(isbn)
  if r.ok and r.json().has_key('items'):
    book = r.json()['items'][0]['volumeInfo']
    logging.warn(book)
    new_book.populate(
        title=book.get('title', ''),
        author=book.get('authors', ''),
        description=book.get('description', ''),
        isbn=isbn,
        )
    # If a subtitle is present, include it in the title.
    # This helps with disambiguation.
    if book.has_key('subtitle') and book['subtitle']:
      new_book.title = "%s: %s" % (book['title'], book['subtitle'])
  else:
    logging.error("Failed to fetch book data: %s" % r.content)
    flash("Failed to fetch book data for isbn: %s" % isbn)
    new_book.description = BOOK_DATA_FAILURE_MSG
  return new_book

@app.context_processor
def include_userlist():
  """context processor to include list of known users, for datalist item."""
  # TODO: move this into memcache, so its cheaper to generate.
  q = model.Person.query(projection=[model.Person.email])
  return { 'known_users': [ person for person in q ]}

#@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred.', 500
