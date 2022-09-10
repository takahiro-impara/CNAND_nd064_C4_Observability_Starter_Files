from flask import Flask, render_template, request, jsonify

import pymongo
import logging
from flask_pymongo import PyMongo
from jaeger_client import Config
from flask_opentracing import FlaskTracing
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)

app.config['MONGO_DBNAME'] = 'example-mongodb'
app.config['MONGO_URI'] = 'mongodb://example-mongodb-svc.default.svc.cluster.local:27017/example-mongodb'

mongo = PyMongo(app)
metrics = PrometheusMetrics(app, group_by='endpoint')
metrics.info("app_info", "App Info", version="1.0.3")
endpoint_counter = metrics.counter(
    'by_endpoint_counter', 'Request count by endpoints',
    labels={'endpoint': lambda: request.endpoint}
)


def init_tracer(service):
    logging.getLogger('').handlers = []
    logging.basicConfig(format='%(message)s', level=logging.DEBUG)

    config = Config(
        config={
            'sampler': {
                'type': 'const',
                'param': 1,
            },
            'logging': True,
        },
        service_name=service,
    )

    # this call also sets opentracing.tracer
    return config.initialize_tracer()


tracer = init_tracer('backend-service')
tracing = FlaskTracing(tracer, True, app)


@app.route('/')
@endpoint_counter
def homepage():
    with tracer.start_span('hello world') as span:
        span.set_tag('first-tag', "Hello World")
    return "Hello World"


@app.route('/api')
@endpoint_counter
def my_api():
    with tracer.start_span('hello world') as span:
        answer = "something"
        span.set_tag('first-tag', answer)

    return jsonify(repsonse=answer)


@app.route('/star', methods=['POST'])
@endpoint_counter
def add_star():
    with tracer.start_span('star') as span:
        star = mongo.db.stars
        name = request.json['name']
        distance = request.json['distance']
        star_id = star.insert({'name': name, 'distance': distance})
        new_star = star.find_one({'_id': star_id})
        output = {'name': new_star['name'], 'distance': new_star['distance']}
        span.set_tag('status', 'star')
    return jsonify({'result': output})


# register additional default metrics
metrics.register_default(
    metrics.counter(
        'by_path_counter', 'Request count by request paths',
        labels={'path': lambda: request.path}
    )
)

if __name__ == "__main__":
    app.run()
