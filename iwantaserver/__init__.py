from subprocess import Popen
import os
import random
import sys

from flask import (Flask, request, session, g, redirect, url_for, abort,
                   render_template, flash)
from flask.ext.sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data/iwantaserver.db"
app.config["SECRET_KEY"] = "secretlol"
db = SQLAlchemy(app)


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True)
    location = db.Column(db.String)
    active = db.Column(db.Boolean)
    image_id = db.Column(db.String, nullable=False)
    image_name = db.Column(db.String)
    size_id = db.Column(db.String, nullable=False)
    size_name = db.Column(db.String)
    max_servers = db.Column(db.Integer, nullable=False)

    servers = db.relationship("Server", backref="event", lazy="dynamic")

    def __init__(self, name, location, active=False,
                 image_id="cc6e0096-84f9-4beb-a21e-d80a11a769d8",
                 size_id="performance1-2", max_servers=5):
        self.name = name
        self.location = location
        self.active = active
        self.image_id = image_id
        self.size_id = size_id
        self.max_servers = max_servers

    def __repr__(self):
        return '<Event %r %s>' % (self.name, "" if self.active else "(inactive)")


class Server(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)
    email = db.Column(db.String)
    available = db.Column(db.Boolean)

    event_id = db.Column(db.Integer, db.ForeignKey("event.id"))

    def __init__(self, ip, password, event_id):
        self.ip = ip
        self.password = password
        self.event_id = event_id

@app.route("/", methods=["GET"])
def show_index():
    return render_template("index.html")

@app.route("/server", methods=["POST"])
def show_server():

    event_name = request.form["event"]
    email_addr = request.form["email"]
    error = ""

    # Check that event exists
    event = Event.query.filter(Event.name.is_(event_name)).scalar()
    if not event:
        return render_template("oops.html",
            error="Sorry, I've never heard of %s" % event_name)

    # Claim a random available server for this user (email)
    servers = Server.query.filter(
        Server.event_id.is_(event.id)).filter(
        Server.available.is_(True)).all()

    if not servers:
        error = ("There are no servers available right now. "
                     "Go check with the Rackspace table and they'll help you out.")
        return render_template("oops.html", error=error)

    server = random.choice(servers)
    server.available = False
    server.email = email_addr
    db.session.add(server)
    db.session.commit()

    # Spin up a new server
    Popen(["givemeaserver.py",
           "--image", event.image_id,
           "--size", event.size_id, "--num", "1",
           "--event", str(event.id)])

    # Show server details
    return render_template("event.html", error=error, name=event.name,
                           image=event.image_name, size=event.size_name,
                           ip=server.ip, password=server.password)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        if not os.path.exists(os.path.join(os.getcwd(), "data")):
            os.mkdir("data")
        db.create_all()
        print("Initialized database")
    else:
        app.run(debug=os.getenv("DEBUG", False))
