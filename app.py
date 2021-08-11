import sqlite3
import pickle
from scipy.io import wavfile


from flask import Flask, json, request, g, jsonify, send_file
app = Flask(__name__)

DATABASE = 'data/audio.db'
DATABASE_ATTR = '_database'
DURATION_INDEX = 0
SAMPLE_RATE_INDEX = 1
AUDIO_BYTES_INDEX = 2
ERROR = "No audio with the name: {}"


@app.route("/post", methods=["POST"])
def handlePost():
    file = request.files["file"]
    samplerate, data = wavfile.read(file)
    duration = data.shape[0] / samplerate
    insert_audio((file.filename, duration, samplerate, pickle.dumps(data)))
    return "Saved {}\n".format(file.filename)


@app.route("/list", methods=["GET"])
def handleList():
    max_duration = int(request.args["maxduration"])
    rows = get_audio_with_constraint(max_duration)
    return jsonify(files=[row[0] for row in rows])


@app.route("/info", methods=["GET"])
def handleInfo():
    name = request.args["name"]
    rows = lookup_audio(name)
    if len(rows) == 0:
        return jsonify(error=ERROR.format(name))
    return jsonify(duration=rows[0][DURATION_INDEX], samplerate=rows[0][SAMPLE_RATE_INDEX])


@app.route("/download", methods=["GET"])
def handleDownload():
    name = request.args["name"]
    rows = lookup_audio(name)
    if len(rows) == 0:
        return jsonify(error=ERROR.format(name))
    wavfile.write('temp.wav', rows[0][SAMPLE_RATE_INDEX], pickle.loads(
        rows[0][AUDIO_BYTES_INDEX]))
    return send_file(
        'temp.wav',
        mimetype="audio/wav",
        as_attachment=True,
        attachment_filename=name)


def lookup_audio(name):
    with app.app_context():
        select_sql = 'SELECT Duration, SampleRate, AudioBytes FROM Audio WHERE Name = \'{}\''.format(
            name)
        return get_db().execute(select_sql).fetchall()


def get_audio_with_constraint(max_duration):
    with app.app_context():
        select_sql = 'SELECT Name FROM Audio WHERE Duration < {}'.format(
            max_duration)
        return get_db().execute(select_sql).fetchall()


def insert_audio(audio_row):
    with app.app_context():
        insert_sql = 'INSERT OR REPLACE INTO Audio(Name, Duration, SampleRate, AudioBytes) VALUES(?,?,?,?) '
        cur = get_db().execute(insert_sql, audio_row)
        get_db().commit()


def get_db_attr():
    return getattr(g, DATABASE_ATTR, None)


def get_db():
    db = get_db_attr()
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


def init_db(schema_filename):
    with app.app_context():
        db = get_db()
        with app.open_resource(schema_filename, mode='r') as schema_file:
            db.cursor().executescript(schema_file.read())
        db.commit()


@app.teardown_appcontext
def close_db(exception):
    db = get_db_attr()
    if db is not None:
        db.close()


if __name__ == "__main__":
    app.run(debug=True)
