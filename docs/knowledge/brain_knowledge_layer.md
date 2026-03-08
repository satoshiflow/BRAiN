# BRAiN Knowledge Layer

PostgreSQL speichert langfristiges Wissen.

Redis speichert kurzfristigen Zustand und Events.

## Redis

Session Context  
Queue  
Event Bus  
Ephemeral State

## PostgreSQL

Architecture Records  
Knowledge  
Decisions  
Change Logs  
Documentation

## Knowledge Schema

knowledge_item

id  
title  
type  
source  
version  
tags  
module  
owner  
created_at  
valid_until  
content
