# -*- coding: utf-8 -*-
from django.core.cache import cache
from django.core.mail import get_connection

from celery import task

from post_office.models import Email, STATUS
from post_office.utils import send_queued_mail
from post_office.settings import get_email_backend


@task
def send_email(email_id):
    email = Email.objects.select_for_update().get(pk=email_id)
    if email.status != STATUS.sent:
        email.dispatch()


@task
def send_emails(email_ids):
    emails = Email.objects.select_for_update().filter(pk__in=email_ids)

    connection = get_connection(get_email_backend())
    connection.open()
    try:
        for email in emails:
            if email.status != STATUS.sent:
                email.dispatch(connection)
    finally:
        connection.close()


@task
def send_all_email():
    lock_id = 'task-send_all_email'
    # cache.add fails if if the key already exists
    acquire_lock = lambda: cache.add(lock_id, "true", 60 * 5)
    # memcache delete is very slow, but we have to use it to take
    # advantage of using add() for atomic locking
    release_lock = lambda: cache.delete(lock_id)

    if acquire_lock():
        try:
            send_queued_mail()
        finally:
            release_lock()
