DROP TABLE IF EXISTS Student;
CREATE TABLE Student (
    stuId TEXT,
    stuName TEXT,
    stuEmail TEXT,
    lineId TEXT,
    nickname TEXT,
    photoUrl TEXT
);

DROP TABLE IF EXISTS Question;
CREATE TABLE Question (
    qid INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT,
    status SMALLINT NOT NULL,    -- 0:ready 1:open 2:close
    startTime DATETIME,
    endTime DATETIME
);

DROP TABLE IF EXISTS Answer;
CREATE TABLE Answer (
    qid INTEGER NOT NULL,
    stuID TEXT,
    timestamp DATETIME,
    content TEXT
);
