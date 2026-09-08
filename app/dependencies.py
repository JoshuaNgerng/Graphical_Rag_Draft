from fastapi import Request
from neo4j import Driver
from celery import Celery
from app.neo4j_graphrag.RelationshipExtractorOllama import RelationshipExtractorOllama

def get_driver(request: Request) -> Driver:
    return request.app.state.driver

def get_extractor(request: Request) -> RelationshipExtractorOllama:
    return request.app.state.extractor

def get_celery_app(request: Request) -> Celery:
    return request.app.state.celery_app

def get_state(request: Request):
    return request.app.state