"""Exercise dependency interactions only; this is not an application acceptance test."""
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TypedDict
import json
import platform
import sqlite3

from defusedxml.ElementTree import fromstring
from defusedxml.common import DefusedXmlException
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from pydantic import BaseModel
from rapidfuzz.fuzz import ratio
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sqlalchemy import create_engine, text


class Payload(BaseModel):
    value: int


app = FastAPI()


@app.post('/echo')
def echo(payload: Payload) -> Payload:
    return payload


class State(TypedDict):
    approved: bool


def approval(state: State) -> dict:
    return {'approved': interrupt({'kind': 'approval'})}


def graph_for(saver):
    builder = StateGraph(State)
    builder.add_node('approval', approval)
    builder.add_edge(START, 'approval')
    builder.add_edge('approval', END)
    return builder.compile(checkpointer=saver)


checks = []
with TestClient(app) as client:
    assert client.post('/echo', json={'value': 3}).json() == {'value': 3}
    assert client.post('/echo', json={'value': 'invalid'}).status_code == 422
checks.append('FastAPI + Pydantic + HTTPX validation')

with TemporaryDirectory() as temp:
    engine = create_engine('sqlite:///' + str(Path(temp) / 'business.sqlite'))
    with engine.begin() as conn:
        conn.execute(text('create table probe (id integer primary key, value text not null)'))
        conn.execute(text('insert into probe values (1, :value)'), {'value': 'retained'})
    with engine.connect() as conn:
        assert conn.execute(text('select value from probe')).scalar() == 'retained'
    engine.dispose()
    checks.append('SQLAlchemy + SQLite transaction')
    config = {'configurable': {'thread_id': 'dependency-probe'}}
    checkpoint = str(Path(temp) / 'checkpoints.sqlite')
    with SqliteSaver.from_conn_string(checkpoint) as saver:
        result = graph_for(saver).invoke({'approved': False}, config)
        assert result.get('__interrupt__')
    # New connection/graph verifies checkpoint storage, not an in-memory resume.
    with SqliteSaver.from_conn_string(checkpoint) as saver:
        result = graph_for(saver).invoke(Command(resume=True), config)
        assert result['approved'] is True
    checks.append('LangGraph interrupt + SQLite checkpoint reopen + resume')

model = make_pipeline(TfidfVectorizer(), LogisticRegression(random_state=0))
model.fit(['human trial treatment', 'adult randomized trial', 'mouse laboratory animals', 'rat animal simulation'], [1, 1, 0, 0])
assert len(model.predict(['human trial'])) == 1
checks.append('scikit-learn TF-IDF + logistic regression fit/predict')
assert ratio('metformin trial', 'metformin trial') == 100
checks.append('RapidFuzz native extension')
try:
    fromstring('<!DOCTYPE a [<!ENTITY x "bad">]><a>&x;</a>')
except DefusedXmlException:
    checks.append('defusedxml rejects entity expansion')
else:
    raise AssertionError('Unsafe XML entity was accepted')

print(json.dumps({'python': platform.python_version(), 'platform': platform.platform(), 'sqlite': sqlite3.sqlite_version, 'checks': checks, 'scope': 'Dependency smoke only; not application implementation or quality evaluation'}, indent=2))
