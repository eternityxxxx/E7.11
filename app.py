import os
from datetime import datetime
from bson import ObjectId
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_caching import Cache
from pymongo import MongoClient
from werkzeug.utils import secure_filename


UPLOAD_FOLDER = './static/advert_images/'

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
MONGO_HOST = os.environ.get('MONGODB_HOST', 'localhost')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

mongo_client = MongoClient(host=MONGO_HOST, port=27017)
db = mongo_client.banana

cache = Cache(app, config={'CACHE_TYPE': 'redis', 'CACHE_REDIS_URL': f'redis://{MONGO_HOST}:6379/0'})


def only_cache_get():
    if request.method == 'GET':
        return False

    return True


@app.route('/', methods=['GET', 'POST'])
@cache.cached(timeout=60, unless=only_cache_get)
def home():
    if request.method == 'POST':
        query = request.form['query']

        if query:
            return redirect(url_for('advert_search', query=query))

    context = {
        'ads': [advert for advert in db.adverts.find()],
    }

    return render_template('home.html', **context)


@app.route('/create/advert/', methods=['GET', 'POST'])
@cache.cached(unless=only_cache_get)
def create_advert():
    if request.method == 'POST':
        date = datetime.now().strftime('%A, %d, %B, %T')

        photo = request.files['advertPhoto']
        filename = secure_filename(photo.filename)
        photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        advert = {
            'title': request.form['advertTitle'],
            'description': request.form['advertDescription'],
            'condition': request.form['advertCondition'],
            'photo': filename,
            'name': request.form['advertSellerName'],
            'contact': request.form['advertSellerContact'],
            'date': date,
            'tags': [],
            'comments': [],
        }

        db.adverts.insert_one(advert)

        return redirect(url_for('home'))

    return render_template('create_advert.html')


@app.route('/create/tag/<advert_id>/', methods=['GET', 'POST'])
@cache.cached(unless=only_cache_get)
def create_tag(advert_id):
    if request.method == 'POST':
        tag = request.form['advertTag']
        db.adverts.update_one({'_id': ObjectId(advert_id)}, {'$push': {'tags': tag}})

        return redirect(url_for('home'))

    return render_template('create_tag.html')


@app.route('/create/comment/<advert_id>/', methods=['GET', 'POST'])
@cache.cached(unless=only_cache_get)
def create_comment(advert_id):
    if request.method == 'POST':
        data = {
            'comment': request.form['advertComment'],
            'author': request.form['advertCommentAuthor'],
        }
        db.adverts.update_one({'_id': ObjectId(advert_id)}, {'$push': {'comments': data}})

        return redirect(url_for('home'))

    return render_template('create_comment.html')


@app.route('/search/<query>', methods=['GET'])
# @cache.cached()
def advert_search(query):

    print(db.adverts.find_one({'title': query}))

    context = {
        'ad': db.adverts.find_one({'title': query}),
    }

    return render_template('advert_search.html', **context)


@app.route('/uploads/<filename>')
def send_photo(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == '__main__':
    app.run(debug=True)
