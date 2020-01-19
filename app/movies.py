#!/usr/bin/env python
import os
from json import dumps
from flask import Flask, g, Response, request
from flask_caching import Cache

from neo4j.v1 import GraphDatabase, basic_auth

app = Flask(__name__, static_url_path='/static/')
cache = Cache(app,config={'CACHE_TYPE': 'simple'})


from redis import Redis
from rq import Queue

rd = Redis(host='redis', port=6379)
q = Queue(connection=rd)

password = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver('bolt://neo4j',auth=basic_auth("neo4j", password))

def get_db():
	if not hasattr(g, 'neo4j_db'):
		g.neo4j_db = driver.session()
	return g.neo4j_db

@app.teardown_appcontext
def close_db(error):
	if hasattr(g, 'neo4j_db'):
		g.neo4j_db.close()

@app.route("/")
def get_index():
	return app.send_static_file('index.html')

def serialize_movie(movie):
	return {
		'id': movie['id'],
		'title': movie['title'],
		'summary': movie['summary'],
		'released': movie['released'],
		'duration': movie['duration'],
		'rated': movie['rated'],
		'tagline': movie['tagline']
	}

def serialize_cast(cast):
	return {
		'name': cast[0],
		'job': cast[1],
		'role': cast[2]
	}

@app.route("/graph")
@cache.memoize(50)
def get_graph():
	print("[CACHE MISS] Loading graph...")
	db = get_db()
	results = db.run("MATCH (m:Movie)<-[:ACTED_IN]-(a:Person) "
			 "RETURN m.title as movie, collect(a.name) as cast "
			 "LIMIT {limit}", {"limit": request.args.get("limit", 100)})
	nodes = []
	rels = []
	i = 0
	for record in results:
		nodes.append({"title": record["movie"], "label": "movie"})
		target = i
		i += 1
		for name in record['cast']:
			actor = {"title": name, "label": "actor"}
			try:
				source = nodes.index(actor)
			except ValueError:
				nodes.append(actor)
				source = i
				i += 1
			rels.append({"source": source, "target": target})
	return Response(dumps({"nodes": nodes, "links": rels}),
					mimetype="application/json")


@app.route("/search")
def get_search():
	print("[CACHE MISS] Searching...")
	try:
		q = request.args["q"]
	except KeyError:
		return []
	else:
		db = get_db()
		results = db.run("MATCH (movie:Movie) "
				 "WHERE movie.title =~ {title} "
				 "RETURN movie", {"title": "(?i).*" + q + ".*"}
		)
		return Response(dumps([serialize_movie(record['movie']) for record in results]),
						mimetype="application/json")


@app.route("/movie/<title>")
@cache.memoize(50)
def get_movie(title):
	print("[CACHE MISS] Loading movie...")
	db = get_db()
	results = db.run("MATCH (movie:Movie {title:{title}}) "
			 "OPTIONAL MATCH (movie)<-[r]-(person:Person) "
			 "RETURN movie.title as title,"
			 "collect([person.name, "
			 "         head(split(lower(type(r)), '_')), r.roles]) as cast "
			 "LIMIT 1", {"title": title})

	result = results.single();
	return Response(dumps({"title": result['title'],
						   "cast": [serialize_cast(member)
									for member in result['cast']]}),
					mimetype="application/json")

@app.route("/count")
def get_count():
	db = get_db()
	results = db.run("MATCH (n:MovieCount) RETURN n")
	result = results.single()
	count = int(result.get("count", -1))
	return Response(dumps({"count": count}), mimetype="application/json")


@app.route("/schedule_count")
def schedule_count():
	q.enqueue(count_all_movies)
	return Response(dumps({"status": "ok"}), mimetype="application/json")



def count_all_movies():
	db = get_db()
	results = db.run("MATCH (movie:Movie) RETURN COUNT(movie)")
	result = results.single()
	count = int(result.get("COUNT(movie)", -1))
	print(db.run("MATCH (n:MovieCount) DELETE n"))
	print(db.run("CREATE (n:MovieCount {count: " + str(count) + " })"))
	return count


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=8080)
