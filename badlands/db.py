import sqlite3, time
from pathlib import Path
class DB:
 def __init__(self,path):
  Path(path).parent.mkdir(parents=True,exist_ok=True)
  self.conn=sqlite3.connect(path)
  self.conn.row_factory=sqlite3.Row
  self.conn.executescript("""
  PRAGMA journal_mode=WAL;
  CREATE TABLE IF NOT EXISTS players(guid TEXT PRIMARY KEY,name TEXT NOT NULL,discord_id TEXT);
  CREATE TABLE IF NOT EXISTS positions(guid TEXT PRIMARY KEY,x REAL,z REAL,seen_at REAL);
  CREATE TABLE IF NOT EXISTS presence(guid TEXT PRIMARY KEY,zone TEXT,entered_at REAL,last_exit REAL DEFAULT 0);
  CREATE TABLE IF NOT EXISTS stats(guid TEXT PRIMARY KEY,kills INTEGER DEFAULT 0,deaths INTEGER DEFAULT 0,streak INTEGER DEFAULT 0,best_streak INTEGER DEFAULT 0,zone_seconds REAL DEFAULT 0);
  CREATE TABLE IF NOT EXISTS kills(id INTEGER PRIMARY KEY AUTOINCREMENT,unique_key TEXT UNIQUE,killer TEXT,victim TEXT,zone TEXT,occurred_at REAL);
  CREATE TABLE IF NOT EXISTS rewards(id INTEGER PRIMARY KEY AUTOINCREMENT,guid TEXT NOT NULL,kind TEXT NOT NULL,tier TEXT NOT NULL,items TEXT NOT NULL,status TEXT DEFAULT 'pending',created_at REAL,claimed_at REAL,UNIQUE(guid,kind,tier,created_at));
  CREATE TABLE IF NOT EXISTS game_grants(grant_id INTEGER PRIMARY KEY,guid TEXT NOT NULL,tier INTEGER NOT NULL,status TEXT NOT NULL,seen_at REAL);
  CREATE TABLE IF NOT EXISTS ingest(id INTEGER PRIMARY KEY CHECK(id=1),remote_name TEXT DEFAULT '',offset_bytes INTEGER DEFAULT 0,tail TEXT DEFAULT '');
  INSERT OR IGNORE INTO ingest(id) VALUES(1);
  """)
  self.conn.commit()
 def execute(self,sql,params=()):
  x=self.conn.execute(sql,params);self.conn.commit();return x
 def one(self,sql,p=()):return self.conn.execute(sql,p).fetchone()
 def all(self,sql,p=()):return self.conn.execute(sql,p).fetchall()
 def player(self,guid,name):
  self.execute('INSERT INTO players(guid,name) VALUES(?,?) ON CONFLICT(guid) DO UPDATE SET name=excluded.name',(guid,name))
 def stat(self,guid): self.execute('INSERT OR IGNORE INTO stats(guid) VALUES(?)',(guid,))
