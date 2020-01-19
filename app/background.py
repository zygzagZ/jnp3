#!/usr/bin/env python
import os
from json import dumps
from flask import Flask, g, Response, request
from flask_caching import Cache
import time

from neo4j.v1 import GraphDatabase, basic_auth
password = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver('bolt://neo4j',auth=basic_auth("neo4j", password))

def count_all_movies():
	db = driver.session()
	results = db.run("MATCH (movie:Movie) RETURN COUNT(movie)")
	result = results.single()
	count = int(result.get("COUNT(movie)", -1))
	time.sleep(10)
	db.run("MATCH (n:MovieCount) SET n.count = " + str(count))
	db.close()
	return count
