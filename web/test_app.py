import unittest
import os
import tempfile

import pytest
import app
import database


@pytest.fixture
def client():
    db_fd, app.app.config['DATABASE'] = tempfile.mkstemp()
    app.app.config['TESTING'] = True
    client = app.app.test_client()

    with app.app.app_context():
        database.init_db()

    yield client

    os.close(db_fd)
    os.unlink(app.app.config['DATABASE'])

def test_empty_db(client):
    """start with blank database"""
    rv = client.get('/')
    assert b'No entries here so far'
