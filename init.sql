DROP TABLE IF EXISTS Student;
CREATE TABLE Student (
    stuId TEXT,
    stuName TEXT,
    email TEXT,
    lineId TEXT,
    nickname TEXT,
    photoUrl TEXT
);

DROP TABLE IF EXISTS Question;
CREATE TABLE Question (
    qid INTEGER NOT NULL,
    content TEXT,
    status SMALLINT NOT NULL,    -- 0: not_started 1:start 2:end
    startTime DATETIME,
    endTime DATETIME,
    PRIMARY KEY (qid)
);

DROP TABLE IF EXISTS Answer;
CREATE TABLE Answer (
    qid INTEGER NOT NULL,
    stuID TEXT,
    timestamp DATETIME,
    content TEXT
);
