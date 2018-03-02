# -*- coding: utf-8 -*-
import datetime
import logging
import model

from google.appengine.api import modules
from google.appengine.api import users
from google.appengine.datastore.datastore_query import Cursor
from google.appengine.ext import ndb


import requests
import requests_toolbelt.adapters.appengine

# Use the App Engine Requests adapter. This makes sure that Requests uses
# URLFetch.
requests_toolbelt.adapters.appengine.monkeypatch()

from urllib import quote, urlencode, urlopen

from flask import Flask, flash, render_template, request, redirect, url_for

BASEURL='https://' + modules.get_hostname(
    module=modules.get_current_module_name(),
    version=modules.get_current_version_name())
ADD_SCAN_REDIR = quote(BASEURL + '/add/{CODE}')
BORROW_SCAN_REDIR = quote(BASEURL + '/borrow/{CODE}')

RESULTS_PER_PAGE=40
BOOK_DATA_FAILURE_MSG = ("Failed to fetch book data.\n" +
                         "Please fill in manually.")

app = Flask(__name__)
app.secret_key = "Some_Secret_Key"

@app.route('/register/<userkey>', methods=['GET', 'POST'])
def process_user_invite(userkey):
  if request.method == 'GET':
    expected_user = ndb.Key(urlsafe=userkey).get()
    if(expected_user.email):
      logging.warning("Email already set to '%s'" % expected_user.email)
      return "User already registered.", 403
    email = users.get_current_user().email()
    expected_user.email = email
    return render_template('user_edit.html', user=expected_user)
  else:
    expected_user = ndb.Key(urlsafe=userkey).get()
    expected_user.email = users.get_current_user().email()
    expected_user.put()
    return redirect('/')

@app.route('/user', methods=['GET', 'POST'])
@app.route('/register', methods=['GET', 'POST'])
def register_current_user():
  if request.method == 'GET':
    email = users.get_current_user().email()
    me = model.Person.by_email(email)
    if not me:
      me = model.Person()
      me.populate(
        email=email,
        displayname=users.get_current_user().nickname())
    return render_template('user_edit.html', user=me)
  else:
    email = request.values.get('email', None)
    user = model.Person(id=email)
    user.email = email
    user.displayname = request.values.get('displayname', None)
    user.put()
    flash("Welcome, %s" % user.displayname)
    return redirect(url_for('register_current_user'))

@app.route('/')
def home():
  if model.Person.by_email(users.get_current_user().email()):
    return redirect(url_for('show_my_books'))
  else:
    flash("Please register, before proceeding.")
    return redirect(url_for('.register_current_user'))

@app.route('/add', methods=['POST'])
@app.route('/add/<isbn>', methods=['POST'])
def add_from_form(isbn=None):
  new_book = model.Book()
  if users.get_current_user():
    new_owner = model.Person.by_email(users.get_current_user().email()).key
  if request.values.has_key('owner'):
    new_owner = model.Person.find_or_create_by_name(request.values['owner']).key
  new_book.populate(
      title=request.values.get('title',''),
      author=request.values.get('author', '').split(','),
      description=request.values.get('description', ''),
      isbn=request.values.get('isbn', isbn),
      artist=request.values.get('artist', '').split(','),
      publisher=request.values.get('publisher', ''),
      owner=new_owner,
  )
  logging.debug("Added book: %s" % new_book)
  new_book.put()
  logging.debug("updating search index.")
  new_book.update_search_index()
  flash("Book Created!")
  return redirect("/book/%s" % new_book.key.urlsafe())

@app.route('/book/<key>/delete', methods=['POST'])
def delete_book(key):
  book = ndb.Key(urlsafe=key)
  for loan in book.get().history():
    loan.key.delete()
  book.delete()
  flash("Book Deleted.")
  return render_template(
      'book_edit.html',
      book=model.Book(),
  )

@app.route('/book/<key>', methods=['GET', 'POST'])
def show_book(key):
  if request.method == 'POST':
    return edit_book(key)
  return render_template(
      'book_edit.html',
      book=ndb.Key(urlsafe=key).get(),
  )

def edit_book(key):
  book = ndb.Key(urlsafe=key).get()
  book.populate(
    title = request.values.get('title', book.title),
    author = request.values.get('author', ','.join(book.author)).split(','),
    description=request.values.get('description', book.description),
    isbn = request.values.get('isbn', book.isbn),
    owner = model.Person.find_or_create_by_name(request.values.get('owner', book.owner)).key,
  )
  book.put()
  logging.debug("updating search index.")
  new_book.update_search_index()
  flash("Changes Saved!")
  return render_template(
      'book_edit.html',
      book=book,
  )

@app.route('/add/')
@app.route('/add')
def empty_book_form():
  return render_template(
      'book_edit.html',
      book=model.Book(),
  )

