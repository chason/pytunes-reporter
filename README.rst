============
pyTunes Reporter
============

.. image:: https://badge.fury.io/py/pytunes-reporter.svg
    :target: https://badge.fury.io/py/pytunes-reporter

.. image:: https://travis-ci.org/gifbitjapan/pytunes-reporter.svg?branch=master
    :target: https://travis-ci.org/gifbitjapan/pytunes-reporter

.. image:: https://coveralls.io/repos/github/gifbitjapan/pytunes-reporter/badge.svg?branch=master
    :target: https://coveralls.io/github/gifbitjapan/pytunes-reporter?branch=master


A Python Framework for Getting Information Out Of iTunes Reporter API

Overview
----------

The iTunes Reporter interface has a lot of very useful information in it, but
unfortunately Apple only provides a Java Applet to access it, and no API.

This library lets you access that data as native Python objects so that you can
display, analyze, or store it however you like.

``Reporter`` takes your API information (either username and password or
AccessKey), and then lets you request information from the API. In the case of
a report, it downloads the TSV (Tab Separated Values) file, unzips it, and
converts it into a native Python object.

In a coming version, you will also be able to use this via the command-line.

Basic Usage
-------------

To access the iTunes Reporter API, you must first instantiate the ``Reporter``
class, using either your username and password::

    from reporter import Reporter

    rep = Reporter(user_id='user@mydomain.com', password='hunter2')
    print(rep.vendors)
    # ['80012345', '80054321']

Or your AccessKey (obtainable via the web interface, Apple's own Reporter tool,
or using the access_key property of an already instantiated ``Reporter``
object::

    from reporter import Reporter

    rep = Reporter(access_key='29c656f3-2dcf-4140-9346-96633197af82')
    print(rep.vendors)
    # ['80012345', '80054321']

In the case of using your user_id and password, at the time of your first
request, Reporter will fetch your AccessKey and use it for that request and all
subsequent ones.
