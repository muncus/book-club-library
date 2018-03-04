# -*- coding: utf-8 -*-
# Administration handlers for book-club-library.
from flask import Blueprint, render_template, request, flash, url_for, redirect

import datetime
import logging
import model

from google.appengine.api import app_identity
from google.appengine.api import mail
from google.appengine.api import modules
from google.appengine.api import search
from google.appengine.api import users
from google.appengine.datastore.datastore_query import Cursor
from google.appengine.ext import deferred
from google.appengine.ext import ndb


admin_blueprint = Blueprint('admin', __name__)

@admin_blueprint.route('/')
def home():
  return render_template("admin_home.html")

@admin_blueprint.route('/clear-search-index')
def clear_search_index(continue_cursor=None):
  """Search for everything, and delete it from the search index."""
  cursor = search.Cursor()
  if continue_cursor:
    cursor = continue_cursor
  index = model.Book.BOOK_INDEX
  res = index.search(search.Query(
      query_string='',
      options=search.QueryOptions(
          limit=50,
          cursor=cursor,
          ids_only=True)))
  for r in res:
    logging.debug("Enqueueing deletion of document: %s" % r.doc_id)
    deferred.defer(index.delete, r.doc_id)
  if res.cursor:
    logging.debug("Batch deleted. Continuing to next batch.")
    return clear_search_index(res.cursor)
  flash("tasks added to delete all documents. Deletions may take a few minutes.")
  return redirect(url_for("admin.home"))

@admin_blueprint.route('/rebuild-search-index')
def rebuild_search_index(continue_cursor=None):
  all_books = model.Book.query()
  for book in all_books:
    deferred.defer(book.update_search_index)
  flash("Search Index Rebuilds enqueued. updates may take a few minutes.")
  return redirect(url_for("admin.home"))

@admin_blueprint.route('/invite-user')
def invite_form():
  return render_template("admin_invite.html")

@admin_blueprint.route('/invite-user', methods=['POST'])
def invite_send():
  """Sends an email to invite the user at the email address given."""
  name = request.values.get('displayname')
  person_obj = model.Person.find_or_create_by_name(name)
  url = ''.join([ 'http://',
      modules.get_hostname(version=modules.get_current_version_name()),
      '/register/',
      person_obj.key.urlsafe()])
  email = request.values.get('email')
  message = request.values.get('message')
  sender = 'invite@' + app_identity.get_application_id() + ".appspotmail.com"
  logging.debug(sender)
  logging.debug(url)
  # logging.debug(render_template("invite_message.txt", join_url=url, personal_message=message))
  mail.send_mail(
    sender=sender,
    to=email,
    subject="You have been invited to a Book Club!",
    bcc='muncus@gmail.com',
    body=render_template("invite_message.txt",
        join_url=url,
        personal_message=message))
  flash("Email sent to %s" % email)
  return redirect(url_for('admin.invite_form'))