@app.route('/add/<isbn>')
def add_from_isbn(isbn):
  new_book = get_populated_book(isbn)

  book_data_fetch_failure = (new_book.description == BOOK_DATA_FAILURE_MSG)
  #First, check if this title is already present.
  q = model.Book.query(
      model.Book.isbn == isbn)
  if (q.count(limit=1) > 0 ):
    # This book already exists.
    # Show the form, but don't write to datastore yet.
    flash('Book exists already. Save changes to make an additional copy.')
    return render_template(
        'book_edit.html',
        book=new_book,
    )
  if book_data_fetch_failure:
    flash('Failed to fetch book data. Please enter manually.')
    return render_template(
        'book_edit.html',
        book=new_book,
    )
  else:
    # no problems. save book.
    new_book.put()
    flash("Book Added!")
    return redirect("/book/%s" % new_book.key.urlsafe())

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
  loan.loaned_to = model.Person.by_email(users.get_current_user().email()).key
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
  loan = ndb.Key(urlsafe=key).get()
  return render_template(
      'loan_edit.html',
      loan=loan)

@app.route('/loan/<key>', methods=['POST'])
def loan_submit(key):
  loan = ndb.Key(urlsafe=key).get()
  loan.loaned_to = model.Person.find_or_create_by_name(request.values['loan_to']).key
  loan.note = request.values['note']
  loan.put()
  flash("Loan Saved.")
  return redirect("/loan/%s" % loan.key.urlsafe())

@app.route('/books')
def show_books():
  fwd_query = model.Book.query().order(model.Book.title, model.Book.key)
  rev_query = model.Book.query().order(-model.Book.title)
  cursor = Cursor(urlsafe=request.values.get('cursor'))
  direction = request.values.get('dir') or 'next'
  fetch_args = {}
  query = fwd_query
  fetch_args['start_cursor'] = cursor
  if direction == 'prev':
    fetch_args['start_cursor'] = cursor.reversed()
    query = rev_query

    all_books, next_cursor, more = query.fetch_page(10, **fetch_args)
    all_books.reverse()
    return render_template(
        'list_books.html',
        list_heading="All Books",
        books=all_books,
        n_cursor=cursor.reversed().urlsafe(),
        p_cursor=next_cursor.urlsafe(),
    )
  else:
    all_books, next_cursor, more = query.fetch_page(10, **fetch_args)
    return render_template(
        'list_books.html',
        list_heading="All Books",
        books=all_books,
        p_cursor=cursor.reversed().urlsafe(),
        n_cursor=next_cursor.urlsafe(),
    )

@app.route('/my-books')
def show_my_books():
  user_key = model.Person.by_email(users.get_current_user().email()).key
  my_books = model.Book.query(
      model.Book.owner == user_key
  ).order(-model.Book.interest)
  return render_template(
      'list_books.html',
      list_heading="My Books",
      books=my_books,
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
      loans_to=to_me,
      loans_from=from_me)

def fetch_details_from_isbn(isbn):
  """Call the google books api with an isbn, to return a dict of metadata."""
  books_api_base_url = 'https://www.googleapis.com/books/v1/volumes'
  query_params = {
    'q': isbn,
    'country': 'US',
  }
  response = requests.request('GET', books_api_base_url, params=query_params)
  return response

def get_populated_book(isbn):
  new_book = model.Book()
  new_book.owner = model.Person.by_email(users.get_current_user().email()).key
  new_book.isbn = isbn

  r = fetch_details_from_isbn(isbn)
  if r.ok and r.json().has_key('items'):
    book = r.json()['items'][0]['volumeInfo']
    logging.warn(book)
    # Note that the description is truncated at 1500 chars.
    new_book.populate(
        title=book.get('title', ''),
        author=book.get('authors', ''),
        description=book.get('description', '')[0:1499],
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
  q = model.Person.query()
  return { 'known_users': [ person for person in q ]}

@app.context_processor
def include_scan_links():
  """add links to zxing app for mobile device scanning."""
  return {'add_url': ADD_SCAN_REDIR,
          'borrow_url': BORROW_SCAN_REDIR,
          'scan_url_add': 'zxing://scan/?ret={hostname}/add/%7BCODE%7D&SCAN_FORMATS=EAN_13'
              .format(hostname=BASEURL),
          'scan_url_borrow': 'zxing://scan/?ret={hostname}/borrow/%7BCODE%7D&SCAN_FORMATS=EAN_13'
              .format(hostname=BASEURL),
          }

# This method is for the XHR to set interest, so it doesnt need to return a value for now.
@app.route("/interest/<book_key>")
def set_interest(book_key):
  book = ndb.Key(urlsafe=book_key).get()
  user = model.Person.by_email(users.get_current_user().email())
  logging.warning("Setting interest: %s, %s" % (book.title, request.values['value']=="true"))
  if(request.values['value']):
    book.set_interest(user, request.values['value']=="true")
  return "banana"

#@app.errorhandler(500)
def server_error(e):
  # Log the error and stacktrace.
  logging.exception('An error occurred during a request.')
  return 'An internal error occurred.', 500
